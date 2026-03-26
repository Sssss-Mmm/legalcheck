import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.models import User, ChatSession, ChatMessage, ClaimCheck, LawArticleRevision, LawArticle, Law
from app.schemas import LoginPayload, UserResponse, CheckRequest, TemplateRequest, TemplateResponse
from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.core.container import get_services

logger = logging.getLogger(__name__)

router = APIRouter()


# --- DI 헬퍼 함수 (lazy 로딩) ---
def _get_check_service():
    """CheckService 인스턴스를 lazy하게 반환합니다."""
    return get_services().check_service


def _get_template_generator():
    """DocumentTemplateGenerator 인스턴스를 lazy하게 반환합니다."""
    return get_services().template_generator


@router.get("/")
def read_root():
    return {"status": "ok", "message": "Legal Fact Checker API is running"}

@router.get("/search/articles")
def search_articles(query: str = Query(..., description="검색할 키워드"), db: Session = Depends(get_db)):
    """조문 키워드 검색 API (실시간 API 연동 하이브리드)"""
    from app.plugins.law_db import search_law_articles
    
    api_results = search_law_articles(law_name=query, keyword="", limit=50)
    
    results = []
    
    is_api_error = False
    if len(api_results) == 1 and api_results[0].get("조문번호") == "-":
        is_api_error = True

    if api_results and not is_api_error:
        for idx, res in enumerate(api_results):
            content_preview = f"[{res['조문제목']}] {res['조문내용']}"
            if len(content_preview) > 500:
                content_preview = content_preview[:500] + "..."
                
            results.append({
                "law_name": res["법령명"],
                "article_number": res["조문번호"],
                "content": content_preview,
                "revision_id": f"api_{idx}"
            })
    else:
        # N+1 쿼리 해결: joinedload로 연관 엔티티를 미리 로드
        revisions = (
            db.query(LawArticleRevision)
            .options(
                joinedload(LawArticleRevision.article).joinedload(LawArticle.law)
            )
            .filter(LawArticleRevision.content.ilike(f"%{query}%"))
            .limit(10)
            .all()
        )
        for rev in revisions:
            article = rev.article
            law = article.law if article else None
            results.append({
                "law_name": law.name if law else "Unknown",
                "article_number": article.article_number if article else "Unknown",
                "content": rev.content[:200] + "...",
                "revision_id": rev.id
            })
            
    return {"results": results}

@router.post("/auth/login", response_model=UserResponse)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        user = User(
            email=payload.email,
            name=payload.name,
            provider=payload.provider,
            provider_id=payload.provider_id,
            image_url=payload.image_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.post("/check")
async def check_fact(
    request: CheckRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    check_service=Depends(_get_check_service),
):
    # Validate user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    session_id = request.session_id
    if session_id:
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not chat_session or chat_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Invalid session")

    # 비즈니스 로직은 CheckService에 위임
    return await check_service.execute(
        db=db,
        user_id=user_id,
        query=request.query,
        session_id=session_id,
        image_data=getattr(request, "image_data", None),
    )

@router.get("/sessions")
def get_user_sessions(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(desc(ChatSession.updated_at)).all()
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "is_bookmarked": s.is_bookmarked,
                "updated_at": s.updated_at
            } for s in sessions
        ]
    }

@router.get("/sessions/{session_id}")
def get_session_details(session_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    
    formatted_messages = []
    for msg in messages:
        if msg.role == "user":
            formatted_messages.append({"role": "user", "content": msg.content})
        else:
            try:
                data = json.loads(msg.content)
                formatted_messages.append({"role": "ai", "content": "", **data})
            except (json.JSONDecodeError, TypeError, ValueError):
                formatted_messages.append({"role": "ai", "content": msg.content})
                
    return {
        "id": session.id,
        "title": session.title,
        "is_bookmarked": session.is_bookmarked,
        "messages": formatted_messages
    }

@router.post("/sessions/{session_id}/bookmark")
def toggle_bookmark(session_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_bookmarked = not session.is_bookmarked
    db.commit()
    return {"id": session.id, "is_bookmarked": session.is_bookmarked}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return {"status": "ok", "message": "Session deleted"}

@router.get("/claims/popular")
def get_popular_claims(db: Session = Depends(get_db)):
    popular = db.query(ClaimCheck.claim_text, func.count(ClaimCheck.id).label('count'))\
                .group_by(ClaimCheck.claim_text)\
                .order_by(desc(func.count(ClaimCheck.id)))\
                .limit(5).all()
    return {"popular_claims": [p.claim_text for p in popular]}

@router.post("/claims/template", response_model=TemplateResponse)
async def generate_document_template(
    request: TemplateRequest,
    template_generator=Depends(_get_template_generator),
):
    try:
        result = await template_generator.generate_template(request.claim_text, request.explanation)
        return TemplateResponse(
            document_title=result.get("document_title", "법적 대응 문서 초안"),
            document_content=result.get("document_content", "문서 생성에 실패했습니다.")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

