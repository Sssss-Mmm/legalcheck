from pydantic import BaseModel
from typing import Optional

class TemplateRequest(BaseModel):
    claim_text: str
    explanation: str

class TemplateResponse(BaseModel):
    document_title: str
    document_content: str
