from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role_name: str
    is_active: int = 1


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role_name: str
    is_active: int
    created_at: Optional[datetime] = None


class TokenData(BaseModel):
    user_id: int
    username: str
    role_name: str