# Импорт для HTTP-ошибок, Зависимостей и статусов в FastAPI
from fastapi import HTTPException, status, Depends

# Импорт OAuth2 для обработки форм логина и Bearer-токенов (стандарт FastAPI для auth)
from fastapi.security import OAuth2PasswordBearer

# Импорт Session из SQLAlchemy для работы с БД
from sqlalchemy.ext.asyncio import AsyncSession

# Импорт select для async-запросов (новый стиль SQLAlchemy 2.0)
from sqlalchemy import select

# Импорт CryptContext для хэширования паролей (bcrypt — безопасный алгоритм)
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

# Импорт для JWT (создание/проверка токенов)
from jose import JWTError, jwt

# Импорт для времени (срок жизни токена)
from datetime import datetime, timedelta

# Импорт get_db из database.py (для Depends в get_current_user)
from .database import get_db

# Импорт моделей из нашего models.py (User для БД)
from .models import User

load_dotenv()

# Секретный ключ для подписи JWT (читаем из .env / окружения)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-me")  # Change in prod

# Алгоритм подписи (HS256 — симметричный, простой и безопасный)
ALGORITHM = "HS256"

# Время жизни токена (30 мин)
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Настройка контекста хэширования паролей с использованием argon2
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# Настройка OAuth2 для Bearer-токенов (tokenUrl="login" — роут для получения токена)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Функция для хэширования пароля (plaintext → хэш)
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)  # Теория: Хэш — односторонний, нельзя восстановить пароль

# Функция для проверки пароля (plaintext vs хэш)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)  # Теория: Проверяет совпадение без хранения plaintext

# Функция для поиска пользователя в БД по username (async)
async def get_user(db: AsyncSession, username: str):
    query = select(User).filter(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()  # Теория: SQLAlchemy запрос (SELECT * FROM users WHERE username = ?)

# Функция аутентификации (проверить username/password) (async)
async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user(db, username)  # Теория: await — ждёт результат от async get_user
    if not user or not verify_password(password, user.hashed_password):
        return False  # Теория: Возвращает False, если пользователь не найден или пароль неверный
    return user

# Функция для создания JWT-токена (sync, нет БД)
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Теория: Добавляет "exp" — срок истечения
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # Теория: Encode — создаёт подписанный токен (строка)
    return encoded_jwt

# Функция для проверки токена и получения текущего пользователя (async, потому что использует get_user)
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Теория: Decode — проверяет подпись и срок
        username: str = payload.get("sub")  # "sub" — subject, здесь username
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception  # Теория: Если токен недействителен — ошибка 401
    user = await get_user(db, username)  # Теория: await — ждёт результат от async get_user
    if user is None:
        raise credentials_exception
    return user  # Возвращает объект User для роутов