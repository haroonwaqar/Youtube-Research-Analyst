import os
import streamlit as st
from dotenv import load_dotenv
from dataGatherer import get_video_chunks
from vectorStore import create_vector_db
from langchain_groq import ChatGroq
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.retrieval import create_retrieval_chain

load_dotenv()  # This loads the variables from the .env file
API_KEY = os.getenv("GROQ_API_KEY")

# question = "Teach me the main topics of this?"
# url = "https://youtu.be/_NLHFoVNlbg?si=74wDw3vYsOQmYBLd"

@st.cache_resource
def get_cached_vector_db(url):
    """
    This function will only run ONCE per unique URL.
    It saves the ChromaDB object in memory.
    """

    chunks = get_video_chunks(url)
    db = create_vector_db(chunks)
    return db

# main function 
def analyst(url ,question):
    # Instead of creating a new DB, we get the cached one
    vector_db = get_cached_vector_db(url)

    llm = ChatGroq(
        model="llama-3.3-70b-versatile", 
        temperature=0,
        groq_api_key=API_KEY
        )

    system_prompt = (
        "You are an expert research assistant. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know. "
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # Create the RAG Chain
    # This 'chains' everything together: Retriever -> Prompt -> LLM
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(vector_db.as_retriever(), question_answer_chain)

    # 4. Ask a question!
    user_input = question
    response = rag_chain.invoke({"input": user_input})

    return response