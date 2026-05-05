from datetime import date
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from database import engine, get_session
from models import SQLModel, User, Project, Task, ProjectMember, Role, TaskStatus
from schemas import LoginRequest, UserCreate, UserRead, Token, ProjectCreate, ProjectRead, TaskCreate, TaskRead, TaskUpdate, ProjectMemberCreate
from auth import get_password_hash, verify_password, create_access_token, get_current_user, require_admin, get_user_by_email
import os

app = FastAPI(title="Team Task Manager")
app.mount("/static", StaticFiles(directory="static"), name="static")


from sqlalchemy.exc import IntegrityError

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin_exists = session.exec(
            select(User).where(
                (User.email == "admin@example.com") | (User.username == "admin")
            )
        ).first()
        if not admin_exists:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=get_password_hash("Admin123!"),
                role=Role.admin,
            )
            session.add(admin)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")


@app.post("/signup", response_model=UserRead)
def signup(user_in: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where((User.email == user_in.email) | (User.username == user_in.username))).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username already registered")
    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=Role.member,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/login", response_model=Token)
def login(form_data: LoginRequest = Body(...), session: Session = Depends(get_session)):
    try:
        user = session.exec(select(User).where(User.email == form_data.email)).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")
        # Coerce raw string from DB into the Role enum before accessing .value
        if not isinstance(user.role, Role):
            user.role = Role(user.role)
        role_value = user.role.value
        access_token = create_access_token(data={"sub": user.email, "role": role_value})
        return {"access_token": access_token, "token_type": "bearer", "role": role_value}
    except HTTPException:
        raise
    except Exception as ex:
        print('LOGIN ERROR:', repr(ex))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Login error: {ex}")


@app.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/projects", response_model=list[ProjectRead])
def list_projects(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.role == Role.admin:
        projects = session.exec(select(Project)).all()
    else:
        member_projects = session.exec(
            select(Project)
            .join(ProjectMember)
            .where(ProjectMember.user_id == current_user.id)
        ).all()
        projects = member_projects
    return projects


@app.post("/projects", response_model=ProjectRead)
def create_project(project_in: ProjectCreate, current_user: User = Depends(require_admin), session: Session = Depends(get_session)):
    project = Project(name=project_in.name, description=project_in.description, created_by=current_user.id)
    session.add(project)
    session.commit()
    session.refresh(project)
    project_member = ProjectMember(project_id=project.id, user_id=current_user.id)
    session.add(project_member)
    session.commit()
    return project


@app.post("/projects/{project_id}/members")
def add_project_member(project_id: int, member_in: ProjectMemberCreate, current_user: User = Depends(require_admin), session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    user = get_user_by_email(session, member_in.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    exists = session.exec(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
    ).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already assigned to this project")
    project_member = ProjectMember(project_id=project_id, user_id=user.id)
    session.add(project_member)
    session.commit()
    return {"project_id": project_id, "user_id": user.id}


@app.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
def list_project_tasks(project_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if current_user.role != Role.admin:
        membership = session.exec(
            select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id)
        ).first()
        if not membership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    return tasks


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.role == Role.admin:
        tasks = session.exec(select(Task)).all()
    else:
        tasks = session.exec(select(Task).where(Task.assigned_to == current_user.id)).all()
    return tasks


@app.post("/tasks", response_model=TaskRead)
def create_task(task_in: TaskCreate, current_user: User = Depends(require_admin), session: Session = Depends(get_session)):
    project = session.get(Project, task_in.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    assignee = get_user_by_email(session, task_in.assigned_to_email)
    if not assignee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    task = Task(
        title=task_in.title,
        description=task_in.description,
        due_date=task_in.due_date,
        project_id=task_in.project_id,
        assigned_to=assignee.id,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.put("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, task_update: TaskUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.role != Role.admin and task.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this task")
    task.status = task_update.status
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
