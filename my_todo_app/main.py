from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from contextlib import asynccontextmanager
from datetime import timedelta
import os
import shutil
from pathlib import Path
import uuid

from .database import engine, get_db, Base
from .models import User
from .schemas import UserCreate, Token, TodoCreate, TodoUpdate, Todo
from .auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .crud import get_todos, get_todo, create_todo, update_todo, delete_todo

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# Создаем папки для статики, если их нет
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ВАЖНО: Читаем секретный ключ из переменных окружения
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-key-change-in-production")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="TODO App с HTMX",
    lifespan=lifespan
)

templates = Jinja2Templates(directory="templates")

# Используем секретный ключ из env
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Функция для сохранения файлов
async def save_upload_file(upload_file: UploadFile, folder: str = "uploads") -> str:
    """Сохраняет файл и возвращает путь"""
    file_ext = Path(upload_file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / folder / unique_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return f"/static/uploads/{folder}/{unique_filename}"

# ===== HTML ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница (редирект на логин или дашборд)"""
    token = request.session.get("token")
    if token:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница логина"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Главный дашборд с задачами"""
    token = request.session.get("token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        user = await get_current_user(token=token, db=db)
        todos = await get_todos(db, user)
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "todos": todos
        })
    except HTTPException:
        request.session.pop("token", None)
        return RedirectResponse(url="/login", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    """Выход из системы"""
    request.session.pop("token", None)
    return RedirectResponse(url="/login", status_code=303)

# ===== API ROUTES =====

@app.post("/api/register")
async def api_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """API регистрации (для HTMX)"""
    query = select(User).filter(User.username == username)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        return templates.TemplateResponse("partials/error.html", {
            "request": request,
            "error": "Пользователь уже существует"
        }, status_code=400)
    
    hashed_password = get_password_hash(password)
    db_user = User(username=username, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    request.session["token"] = access_token
    
    response = templates.TemplateResponse("partials/success.html", {
        "request": request,
        "message": "Регистрация успешна!"
    })
    response.headers["HX-Redirect"] = "/dashboard"
    return response

@app.post("/api/login")
async def api_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """API логина (для HTMX)"""
    user = await authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("partials/error.html", {
            "request": request,
            "error": "Неверный логин или пароль"
        }, status_code=401)
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    request.session["token"] = access_token
    
    response = templates.TemplateResponse("partials/success.html", {
        "request": request,
        "message": "Вход выполнен!"
    })
    response.headers["HX-Redirect"] = "/dashboard"
    return response

# ===== TODO API (HTMX) =====

@app.post("/api/todos")
async def api_create_todo(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    """Создание задачи через HTMX"""
    token = request.session.get("token")
    if not token:
        raise HTTPException(status_code=401)
    
    user = await get_current_user(token=token, db=db)
    
    image_url = None
    if image and image.filename:
        image_url = await save_upload_file(image, "todos")
    
    todo_data = TodoCreate(title=title, description=description)
    new_todo = await create_todo(db, user, todo_data)
    
    # Обновляем image_url если есть
    if image_url:
        new_todo.image_url = image_url
        await db.commit()
        await db.refresh(new_todo)
    
    return templates.TemplateResponse("partials/todo_item.html", {
        "request": request,
        "todo": new_todo
    })

@app.delete("/api/todos/{todo_id}")
async def api_delete_todo(
    request: Request,
    todo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление задачи через HTMX"""
    token = request.session.get("token")
    if not token:
        raise HTTPException(status_code=401)
    
    user = await get_current_user(token=token, db=db)
    await delete_todo(db, user, todo_id)
    
    return ""  # HTMX удалит элемент из DOM

@app.patch("/api/todos/{todo_id}/toggle")
async def api_toggle_todo(
    request: Request,
    todo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Переключение статуса задачи"""
    token = request.session.get("token")
    if not token:
        raise HTTPException(status_code=401)
    
    user = await get_current_user(token=token, db=db)
    todo = await get_todo(db, user, todo_id)
    
    if not todo:
        raise HTTPException(status_code=404)
    
    todo_update = TodoUpdate(completed=not todo.completed)
    updated_todo = await update_todo(db, user, todo_id, todo_update)
    
    return templates.TemplateResponse("partials/todo_item.html", {
        "request": request,
        "todo": updated_todo
    })

@app.post("/api/upload-avatar")
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Загрузка аватарки"""
    token = request.session.get("token")
    if not token:
        raise HTTPException(status_code=401)
    
    user = await get_current_user(token=token, db=db)
    avatar_url = await save_upload_file(avatar, "avatars")
    
    user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)
    
    return templates.TemplateResponse("partials/avatar.html", {
        "request": request,
        "user": user
    })

# ===== JSON API (для совместимости) =====

@app.post("/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    query = select(User).filter(User.username == user.username)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный username или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/todos/", response_model=list[Todo])
async def read_todos(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    todos = await get_todos(db, current_user, skip=skip, limit=limit)
    return todos

# Health check endpoint (для мониторинга)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}