import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


# =====================================================
# CONFIGURATION
# =====================================================

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(
    page_title="ResearchMind AI",
    page_icon="🧠",
    layout="wide"
)


# =====================================================
# CUSTOM UI
# =====================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 42px;
        font-weight: 800;
        color: #4A90E2;
        margin-bottom: 0px;
    }

    .subtitle {
        color: gray;
        font-size: 17px;
        margin-top: 0px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<p class="main-title">🧠 ResearchMind AI</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="subtitle">Advanced AI Research Assistant for PDF Understanding, Summarization, Flashcards, MCQs, and Source-Based Q&A</p>',
    unsafe_allow_html=True
)


# =====================================================
# SESSION STATE
# =====================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "chunks" not in st.session_state:
    st.session_state.chunks = []

if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""

if "processed_file_names" not in st.session_state:
    st.session_state.processed_file_names = []

if "document_summary" not in st.session_state:
    st.session_state.document_summary = ""

if "flashcards" not in st.session_state:
    st.session_state.flashcards = ""

if "mcqs" not in st.session_state:
    st.session_state.mcqs = ""


# =====================================================
# HELPER FUNCTIONS
# =====================================================

@st.cache_resource(show_spinner=False)
def load_embeddings():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return embeddings


def get_llm(model_name, temperature):
    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name=model_name,
        temperature=temperature
    )
    return llm


def extract_text_from_pdfs(uploaded_files):
    full_text = ""

    for uploaded_file in uploaded_files:
        pdf_reader = PdfReader(uploaded_file)
        file_name = uploaded_file.name

        for page_number, page in enumerate(pdf_reader.pages, start=1):
            extracted_text = page.extract_text()

            if extracted_text:
                full_text += f"\n\n[Source: {file_name}, Page: {page_number}]\n"
                full_text += extracted_text

    return full_text


def build_vector_store(full_text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", " "]
    )

    chunks = text_splitter.split_text(full_text)

    embeddings = load_embeddings()

    vector_store = FAISS.from_texts(
        chunks,
        embedding=embeddings
    )

    return vector_store, chunks


def run_llm(prompt, model_name, temperature):
    llm = get_llm(model_name, temperature)
    response = llm.invoke(prompt)
    return response.content


def create_download_text():
    conversation = "ResearchMind AI Chat Export\n"
    conversation += f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    for message in st.session_state.messages:
        role = message["role"].upper()
        content = message["content"]
        conversation += f"{role}:\n{content}\n\n"

    return conversation


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.header("⚙️ Settings")

    model_name = st.selectbox(
        "Choose Groq Model",
        [
            "llama-3.3-70b-versatile",
            "deepseek-r1-distill-llama-70b",
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant"
        ],
        index=0
    )

    temperature = st.slider(
        "Creativity / Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.1
    )

    k_value = st.slider(
        "Number of Source Chunks",
        min_value=1,
        max_value=10,
        value=5
    )

    st.divider()

    uploaded_files = st.file_uploader(
        "📄 Upload PDF Files",
        type="pdf",
        accept_multiple_files=True
    )

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    if st.button("🔄 Reset Documents"):
        st.session_state.vector_store = None
        st.session_state.chunks = []
        st.session_state.raw_text = ""
        st.session_state.processed_file_names = []
        st.session_state.document_summary = ""
        st.session_state.flashcards = ""
        st.session_state.mcqs = ""
        st.rerun()


# =====================================================
# API KEY CHECK
# =====================================================

if not GROQ_API_KEY:
    st.error("Missing GROQ_API_KEY. Please add it to your .env file.")
    st.code("GROQ_API_KEY=your_groq_api_key_here")
    st.stop()


# =====================================================
# PDF PROCESSING
# =====================================================

if uploaded_files:
    current_file_names = []

    for uploaded_file in uploaded_files:
        current_file_names.append(uploaded_file.name)

    if current_file_names != st.session_state.processed_file_names:
        with st.spinner("Reading and processing PDFs..."):
            raw_text = extract_text_from_pdfs(uploaded_files)

            vector_store, chunks = build_vector_store(raw_text)

            st.session_state.raw_text = raw_text
            st.session_state.vector_store = vector_store
            st.session_state.chunks = chunks
            st.session_state.processed_file_names = current_file_names

        st.success("✅ PDFs processed successfully!")


# =====================================================
# PROJECT METRICS
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Uploaded PDFs", len(st.session_state.processed_file_names))

with col2:
    st.metric("Text Chunks", len(st.session_state.chunks))

with col3:
    st.metric("Chat Messages", len(st.session_state.messages))


# =====================================================
# RESEARCH TOOLS
# =====================================================

st.divider()
st.subheader("🛠️ Research Tools")

tool_col1, tool_col2, tool_col3 = st.columns(3)

with tool_col1:
    if st.button("📘 Generate Summary"):
        if not st.session_state.raw_text:
            st.warning("Please upload and process a PDF first.")
        else:
            with st.spinner("Generating document summary..."):
                prompt = f"""
You are an expert academic research assistant.

Create a university-level summary of the document.

Include:
1. Main topic
2. Key ideas
3. Important findings
4. Technical terms explained simply
5. Short exam/revision notes

DOCUMENT:
{st.session_state.raw_text[:18000]}
"""
                st.session_state.document_summary = run_llm(
                    prompt,
                    model_name,
                    temperature
                )

with tool_col2:
    if st.button("🧠 Generate Flashcards"):
        if not st.session_state.raw_text:
            st.warning("Please upload and process a PDF first.")
        else:
            with st.spinner("Generating flashcards..."):
                prompt = f"""
Create high-quality study flashcards from this document.

Format exactly like this:

Q1: ...
A1: ...

Q2: ...
A2: ...

Make them useful for revision.

DOCUMENT:
{st.session_state.raw_text[:15000]}
"""
                st.session_state.flashcards = run_llm(
                    prompt,
                    model_name,
                    temperature
                )

with tool_col3:
    if st.button("📝 Generate MCQs"):
        if not st.session_state.raw_text:
            st.warning("Please upload and process a PDF first.")
        else:
            with st.spinner("Generating MCQs..."):
                prompt = f"""
Generate 15 exam-style multiple choice questions from this document.

For each question include:
- Question
- Four options: A, B, C, D
- Correct answer
- Short explanation

DOCUMENT:
{st.session_state.raw_text[:15000]}
"""
                st.session_state.mcqs = run_llm(
                    prompt,
                    model_name,
                    temperature
                )


# =====================================================
# DISPLAY GENERATED CONTENT
# =====================================================

if st.session_state.document_summary:
    with st.expander("📘 Document Summary", expanded=False):
        st.markdown(st.session_state.document_summary)

if st.session_state.flashcards:
    with st.expander("🧠 Flashcards", expanded=False):
        st.markdown(st.session_state.flashcards)

if st.session_state.mcqs:
    with st.expander("📝 MCQs", expanded=False):
        st.markdown(st.session_state.mcqs)


# =====================================================
# CHAT DISPLAY
# =====================================================

st.divider()
st.subheader("💬 Chat with Your PDFs")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =====================================================
# CHAT INPUT
# =====================================================

user_question = st.chat_input("Ask a question from your PDFs...")

if user_question:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_question
        }
    )

    with st.chat_message("user"):
        st.markdown(user_question)

    if st.session_state.vector_store is None:
        with st.chat_message("assistant"):
            warning_message = "⚠️ Please upload at least one PDF before asking questions."
            st.warning(warning_message)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": warning_message
                }
            )

    else:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    docs = st.session_state.vector_store.similarity_search(
                        user_question,
                        k=k_value
                    )

                    context = "\n\n".join(
                        [doc.page_content for doc in docs]
                    )

                    prompt = f"""
You are ResearchMind AI, an advanced academic PDF research assistant.

Rules:
- Answer ONLY using the provided PDF context.
- If the answer is not present, say: "I could not find this information in the uploaded PDF."
- Explain clearly and logically.
- Use bullet points where helpful.
- Mention important terms and explain them simply.
- Avoid hallucination.

PDF CONTEXT:
{context}

USER QUESTION:
{user_question}

FINAL ANSWER:
"""

                    answer = run_llm(
                        prompt,
                        model_name,
                        temperature
                    )

                    st.markdown(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

                    with st.expander("📚 Source Chunks Used"):
                        for i, doc in enumerate(docs, start=1):
                            st.markdown(f"### Source Chunk {i}")
                            st.write(doc.page_content[:1800])

                except Exception as e:
                    error_message = f"Error: {e}"
                    st.error(error_message)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_message
                        }
                    )


# =====================================================
# EXPORT CHAT
# =====================================================

st.divider()

if st.session_state.messages:
    export_text = create_download_text()

    st.download_button(
        label="💾 Download Chat History",
        data=export_text,
        file_name=f"researchmind_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )

st.caption("🚀 Powered by Streamlit + LangChain + FAISS + HuggingFace Embeddings + Groq")