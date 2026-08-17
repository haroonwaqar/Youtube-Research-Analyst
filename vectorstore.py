import os
import hashlib
import time
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import re

INDEX_NAME = "yt-research-analyst"

def extract_video_id(url):
    """Extracts the 11-character YouTube video ID from standard or shortened URLs."""
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    return url

def get_embedding_model():
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN environment variable is missing! Please add it to your .env file or Heroku Config Vars.")
        
    return HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        task="feature-extraction",
        huggingfacehub_api_token=hf_token
    )

def _init_pinecone():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY variable is missing!")
    
    pc = Pinecone(api_key=api_key)
    
    # Check if index exists, create if not
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        print(f"[Pinecone] Creating index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=384, # Output dimension for all-MiniLM-L6-v2
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        # Wait for index to be ready
        while not pc.describe_index(INDEX_NAME).status['ready']:
            time.sleep(1)
            
    return pc

def check_namespace_exists(url):
    """Check if a video's transcript has already been embedded."""
    pc = _init_pinecone()
    index = pc.Index(INDEX_NAME)
    video_id = extract_video_id(url)
    namespace = "yt_" + hashlib.md5(video_id.encode()).hexdigest()
    
    stats = index.describe_index_stats()
    if "namespaces" in stats and namespace in stats["namespaces"]:
        # Check if vector count > 0
        if stats["namespaces"][namespace]["vector_count"] > 0:
            return True
    return False

def store_vector_db(chunks, url):
    """Embed and store chunks into Pinecone under a unique namespace."""
    _init_pinecone()
    video_id = extract_video_id(url)
    namespace = "yt_" + hashlib.md5(video_id.encode()).hexdigest()
    embedding = get_embedding_model()
    
    print(f"[Pinecone] Uploading {len(chunks)} chunks to namespace '{namespace}'...")
    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embedding,
        index_name=INDEX_NAME,
        namespace=namespace
    )

def get_vector_db(url):
    """Return a Pinecone Vector Store instance pointing to a specific namespace."""
    video_id = extract_video_id(url)
    namespace = "yt_" + hashlib.md5(video_id.encode()).hexdigest()
    embedding = get_embedding_model()
    
    return PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embedding,
        namespace=namespace
    )