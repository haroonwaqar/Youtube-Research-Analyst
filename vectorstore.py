import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def _get_device():
    """Auto-detect best available device: MPS (Mac GPU) > CUDA > CPU."""
    if torch.backends.mps.is_available():
        return 'mps'
    elif torch.cuda.is_available():
        return 'cuda'
    return 'cpu'

def create_vector_db(chunks):
    device = _get_device()
    print(f"[vectorStore] Using device: {device}")

    # Initialize the Embedding Model
    embedding = HuggingFaceEmbeddings(
        model_name = "all-MiniLM-L6-v2",
        model_kwargs = {'device': device}
    )

    # Create the Vector Store    
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        # persist_directory="./chroma_db"
    )

    return vector_db