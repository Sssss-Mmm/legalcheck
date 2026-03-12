from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()

from app.api.endpoints import router as api_router
from app.api.endpoints import checker
from app.core.database import engine
from app.models import Base

# Initialize DB tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load vector store on startup
    checker.initialize_vector_store()
    yield

app = FastAPI(title="Legal Fact Checker API", lifespan=lifespan)

# CORS origins from env variable (comma-separated), fallback to localhost:3000
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 관리자(Admin) 라우터 추가 등록
from app.api.admin import router as admin_router
app.include_router(admin_router)
