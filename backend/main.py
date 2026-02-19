from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

from pydantic import BaseModel
from contextlib import asynccontextmanager
from rag import LegalFactChecker

class CheckRequest(BaseModel):
    query: str

checker = LegalFactChecker()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load vector store on startup
    checker.initialize_vector_store()
    yield

from fastapi.middleware.cors import CORSMiddleware

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

@app.post("/check")
async def check_fact(request: CheckRequest):
    result = await checker.check_fact(request.query)
    return result
