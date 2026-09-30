from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str
    department: Optional[str] = None
    role: Optional[str] = "user"  # "admin", "analyst", "user"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
