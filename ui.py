import streamlit as st
from main import analyst 

# Page Configuration
st.set_page_config(page_title="YouTube Research Analyst", page_icon="", layout="centered")

st.title("YouTube Research Analyst")
st.markdown("""
    Summarize long technical lectures and ask specific questions.\n 
    *Powered by Llama 3.3 & ChromaDB.*
""")

# Sidebar for Settings
with st.sidebar:
    st.header("Settings")
    video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/...")
    st.info("This tool uses RAG to analyze the video transcript locally on your Mac's GPU.")

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Ask something about the video..."):
    if not video_url:
        st.error("Please enter a YouTube URL in the sidebar first!")
    else:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate AI Response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing transcript..."):
                try:
                    # Calling your refactored logic
                    result = analyst(video_url, prompt)
                    response_text = result["answer"]
                    st.markdown(response_text)
                    
                    # Add AI response to history
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"An error occurred: {e}")