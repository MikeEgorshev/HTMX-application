# Импорт async-двигателя и сессий
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv  # Новый импорт для .env

# Загружаем .env (локально) или env vars (в Docker)
load_dotenv()

# URL из env, default для fallback (matches docker-compose for local dev)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/todo_db"  # Локальный default
)

# Async engine — для async подключений
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# Async фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

# Базовый класс (тот же)
Base = declarative_base()

# Async get_db (генератор для Depends)
async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()  # await для async закрытия