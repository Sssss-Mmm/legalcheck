from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from app.core.config import get_settings

from app.api.endpoints import router as api_router
from app.core.database import engine
from app.core.container import get_services
from app.models import Base

# Initialize DB tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load vector store on startup
    services = get_services()
    services.checker.initialize_vector_store()
    yield

app = FastAPI(title="Legal Fact Checker API", lifespan=lifespan)

# CORS origins from config
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 관리자(Admin) 라우터 추가 등록
from app.api.admin import router as admin_router
app.include_router(admin_router)
