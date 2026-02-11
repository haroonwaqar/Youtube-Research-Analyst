import os
from dotenv import load_dotenv
from ingestion import get_video_chunks
from vectorstore import create_vector_db
from langchain_groq import ChatGroq
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.retrieval import create_retrieval_chain

load_dotenv()  # This loads the variables from the .env file
API_KEY = os.getenv("GROQ_API_KEY")

question = "What does the professor say about building prototypes?"
url = "https://youtu.be/_NLHFoVNlbg?si=74wDw3vYsOQmYBLd"

def analyst(url ,question):

    chunks = get_video_chunks(url)
    vector_db = create_vector_db(chunks)

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

    # 3. Create the RAG Chain
    # This 'chains' everything together: Retriever -> Prompt -> LLM
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(vector_db.as_retriever(), question_answer_chain)

    # 4. Ask a question!
    user_input = question
    response = rag_chain.invoke({"input": user_input})

    print("\n--- AI RESPONSE ---")
    print(response["answer"])

analyst(url,question)