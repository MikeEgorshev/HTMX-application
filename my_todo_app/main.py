# Основной импорт FastAPI
from fastapi import FastAPI, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

# Импорт формы для логина (username/password из form-data)
from fastapi.security import OAuth2PasswordRequestForm

# Импорт для async-запросов (новый стиль SQLAlchemy 2.0)
from sqlalchemy import select

# Импорт для lifespan (новый способ событий)
from contextlib import asynccontextmanager
from datetime import timedelta

# Импорт наших модулей
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Моё TODO-приложение с аутентификацией",
    lifespan=lifespan
)

# Роут регистрации (/register)
@app.post("/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем, существует ли пользователь (async-стиль)
    query = select(User).filter(User.username == user.username)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким username уже существует"
        )
    
    # Хэшируем пароль и добавляем пользователя в БД
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Создаём токен и возвращаем
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Роут логина (/login) - FIXED: added await
@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)  # ← FIXED: added await
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

# Защищённые роуты для задач - FIXED: all functions now async with await

@app.get("/todos/", response_model=list[Todo])
async def read_todos(  # ← FIXED: added async
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    todos = await get_todos(db, current_user, skip=skip, limit=limit)  # ← FIXED: added await
    return todos

@app.get("/todos/{todo_id}", response_model=Todo)
async def read_todo(  # ← FIXED: added async
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    todo = await get_todo(db, current_user, todo_id)  # ← FIXED: added await
    if not todo:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return todo

@app.post("/todos/", response_model=Todo, status_code=201)
async def create_todo_endpoint(  # ← FIXED: added async
    todo: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_todo(db, current_user, todo)  # ← FIXED: added await

@app.patch("/todos/{todo_id}", response_model=Todo)
async def update_todo_endpoint(  # ← FIXED: added async
    todo_id: int,
    todo_update: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    updated_todo = await update_todo(db, current_user, todo_id, todo_update)  # ← FIXED: added await
    if not updated_todo:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return updated_todo

@app.delete("/todos/{todo_id}", response_model=Todo)
async def delete_todo_endpoint(  # ← FIXED: added async
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    deleted_todo = await delete_todo(db, current_user, todo_id)  # ← FIXED: added await
    if not deleted_todo:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return deleted_todo

# Простой роут для проверки (доступен всем)
@app.get("/")
def root():
    return {"message": "Привет! Зайди в /docs для тестирования API"}