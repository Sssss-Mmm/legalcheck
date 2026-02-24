from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.law import VerdictEnum

# --- Topic Schemas ---
class TopicBase(BaseModel):
    name: str
    description: Optional[str] = None

class TopicCreate(TopicBase):
    pass

class TopicResponse(TopicBase):
    id: int

    class Config:
        from_attributes = True

# --- ExplanationCache Schemas ---
class ExplanationCacheBase(BaseModel):
    plain_summary: str
    example_case: Optional[str] = None
    caution_note: Optional[str] = None

class ExplanationCacheCreate(ExplanationCacheBase):
    article_revision_id: int

class ExplanationCacheResponse(ExplanationCacheBase):
    id: int
    article_revision_id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# --- LawArticleRevision Schemas ---
class LawArticleRevisionBase(BaseModel):
    content: str
    effective_start_date: date
    effective_end_date: Optional[date] = None
    summary_plain: Optional[str] = None
    amendment_note: Optional[str] = None

class LawArticleRevisionCreate(LawArticleRevisionBase):
    article_id: int

class LawArticleRevisionResponse(LawArticleRevisionBase):
    id: int
    article_id: int
    explanation_caches: List[ExplanationCacheResponse] = []

    class Config:
        from_attributes = True

# --- LawArticle Schemas ---
class LawArticleBase(BaseModel):
    article_number: str
    title: Optional[str] = None
    is_active: bool = True

class LawArticleCreate(LawArticleBase):
    law_id: int

class LawArticleResponse(LawArticleBase):
    id: int
    law_id: int
    topics: List[TopicResponse] = []
    # Optionally include active revision summary if needed, keeping simple for now

    class Config:
        from_attributes = True

# --- Law Schemas ---
class LawBase(BaseModel):
    name: str
    short_name: Optional[str] = None
    jurisdiction: str = "KR"

class LawCreate(LawBase):
    pass

class LawResponse(LawBase):
    id: int
    created_at: datetime
    # Optionally load articles

    class Config:
        from_attributes = True

# --- ClaimCheck Schemas ---
class ClaimCheckBase(BaseModel):
    claim_text: str
    verdict: VerdictEnum
    explanation: str

class ClaimCheckCreate(ClaimCheckBase):
    # To link with revisions
    revision_ids: List[int]

class ClaimCheckResponse(ClaimCheckBase):
    id: int
    created_at: datetime
    revisions: List[LawArticleRevisionResponse] = []

    class Config:
        from_attributes = True
