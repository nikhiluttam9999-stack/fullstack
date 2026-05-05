from datetime import date
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from models import Role, TaskStatus


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Role

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int

    class Config:
        orm_mode = True


class ProjectMemberCreate(BaseModel):
    email: EmailStr


class ProjectMemberRead(BaseModel):
    project_id: int
    user_id: int

    class Config:
        orm_mode = True


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    project_id: int
    assigned_to_email: EmailStr


class TaskRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    due_date: Optional[date]
    project_id: int
    assigned_to: Optional[int]
    assignee: Optional[UserRead] = None

    class Config:
        orm_mode = True


class TaskUpdate(BaseModel):
    status: TaskStatus
