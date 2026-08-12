from langchain_community.document_loaders import YoutubeLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Get the video transcript and split into chunks
def get_video_chunks(url):

    loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
    data = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap = 100,
        length_function = len,
        add_start_index = True, # This helps to track where in the video the chunk is!
    )

    chunks = text_splitter.split_documents(data)
    
    if len(chunks) > 500:
        raise ValueError(f"Video is too long ({len(chunks)} chunks). Please use a shorter video.")

    return chunks
