import os
from langchain_huggingface import HuggingFaceEmbeddings # Free & Local
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def ingest_notes(file_path):
    # 1. Load the PDF
    loader = PyPDFLoader(file_path)
    data = loader.load()

    # 2. Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(data)

    # 3. Store in the SAME database main.py uses
    persist_directory = "./db"
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    print(f"Successfully added {len(chunks)} units to the AURA vault.")