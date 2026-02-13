# YouTube Research Analyst

A Retrieval-Augmented Generation (RAG) application that allows users to have semantically grounded conversations with YouTube video transcripts. Built with **LangChain**, **ChromaDB**, and **Groq**, optimized for **Apple Silicon GPU (MPS)**.

## Features
- **Semantic Retrieval:** Uses high-dimensional vector embeddings to understand the context of questions, moving beyond simple keyword matching.
- **Hardware Optimized:** Leverages **Metal Performance Shaders (MPS)** on Mac M-series chips for accelerated local embedding generation.
- **High-Speed Inference:** Integrated with **Groq (Llama 3.3)** to provide sub-second conversational responses.
- **Modular Architecture:** Clean separation of concerns between Data Ingestion, Vector Storage, and Application Logic.
- **Resource Caching:** Implements intelligent caching to prevent redundant processing of the same video.

## Tech Stack
- **Framework:** LangChain (LCEL)
- **LLM:** Llama 3.3 (via Groq)
- **Vector Database:** ChromaDB
- **Embeddings:** HuggingFace `all-MiniLM-L6-v2` (Local)
- **UI:** Streamlit
- **Environment:** Python 3.13

## How it Works (The Pipeline)

1. **Ingestion Layer:** Utilizing the youtube transcript api to extract raw text data directly from video transcripts.
2. **Transformation Layer:** Employs a **RecursiveCharacterTextSplitter** with a specific chunk size and overlap. This ensures that technical concepts aren't lost between fragments, maintaining **semantic integrity**.
3. **Embedding Layer:** Converts text chunks into **384-dimensional vectors** using the hugging face model. This process is offloaded to the **local Mac GPU (MPS)** for high-speed parallel processing.
4. **Retrieval Layer:** When a query is made, **ChromaDB** calculates the **Cosine Similarity** between the question's vector and the stored transcript vectors to identify the top $k$ most relevant context pieces.
5. **Generation Layer:** The retrieved context is injected into a custom system prompt. This context-rich prompt is then sent to **Llama 3.3 (via Groq)** to generate an accurate, fact-grounded response.

## Screenshot
### The Stanford CS230 Lecture 1: Introduction to Deep Learning is used here to demonstrate the tool. 
![Home](<screenshots/img1.png>)
![Home](<screenshots/img2.png>)
![Home](<screenshots/img3.png>)
Link to the Youtube Lecture: <https://youtu.be/_NLHFoVNlbg?si=1zlZg1D3vukTZMNe>