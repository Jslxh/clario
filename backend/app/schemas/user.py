import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleRead(RoleBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    email: EmailStr
    name: str
    department: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    roles: List[RoleRead] = []

    model_config = ConfigDict(from_attributes=True)
