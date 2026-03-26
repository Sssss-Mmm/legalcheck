from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from app.models import Law, LawArticle, LawArticleRevision, Topic
from app.schemas.law import (
    LawCreate, LawResponse,
    LawArticleCreate, LawArticleResponse,
    LawArticleRevisionCreate, LawArticleRevisionResponse,
    TopicCreate, TopicResponse
)
from app.core.database import get_db
from app.core.auth import verify_admin
from app.core.container import get_services

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_admin)])

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
        services = get_services()
        background_tasks.add_task(services.checker.add_revisions, [{
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
        services = get_services()
        file_content = await file.read()
        created_articles, embedded_revisions = await services.pdf_parser.process_pdf(db, law_id, file_content)
        
        # 벡터 스토어 업데이트
        background_tasks.add_task(services.checker.add_revisions, embedded_revisions)
        
        return {
            "message": f"Successfully parsed and inserted {len(created_articles)} articles.",
            "articles": created_articles
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"PDF upload failed for law_id={law_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

