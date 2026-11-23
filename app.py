import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

st.set_page_config(page_title="AI Electronics Assistant", page_icon="⚡", layout="wide")

# Initialize session state for responses
if "tab1_response" not in st.session_state:
    st.session_state.tab1_response = ""
if "tab2_response" not in st.session_state:
    st.session_state.tab2_response = ""
if "tab3_response" not in st.session_state:
    st.session_state.tab3_response = ""

st.title("⚡ AI Electronics Design & Debugging Assistant")
st.markdown("Your smart assistant for electronics engineering, hardware troubleshooting, and component recommendations.")

# Try to get the API key
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key or google_api_key == "your_gemini_api_key_here":
    st.error("Please set your GOOGLE_API_KEY in the .env file.")
    st.stop()

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=google_api_key)

@st.cache_resource
def init_vector_store():
    # Ensure Datasheets directory exists
    if not os.path.exists("Datasheets"):
        os.makedirs("Datasheets")
        
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    loader = PyPDFDirectoryLoader("Datasheets")
    docs = loader.load()
    
    if not docs:
        return None, embeddings
        
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    
    # Ensure db directory exists
    if not os.path.exists("db"):
        os.makedirs("db")
        
    vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
    vectorstore.save_local("./db")
    return vectorstore, embeddings

with st.spinner("Initializing system and loading datasheets (if any)..."):
    try:
        vectorstore, embeddings = init_vector_store()
    except Exception as e:
        st.error(f"Error initializing vector store: {e}")
        vectorstore = None

# Tabs for the features
tab1, tab2, tab3 = st.tabs(["📚 Datasheet QA", "🛠️ Hardware Troubleshooting", "💡 Component Recommendation"])

# Feature 1: Datasheet QA
with tab1:
    st.header("Datasheet Question Answering")
    st.markdown("Ask questions about the components whose datasheets are loaded in the `Datasheets` folder.")
    if vectorstore is None:
        st.warning("No datasheets found or processed. Please add PDF files to the 'Datasheets' folder and restart the app.")
    else:
        user_question = st.text_input("Ask a question about your components:")
        if st.button("Ask"):
            if user_question:
                with st.spinner("Searching datasheets..."):
                    retriever = vectorstore.as_retriever()
                    system_prompt = (
                        "You are an expert electronics engineer assistant. "
                        "Use the following pieces of retrieved context to answer the user's question. "
                        "If you don't know the answer, say that you don't know. "
                        "\n\nContext: {context}"
                    )
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", system_prompt),
                        ("human", "{input}"),
                    ])
                    question_answer_chain = create_stuff_documents_chain(llm, prompt)
                    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                    
                    response = rag_chain.invoke({"input": user_question})
                    st.session_state.tab1_response = response["answer"]
            else:
                st.warning("Please ask a question first.")
                
        if st.session_state.tab1_response:
            st.write(st.session_state.tab1_response)

# Feature 2: Hardware Troubleshooting
with tab2:
    st.header("Hardware Troubleshooting Assistant")
    st.markdown("Describe the symptoms of your hardware issue, and the AI will help you debug it.")
    symptoms = st.text_area("Describe the hardware symptoms (e.g., MQ2 output always HIGH, LPC2148 not detected):")
    if st.button("Diagnose Issue"):
        if symptoms:
            with st.spinner("Diagnosing..."):
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are an expert electronics debugging engineer. The user will provide hardware symptoms. You should identify possible causes, suggest debugging steps, and provide engineering recommendations. Be concise and structured. Do NOT reference any uploaded documents or say 'based on the provided context' - rely solely on your internal knowledge."),
                    ("human", "{symptoms}")
                ])
                chain = prompt | llm
                response = chain.invoke({"symptoms": symptoms})
                st.session_state.tab2_response = response.content
        else:
            st.warning("Please describe the symptoms first.")
            
    if st.session_state.tab2_response:
        st.write(st.session_state.tab2_response)

# Feature 3: Component Recommendation
with tab3:
    st.header("Smart Component Recommendation System")
    st.markdown("Describe what you want to build, and the AI will suggest suitable components.")
    project_reqs = st.text_area("Describe your project requirements (e.g., I want to build a wireless temperature monitoring system):")
    if st.button("Get Recommendations"):
        if project_reqs:
            with st.spinner("Generating recommendations..."):
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are an expert electronics design assistant. The user will provide project requirements. You should recommend suitable electronic components (microcontrollers, sensors, modules, etc.) and provide brief design advice. Be concise and structured. Do NOT reference any uploaded documents or say 'based on the provided context' - rely solely on your internal knowledge."),
                    ("human", "{requirements}")
                ])
                chain = prompt | llm
                response = chain.invoke({"requirements": project_reqs})
                st.session_state.tab3_response = response.content
        else:
            st.warning("Please provide your project requirements first.")
            
    if st.session_state.tab3_response:
        st.write(st.session_state.tab3_response)
