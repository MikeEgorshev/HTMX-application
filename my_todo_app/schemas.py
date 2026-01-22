# Импорт базового класса от Pydantic для создания схем (моделей данных)
from pydantic import BaseModel, Field

# Импорт Optional для опциональных полей (может быть None)
from typing import Optional

#
from datetime import datetime

# Схема для базовых данных пользователя (для чтения/ответов)
class User(BaseModel):
    # Поле username: обязательное, тип str
    username: str

    # Тип строки адреса аватарки
    avatar_url: Optional[str] = None

    # Настройка: from_attributes = True — позволяет конвертировать SQLAlchemy-объект в Pydantic-схему
    class Config:
        from_attributes = True  # Важно для интеграции с моделями БД (автоматическая конвертация атрибутов)

# Схема для создания пользователя (регистрация)
class UserCreate(User):
    # Наследуем от User (username), добавляем password: обязательное, str
    password: str = Field(..., min_length=8, max_length=72)

# Схема для токена (ответ на логин/регистрацию)
class Token(BaseModel):
    # Поле access_token: JWT-токен, str
    access_token: str
    # Поле token_type: тип токена, всегда "bearer"
    token_type: str

# Базовая схема для задач (общие поля)
class TodoBase(BaseModel):
    # title: обязательное, str
    title: str
    # description: опциональное (Optional[str] = None), может быть None
    description: Optional[str] = None
    # completed: булево, по умолчанию False
    completed: bool = False

# Схема для создания задачи (наследуем от TodoBase)
class TodoCreate(TodoBase):
    pass  # Ничего не добавляем — используем базовые поля

# Схема для обновления задачи (частичного)
class TodoUpdate(TodoBase):
    # Все поля опциональные (Optional), чтобы обновлять только нужное
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

# Схема для чтения задачи (ответ клиенту)
class Todo(TodoBase):
    # Добавляем id: обязательное, int (генерит БД)
    id: int
    # owner_id: int, для показа владельца
    owner_id: int

    # Путь до картинки = str or None
    image_url: Optional[str] = None
    # Дата создания
    created_at: datetime
    # Дата обновления
    updated_at: Optional[datetime] = None

    # Настройка: from_attributes = True — для конвертации из SQLAlchemy-модели
    class Config:
        from_attributes = True