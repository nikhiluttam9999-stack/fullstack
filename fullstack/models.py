from datetime import date
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column
from sqlalchemy.types import Enum as SqlEnum
from typing import Optional, List


class Role(str, Enum):
    admin = "Admin"
    member = "Member"


class ProjectMember(SQLModel, table=True):
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: Role = Field(
        sa_column=Column(
            SqlEnum(
                Role,
                values_callable=lambda enum: [item.value for item in enum],
                native_enum=False,
            ),
            default=Role.member,
        ),
        nullable=False,
    )

    projects: List["Project"] = Relationship(back_populates="members", link_model=ProjectMember)
    assigned_tasks: List["Task"] = Relationship(back_populates="assignee")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    created_by: int = Field(foreign_key="user.id")

    members: List[User] = Relationship(back_populates="projects", link_model=ProjectMember)
    tasks: List["Task"] = Relationship(back_populates="project")


class TaskStatus(str, Enum):
    pending = "Pending"
    in_progress = "In Progress"
    completed = "Completed"


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    status: TaskStatus = Field(
        default=TaskStatus.pending,
        sa_column=Column(
            SqlEnum(
                TaskStatus,
                values_callable=lambda enum: [item.value for item in enum],
                native_enum=False,
            ),
            default=TaskStatus.pending,
        ),
        nullable=False,
    )
    due_date: Optional[date] = None
    project_id: int = Field(foreign_key="project.id")
    assigned_to: Optional[int] = Field(default=None, foreign_key="user.id")

    project: Optional[Project] = Relationship(back_populates="tasks")
    assignee: Optional[User] = Relationship(back_populates="assigned_tasks")
