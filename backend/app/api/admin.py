from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os

from app.models import Law, LawArticle, LawArticleRevision, Topic, ExplanationCache
from app.schemas.law import (
    LawCreate, LawResponse,
    LawArticleCreate, LawArticleResponse,
    LawArticleRevisionCreate, LawArticleRevisionResponse,
    TopicCreate, TopicResponse
)
from app.core.database import get_db

# For PDF extraction
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/laws", response_model=LawResponse)
def create_law(law: LawCreate, db: Session = Depends(get_db)):
    db_law = Law(**law.model_dump())
    db.add(db_law)
    db.commit()
    db.refresh(db_law)
    return db_law

@router.post("/articles", response_model=LawArticleResponse)
def create_article(article: LawArticleCreate, db: Session = Depends(get_db)):
    db_article = LawArticle(**article.model_dump())
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article

@router.post("/revisions", response_model=LawArticleRevisionResponse)
def create_revision(revision: LawArticleRevisionCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_revision = LawArticleRevision(**revision.model_dump())
    db.add(db_revision)
    db.commit()
    db.refresh(db_revision)
    
    article = db.query(LawArticle).filter(LawArticle.id == revision.article_id).first()
    if article:
        law = db.query(Law).filter(Law.id == article.law_id).first()
        from app.services.rag_service import LegalFactChecker
        checker = LegalFactChecker()
        background_tasks.add_task(checker.add_revisions, [{
            "law_id": article.law_id,
            "article_id": article.id,
            "revision_id": db_revision.id,
            "content": db_revision.content,
            "law_name": law.name if law else "Unknown",
            "article_number": article.article_number
        }])
    
    return db_revision

@router.post("/topics", response_model=TopicResponse)
def create_topic(topic: TopicCreate, db: Session = Depends(get_db)):
    db_topic = Topic(**topic.model_dump())
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    return db_topic

# --- PDF Upload & Parsing Endpoint ---

class ParsedArticle(BaseModel):
    article_number: str = Field(description="조문 번호. 예: 제36조")
    title: str = Field(description="조문 제목. 예: 임금 지급")
    content: str = Field(description="조문 내용 전체")

class ParsedLaw(BaseModel):
    articles: List[ParsedArticle] = Field(description="추출된 법 조문 목록")

@router.post("/laws/{law_id}/upload_pdf")
async def upload_law_pdf(law_id: int, background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    법률 PDF 파일을 업로드하면 LLM을 이용해 조문별로 텍스트를 분리하고 DB에 자동 삽입합니다.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    law = db.query(Law).filter(Law.id == law_id).first()
    if not law:
        raise HTTPException(status_code=404, detail="Law not found")

    try:
        # Save uploaded file to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Load PDF using PyPDFLoader
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()
        full_text = "\n".join([doc.page_content for doc in documents])
        
        # NOTE: For very large PDFs, sending the entire text to LLM might exceed context limits.
        # In a real-world scenario, you'd chunk this or use a regex-based approach first.
        # For this MVP, we use gpt-4o-mini with structured output on a (presumably) reasonably sized text.
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "당신은 법률 문서 파싱 전문가입니다. 입력된 텍스트에서 각 조문(예: '제1조(목적) ...')을 분리하여 리스트 형태로 추출하세요."),
            ("user", "텍스트:\n{text}")
        ])
        
        parser = JsonOutputParser(pydantic_object=ParsedLaw)
        chain = prompt | llm | parser
        
        # Taking only first 20000 chars to avoid overwhelming the mini model if the file is massive.
        # This is a safety measure for the pilot.
        text_to_process = full_text[:40000] 
        
        parsed_result = chain.invoke({"text": text_to_process})
        
        created_articles = []
        embedded_revisions = []
        from datetime import date
        
        # Insert extracted articles into DB
        for article_data in parsed_result.get("articles", []):
            # Create LawArticle
            db_article = LawArticle(
                law_id=law_id,
                article_number=article_data["article_number"],
                title=article_data["title"],
                is_active=True
            )
            db.add(db_article)
            db.flush() # To get the article ID
            
            # Create LawArticleRevision
            db_revision = LawArticleRevision(
                article_id=db_article.id,
                content=article_data["content"],
                effective_start_date=date.today(), # Defaulting to today for MVP
                effective_end_date=None
            )
            db.add(db_revision)
            db.flush() # To get the revision ID
            
            created_articles.append({
                "article_number": db_article.article_number,
                "title": db_article.title
            })
            
            embedded_revisions.append({
                "law_id": law_id,
                "article_id": db_article.id,
                "revision_id": db_revision.id,
                "content": db_revision.content,
                "law_name": law.name,
                "article_number": db_article.article_number
            })
            
        db.commit()
        
        # Trigger vector store update for the new revisions
        from app.services.rag_service import LegalFactChecker
        checker = LegalFactChecker()
        background_tasks.add_task(checker.add_revisions, embedded_revisions)
        
        return {
            "message": f"Successfully parsed and inserted {len(created_articles)} articles.",
            "articles": created_articles
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
