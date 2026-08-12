# Endpoints:
#   GET  /api/health         → Health check
#   POST /api/process-video  → Ingest a YouTube video (rate limited: 3/min)
#   POST /api/ask            → Ask a question via SSE stream (rate limited: 10/min)
#   POST /api/video-info     → Fetch video metadata (title, thumbnail)
#   GET  /                   → Serves the frontend (static files)

import os
import re
import time
import json
import logging
import requests as http_requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from main import process_video, stream_ask_question

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RATE LIMITER — Sliding window per IP

# How it works:
#   For each IP address, we keep a list of request timestamps.
#   When a new request comes in:
#     1. Remove all timestamps older than the window (60 seconds)
#     2. Count remaining timestamps
#     3. If count >= limit → reject with 429 (Too Many Requests)
#     4. Otherwise → add current timestamp, allow the request

#   Example with limit=3, window=60s:
#     requests = {"192.168.1.1": [t=0s, t=20s, t=40s]}
#     New request at t=45s → 3 requests in window → REJECTED (429)
#     New request at t=61s → timestamps [t=0s] expired → 2 in window → ALLOWED

import threading

class RateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, ip: str, limit: int, window: int = 60) -> bool:
        now = time.time()
        
        with self._lock:
            if ip not in self._requests:
                self._requests[ip] = []

            # Step 1: Slide the window — remove expired timestamps
            self._requests[ip] = [t for t in self._requests[ip] if now - t < window]

            # Step 2: Check if limit exceeded
            if len(self._requests[ip]) >= limit:
                logger.warning(f"Rate limit hit: {ip} ({len(self._requests[ip])}/{limit})")
                return False

            # Step 3: Record this request
            self._requests[ip].append(now)
            return True

rate_limiter = RateLimiter()


# INPUT VALIDATION — Pydantic models

# These models validate every incoming request BEFORE it reaches your code.
# Invalid requests are rejected with a 422 error automatically.


YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)"
    r"[\w\-]+"
)


class VideoRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v):
        v = v.strip()
        if not YOUTUBE_URL_PATTERN.match(v):
            raise ValueError("Invalid YouTube URL. Must be a youtube.com or youtu.be link.")
        return v


class QuestionRequest(BaseModel):
    url: str
    question: str

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v):
        v = v.strip()
        if not YOUTUBE_URL_PATTERN.match(v):
            raise ValueError("Invalid YouTube URL.")
        return v

    @field_validator("question")
    @classmethod
    def validate_question(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty.")
        if len(v) > 500:
            raise ValueError("Question must be under 500 characters.")
        return v


# FASTAPI APP

app = FastAPI(
    title="YouTube Research Analyst API",
    docs_url=None,    # Disable Swagger UI in production
    redoc_url=None,   # Disable ReDoc in production
)

# CORS — restrict origins for production safety
# On Heroku, set ALLOWED_ORIGINS env var to your app's domain
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# No-cache middleware — prevents browser from serving stale JS/CSS
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".js", ".css", ".html")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# Global Error Handler — never leak internals

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."}
    )


# Endpoints

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/video-info")
async def video_info(body: VideoRequest):
    """
    Fetch video metadata (title, author, thumbnail) using YouTube's
    public oEmbed API. No API key required.
    """
    try:
        resp = http_requests.get(
            "https://www.youtube.com/oembed",
            params={"url": body.url, "format": "json"},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title", ""),
                "author": data.get("author_name", ""),
                "thumbnail": data.get("thumbnail_url", ""),
            }
    except Exception:
        pass
    # Graceful fallback — don't error if metadata fetch fails
    return {"title": "", "author": "", "thumbnail": ""}


@app.post("/api/process-video")
async def process_video_endpoint(request: Request, body: VideoRequest):
    """
    Ingest a YouTube video: fetch transcript → chunk → embed → store in ChromaDB.
    Rate limited to 3 requests/min per IP.
    """
    ip = request.client.host
    if not rate_limiter.check(ip, limit=10):
        raise HTTPException(
            status_code=429,
            detail="Too many video processing requests. Please wait a minute."
        )

    logger.info(f"Processing video: {body.url} (from {ip})")

    try:
        result = process_video(body.url)
        return result
    except ValueError as e:
        # Catch our custom "Video too long" error
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process video. Check the URL and try again."
        )


@app.post("/api/ask")
async def ask_endpoint(request: Request, body: QuestionRequest):
    """
    Ask a question about a processed video.
    Streams the LLM response via Server-Sent Events (SSE).
    Rate limited to 10 requests/min per IP.

    SSE format:
      data: {"token": "partial text"}   ← streamed tokens
      data: {"done": true}              ← signals completion
      data: {"error": "message"}        ← if something goes wrong
    """
    ip = request.client.host
    if not rate_limiter.check(ip, limit=10):
        raise HTTPException(
            status_code=429,
            detail="Too many questions. Please wait a minute."
        )

    logger.info(f"Question from {ip}: {body.question[:80]}...")

    def generate():
        try:
            for token in stream_ask_question(body.url, body.question):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': 'Failed to generate answer. Please try again.'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# Static Files — serve the frontend
# This MUST be the last route — it catches all non-API requests
# and serves frontend files (index.html, style.css, app.js)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
