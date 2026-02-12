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

## System Architecture
1. **Ingestion Layer:** Extracts transcripts via `youtube-transcript-api`.
2. **Transformation Layer:** Implements `RecursiveCharacterTextSplitter` to maintain semantic integrity across chunks.
3. **Embedding Layer:** Generates 384-dimensional vectors using the local Mac GPU.
4. **Retrieval Layer:** Performs **Cosine Similarity** search to find the top $k$ relevant context chunks.
5. **Generation Layer:** Augments the LLM prompt with retrieved context to produce fact-based answers.
