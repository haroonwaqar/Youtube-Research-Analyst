import os
from apify_client import ApifyClient
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def get_video_chunks(url):
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        raise ValueError("APIFY_API_TOKEN environment variable is missing!")
        
    client = ApifyClient(apify_token)
    
    print(f"[dataGatherer] Fetching transcript via Apify Cloud Scraper...")
    run_input = { "videoUrls": [url] }
    
    try:
        run = client.actor("sauliusautomatesit/youtube-transcript-scraper").call(run_input=run_input)
        
        # In newer apify-client versions, run is a Pydantic object with snake_case attributes
        if hasattr(run, "default_dataset_id"):
            dataset_id = run.default_dataset_id
        elif hasattr(run, "get") and callable(run.get):
            dataset_id = run.get("defaultDatasetId", run.get("default_dataset_id"))
        elif hasattr(run, "__getitem__"):
            dataset_id = run["defaultDatasetId"]
        else:
            dataset_id = getattr(run, "defaultDatasetId", getattr(run, "default_dataset_id", None))
            
        if not dataset_id:
            raise ValueError(f"Could not find default_dataset_id in the Apify run response. Response type: {type(run)}")
            
        full_text = ""
        for item in client.dataset(dataset_id).iterate_items():
            # Robust schema extraction because different actors return different JSON schemas
            if "transcript" in item:
                transcript_data = item["transcript"]
                if isinstance(transcript_data, list):
                    if len(transcript_data) > 0 and isinstance(transcript_data[0], dict):
                        full_text = " ".join([t.get('text', t.get('subtitle', '')) for t in transcript_data])
                    else:
                        full_text = " ".join(str(t) for t in transcript_data)
                elif isinstance(transcript_data, str):
                    full_text = transcript_data
            elif "text" in item:
                full_text += item["text"] + " "
            elif "subtitles" in item:
                # Another common schema key
                subtitles = item["subtitles"]
                if isinstance(subtitles, list) and isinstance(subtitles[0], dict):
                    full_text = " ".join([t.get('text', '') for t in subtitles])
                
        if not full_text:
            raise ValueError(f"Could not extract transcript text from Apify. Ensure the video has closed captions enabled.")
            
    except Exception as e:
        raise ValueError(f"Failed to fetch transcript via Apify. Error: {e}")
        
    data = [Document(page_content=full_text, metadata={"source": url})]

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
