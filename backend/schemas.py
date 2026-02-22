from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    provider: Optional[str] = None
    provider_id: Optional[str] = None
    image_url: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- ChatMessage Schemas ---
class ChatMessageBase(BaseModel):
    role: str
    content: str

class ChatMessageCreate(ChatMessageBase):
    session_id: int

class ChatMessageResponse(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- ChatSession Schemas ---
class ChatSessionBase(BaseModel):
    title: Optional[str] = None

class ChatSessionCreate(ChatSessionBase):
    user_id: int

class ChatSessionResponse(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True

# --- API Payloads ---
class LoginPayload(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    provider: Optional[str] = None
    provider_id: Optional[str] = None
    image_url: Optional[str] = None
    # Add an ID token here if verifying the token on the backend

class CheckRequest(BaseModel):
    query: str
    session_id: Optional[int] = None
