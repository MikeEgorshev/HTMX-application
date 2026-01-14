#Теория: CRUD — это 4 основные операции с данными:

#Create — создать задачу
#Read — прочитать (список или одну задачу)
#Update — обновить задачу
#Delete — удалить задачу

# Импорт сессии из SQLAlchemy (для async)
from sqlalchemy.ext.asyncio import AsyncSession

# Импорт select для запросов (новый стиль SQLAlchemy 2.0)
from sqlalchemy import select

# Импорт наших моделей (TodoItem и User)
from .models import TodoItem, User

# Импорт Pydantic-схем для валидации и ответов
from .schemas import TodoCreate, TodoUpdate

# Функция для получения всех задач текущего пользователя (async версия)
async def get_todos(db: AsyncSession, current_user: User, skip: int = 0, limit: int = 100):
    query = select(TodoItem).filter(TodoItem.owner_id == current_user.id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

# Функция для получения одной задачи по id (async)
async def get_todo(db: AsyncSession, current_user: User, todo_id: int):
    query = select(TodoItem).filter(TodoItem.id == todo_id, TodoItem.owner_id == current_user.id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

# Функция для создания новой задачи (async)
async def create_todo(db: AsyncSession, current_user: User, todo: TodoCreate):
    db_todo = TodoItem(**todo.model_dump(), owner_id=current_user.id)
    db.add(db_todo)
    await db.commit()
    await db.refresh(db_todo)
    # FIXED: Removed print that was causing lazy load issues
    # If you need logging, use: logging.info(f"Created todo for user {current_user.id}")
    return db_todo

# Функция для обновления задачи (async)
async def update_todo(db: AsyncSession, current_user: User, todo_id: int, todo_update: TodoUpdate):
    db_todo = await get_todo(db, current_user, todo_id)
    if not db_todo:
        return None
    update_data = todo_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_todo, key, value)
    await db.commit()
    await db.refresh(db_todo)
    return db_todo

# Функция для удаления задачи (async)
async def delete_todo(db: AsyncSession, current_user: User, todo_id: int):
    db_todo = await get_todo(db, current_user, todo_id)
    if not db_todo:
        return None
    db.delete(db_todo)
    await db.commit()
    return db_todo