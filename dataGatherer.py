import requests
import yt_dlp
from langchain_community.document_loaders import YoutubeLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def _fallback_ytdlp(url):
    print(f"[dataGatherer] youtube-transcript-api failed. Falling back to yt-dlp for {url}...")
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        subs = info.get('subtitles', {})
        auto_subs = info.get('automatic_captions', {})
        
        en_subs = subs.get('en', []) or auto_subs.get('en', [])
        if not en_subs:
            raise ValueError("No English subtitles found via yt-dlp.")
            
        # Try to grab JSON3 format which is easiest to parse
        json3_url = next((s['url'] for s in en_subs if s.get('ext') == 'json3'), en_subs[0]['url'])
        
        res = requests.get(json3_url)
        if 'json3' in json3_url:
            data = res.json()
            text = " ".join(
                seg.get('utf8', '')
                for event in data.get('events', [])
                for seg in event.get('segs', [])
            )
        else:
            # VTT fallback parsing
            import re
            text = re.sub(r'<[^>]+>', '', res.text)
            text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} -->.*?\n', '', text)
            text = re.sub(r'WEBVTT\n.*?\n', '', text)
            text = ' '.join(text.split())
            
        return [Document(page_content=text, metadata={"source": url})]

def get_video_chunks(url):
    try:
        loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
        data = loader.load()
    except Exception as e:
        print(f"[dataGatherer] Exception with primary loader: {e}")
        data = _fallback_ytdlp(url)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap = 100,
        length_function = len,
        add_start_index = True, 
    )

    chunks = text_splitter.split_documents(data)
    
    if len(chunks) > 500:
        raise ValueError(f"Video is too long ({len(chunks)} chunks). Please use a shorter video.")

    return chunks
