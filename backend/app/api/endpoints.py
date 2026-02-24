from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import User, ChatSession, ChatMessage, ClaimCheck, VerdictEnum, LawArticleRevision, ExplanationCache
from app.schemas import LoginPayload, UserResponse, CheckRequest
from app.core.database import get_db
from app.services.rag_service import LegalFactChecker
import json

router = APIRouter()
checker = LegalFactChecker()

@router.get("/")
def read_root():
    return {"status": "ok", "message": "Legal Fact Checker API is running"}

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
async def check_fact(request: CheckRequest, user_id: int, db: Session = Depends(get_db)):
    # Validate user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    session_id = request.session_id
    if not session_id:
        chat_session = ChatSession(user_id=user_id, title=request.query[:50])
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        session_id = chat_session.id
    else:
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not chat_session or chat_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Invalid session")

    # Load history
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    history = [{"role": msg.role, "content": msg.content} for msg in messages]

    # Add user message to DB
    user_msg = ChatMessage(session_id=session_id, role="user", content=request.query)
    db.add(user_msg)
    db.commit()

    # Get RAG response
    result = await checker.check_fact_with_history(request.query, history)
    
    # Extract parsed JSON result from LLM
    parsed_result = result["result"]
    verdict_str = parsed_result.get("verdict", "ERROR").upper()
    explanation = parsed_result.get("explanation", "")
    example_case = parsed_result.get("example_case", "")
    caution_note = parsed_result.get("caution_note", "")
    sources = result.get("sources", [])

    # Map string verdict to Enum
    try:
        verdict_enum = VerdictEnum(verdict_str)
    except ValueError:
        verdict_enum = VerdictEnum.PARTIAL # Defaulting on error

    # Save ClaimCheck record
    claim_check = ClaimCheck(
        claim_text=request.query,
        verdict=verdict_enum,
        explanation=explanation
    )
    db.add(claim_check)
    
    # We could link the revision here if our retriever returned the revision IDs.
    # Currently `sources` returns the document source, which could be modified in ingest_service to be the revision_id.
    
    # Add AI message to DB (storing as JSON string for now)
    ai_msg = ChatMessage(session_id=session_id, role="ai", content=json.dumps(parsed_result, ensure_ascii=False))
    db.add(ai_msg)
    db.commit()

    return {
        "session_id": session_id,
        "result": parsed_result,
        "sources": result.get("sources", [])
    }
