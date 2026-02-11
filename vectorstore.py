from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def create_vector_db(chunks):
    # 1. Initialize the Embedding Model
    # We use a Mac-specific 'model_kwargs' to force it onto the GPU
    embedding = HuggingFaceEmbeddings(
        model_name = "all-MiniLM-L6-v2",
        model_kwargs = {'device': 'mps'}
    )

    # 2. Create the Vector Store
    # 'persist_directory' saves the data to your disk so you don't have to re-embed every time

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory="./chroma_db"
    )

    return vector_db