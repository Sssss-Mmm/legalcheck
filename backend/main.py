from fastapi import FastAPI, Depends, HTTPException
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

load_dotenv()

from rag import LegalFactChecker
import models
import schemas
from database import engine, get_db

# Initialize DB tables
models.Base.metadata.create_all(bind=engine)

checker = LegalFactChecker()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load vector store on startup
    checker.initialize_vector_store()
    yield

app = FastAPI(title="Legal Fact Checker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Legal Fact Checker API is running"}

@app.post("/auth/login", response_model=schemas.UserResponse)
def login(payload: schemas.LoginPayload, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        user = models.User(
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

@app.post("/check")
async def check_fact(request: schemas.CheckRequest, user_id: int, db: Session = Depends(get_db)):
    # Validate user
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    session_id = request.session_id
    if not session_id:
        chat_session = models.ChatSession(user_id=user_id, title=request.query[:50])
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        session_id = chat_session.id
    else:
        chat_session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
        if not chat_session or chat_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Invalid session")

    # Load history
    messages = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id).order_by(models.ChatMessage.created_at).all()
    history = [{"role": msg.role, "content": msg.content} for msg in messages]

    # Add user message to DB
    user_msg = models.ChatMessage(session_id=session_id, role="user", content=request.query)
    db.add(user_msg)
    db.commit()

    # Get RAG response
    result = await checker.check_fact_with_history(request.query, history)

    # Add AI message to DB
    ai_msg = models.ChatMessage(session_id=session_id, role="ai", content=result["result"])
    db.add(ai_msg)
    db.commit()

    return {
        "session_id": session_id,
        "result": result["result"],
        "sources": result.get("sources", [])
    }
