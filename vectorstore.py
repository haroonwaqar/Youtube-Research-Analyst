from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def create_vector_db(chunks):
    # Initialize the Embedding Model
    embedding = HuggingFaceEmbeddings(
        model_name = "all-MiniLM-L6-v2",
        model_kwargs = {'device': 'mps'}
    )

    # Create the Vector Store    
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        # persist_directory="./chroma_db"
    )

    return vector_db