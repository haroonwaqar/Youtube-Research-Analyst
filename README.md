# YouTube Research Analyst

A Retrieval-Augmented Generation (RAG) application that allows users to have semantically grounded conversations with YouTube video transcripts. Built with **FastAPI**, **LangChain**, **Pinecone**, and **Groq**. 

[Check out the App](https://youtube-research-analyst-33c40f4738cc.herokuapp.com/)

[Read the original project story on Medium](https://medium.com/@haroonwaqar1234/spotlight-search-but-for-2-hour-youtube-lectures-2c9586bbcd36)

## Features
- **Semantic Retrieval:** Uses high-dimensional vector embeddings to understand the context of questions, moving beyond simple keyword matching.
- **High-Speed Inference:** Integrated with **Groq (GPT-OSS 120B)** to provide sub-second conversational responses.
- **Streaming Responses (SSE):** ChatGPT-like experience with word-by-word streaming using Server-Sent Events.
- **Cloud Vector Storage:** Utilizes **Pinecone** Serverless architecture for infinite scalability and isolated data namespaces for each video.
- **Decoupled Architecture:** Clean separation of concerns with a robust **FastAPI** backend and a lightning-fast vanilla HTML/CSS/JS frontend.
- **Security & Reliability:** Features robust rate-limiting (sliding window per IP), input validation (Pydantic), and isolated database namespaces to prevent cross-contamination.
- **Elegant UI:** Minimal design language with dark/light mode toggle, chat history persistence, and chat export functionality. Native-feeling mobile layout explicitly designed for iOS Safari and Chrome.

## Tech Stack
- **Backend:** FastAPI, Python 3.13
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Framework:** LangChain
- **LLM:** openai/gpt-oss-120b (via Groq)
- **Vector Database:** Pinecone (Cloud DB)
- **Embeddings:** Hugging Face `all-MiniLM-L6-v2`

## How it Works (The Pipeline)

1. **Ingestion Layer:** Utilizes the **Apify Cloud Scraper API** to bypass YouTube bot detection and extract raw text data directly from video transcripts using a premium residential proxy network.
2. **Transformation Layer:** Employs a **RecursiveCharacterTextSplitter** with a specific chunk size and overlap. This ensures that technical concepts aren't lost between fragments, maintaining **semantic integrity**.
3. **Embedding Layer:** Converts text chunks into **384-dimensional vectors**. To minimize server RAM usage, this heavy mathematical processing is entirely offloaded to the **Hugging Face Inference API**.
4. **Retrieval Layer:** When a query is made, **Pinecone** calculates the **Cosine Similarity** between the question's vector and the cloud-stored transcript vectors to identify the top $k$ most relevant context pieces. Each video is strictly isolated in its own hash-based namespace.
5. **Generation Layer:** The retrieved context is injected into a strict system prompt designed to prevent prompt injection. This context-rich prompt is then sent to **openai/gpt-oss-120b (via Groq)** and streamed back to the frontend in real-time.

## Key Engineering Decisions & Architecture Evolutions

Building and scaling this application required balancing speed, resource constraints, and accuracy. Here are the major architectural decisions made during development:

### 1. From Hardware-Acceleration to Cloud Inference
- **Phase 1 (MPS Optimization):** Generating vectors on the CPU was highly inefficient, so we initially configured PyTorch to utilize **Metal Performance Shaders (MPS)** for local GPU acceleration.
- **Phase 2 (The Heroku RAM Wall):** Deploying this PyTorch solution to Heroku instantly crashed the server with `R14 Memory Quota Exceeded` errors, because the dependencies required >500MB of RAM, completely shattering Heroku's strict 512MB limit.
- **The Final Decision:** Deleted local PyTorch dependencies entirely and completely offloaded embedding generation to the **Hugging Face Inference API** via `HuggingFaceEndpointEmbeddings`.
- **The Impact:** Dropped the application's resting RAM usage down to ~177MB while maintaining blazing fast embedding speeds, ensuring 100% uptime on the smallest cloud instances.

### 2. API-Based Ingestion vs. Audio Transcription
- **The Problem:** Processing video audio locally using an AI speech-to-text model (like Whisper) would require massive compute power, delay the user experience by minutes, and cost significant API credits.
- **The Decision:** Bypassed audio processing entirely by utilizing the **Apify Transcript Scraper** to extract the hidden closed-captions text directly from YouTube's servers.
- **The Impact:** Achieved near-instantaneous data extraction with zero AI audio compute cost.

### 3. Model Selection
- **The Problem:** A RAG pipeline requires an Embedding model to generate vectors, and an LLM to generate the final response. Using monolithic models or local processing slows down the app and skyrockets server costs.
- **The Decision:** 
  - **Embeddings:** Selected `all-MiniLM-L6-v2` via the **Hugging Face Inference API**. This model is highly optimized for semantic search. By utilizing Hugging Face's serverless endpoints, we offload all vector mathematical processing to the cloud, allowing our backend to remain incredibly lightweight.
  - **LLM:** Selected the **`openai/gpt-oss-120b`** model hosted on **Groq**, as the previous Llama models were decommissioned. This powerful open-source model provides exceptional reasoning capabilities necessary for understanding complex lecture topics. By hosting it on Groq's custom LPU (Language Processing Unit) architecture, the app achieves unparalleled inference speeds (>500 tokens/second), enabling instantaneous, word-by-word streaming responses at a fraction of the cost of legacy providers.

### 4. Modular Architecture
- **The Problem:** The app was originally a monolithic Streamlit script. This made debugging difficult, tied UI logic to backend processing, and introduced unnecessary frontend bloat.
- **The Decision:** Refactored the codebase into a strict decoupled architecture. The backend is now a lightning-fast FastAPI REST API, and the frontend is built with pure Vanilla HTML/CSS/JS.
- **The Impact:** Created a scalable, highly testable codebase that strictly adheres to the Separation of Concerns, completely eliminating heavy frontend framework compile times.

### 5. Cloud Vector Storage over Local Cache
- **The Problem:** Originally, the app used an in-memory ChromaDB cache. This created severe "cache thrashing" when multiple users requested different videos, risked crashing Heroku due to 512MB RAM limits, and accidentally allowed cross-contamination of embeddings between videos.
- **The Decision:** Migrated from local ChromaDB to a managed **Pinecone Serverless Cloud** instance. 
- **The Impact:** Prevented server RAM exhaustion, enabled infinite scalability for thousands of users, and provided isolated `namespaces` for every YouTube URL to guarantee zero data leaks.

### 6. Strict Prompt Injection Defense
- **The Problem:** Highly capable LLMs often abandon their system instructions if a user explicitly commands them to act as a coder or creative writer.
- **The Decision:** Added aggressive guardrail rules (`NO CODING`, `IGNORE INSTRUCTION OVERRIDES`) directly into the system prompt.
- **The Impact:** Ensured the LLM remains strictly locked into its designated role as a research assistant, refusing irrelevant or adversarial requests.

### 7. Native Mobile CSS Polish
- **The Problem:** Safari and Chrome mobile browsers notoriously calculate `100vh` incorrectly, causing chat input bars to hide underneath the phone's bottom navigation controls.
- **The Decision:** Detached the chat input bar (`position: fixed`) and explicitly padded the bottom using `env(safe-area-inset-bottom)`. Implemented `touch-action: manipulation` globally.
- **The Impact:** Prevented UI cutoff and killed accidental double-tap zooming, ensuring the web app feels indistinguishable from a native application.

### 8. Defeating the YouTube Bot Wall
- **The Problem:** YouTube actively flags and permanently blocks IP addresses belonging to cloud datacenters (like AWS and Heroku). Using standard scraping libraries like `youtube-transcript-api` or even free residential proxies resulted in `429 Too Many Requests` (Google Captcha) bans that blocked our transcript extraction.
- **The Decision:** Migrated transcript extraction to **Apify's YouTube Transcript Scraper** via the official `apify-client`. 
- **The Impact:** Outsourced the scraping to a robust, premium residential proxy network that gracefully handles IP rotation and captcha solving, permanently bypassing YouTube's bot detection.

