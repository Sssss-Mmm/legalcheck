import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

VECTOR_STORE_PATH = "chroma_db"

def ingest_data(file_paths: list[str]):
    documents = []
    for path in file_paths:
        if path.endswith(".pdf"):
            loader = PyPDFLoader(path)
        else:
            loader = TextLoader(path)
        documents.extend(loader.load())

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)

    vector_store = Chroma.from_documents(
        documents=splits,
        embedding=OpenAIEmbeddings(),
        persist_directory=VECTOR_STORE_PATH
    )
    print(f"Ingested {len(splits)} chunks into {VECTOR_STORE_PATH}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    
    if not os.path.exists(data_dir):
        print(f"Data directory not found: {data_dir}")
        exit(1)
        
    pdf_files = [
        os.path.join(data_dir, f) 
        for f in os.listdir(data_dir) 
        if f.lower().endswith(".pdf")
    ]
    
    if pdf_files:
        print(f"Found {len(pdf_files)} PDF files: {pdf_files}")
        ingest_data(pdf_files)
    else:
        print("No PDF files found in data directory.")
