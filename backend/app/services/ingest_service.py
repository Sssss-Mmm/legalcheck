import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
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

    # Initialize LLM for summarization
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "다음 텍스트의 내용을 파악하여, 전체 맥락을 이해할 수 있는 핵심적인 '소제목' 1줄과 주요 내용을 요약한 '요약문'을 작성하세요. 이 요약문은 나중에 문서 검색기로 검색할 때 사용되므로, 핵심 키워드와 법률/규정 관련 사실을 잘 포함해야 합니다. 출력은 반드시 다음과 같은 형식으로 작성하세요:\n\n[소제목] (소제목 내용)\n\n[요약]\n(해당 텍스트의 요약 내용)"),
        ("user", "텍스트: {text}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    summary_docs = []
    print(f"Generating summaries for {len(splits)} chunks...")
    for i, split in enumerate(splits):
        try:
            original_text = split.page_content
            # Generate summary
            summary = chain.invoke({"text": original_text})
            
            # Create a new document with summary as page_content and original text in metadata
            new_metadata = split.metadata.copy()
            new_metadata["original_text"] = original_text
            
            summary_docs.append(Document(page_content=summary, metadata=new_metadata))
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}/{len(splits)} chunks")
        except Exception as e:
            print(f"Error processing chunk {i}: {e}")
            # Fallback to original text if summary generation fails
            new_metadata = split.metadata.copy()
            new_metadata["original_text"] = split.page_content
            summary_docs.append(Document(page_content=split.page_content, metadata=new_metadata))

    print("Storing summary documents into Vector Store...")
    vector_store = Chroma.from_documents(
        documents=summary_docs,
        embedding=OpenAIEmbeddings(),
        persist_directory=VECTOR_STORE_PATH
    )
    print(f"Ingested {len(splits)} chunks into {VECTOR_STORE_PATH}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) 
    # __file__ is backend/app/services/ingest_service.py
    # dir: backend/app/services
    # parent: backend/app
    # app parent: backend
    project_root = os.path.dirname(os.path.dirname(current_dir))
    data_dir = os.path.join(project_root, "data")
    
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
