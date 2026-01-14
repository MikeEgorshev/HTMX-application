# Импорт инструментов из SQLAlchemy для определения колонок и типов данных
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey

# Импорт базового класса Base из нашего database.py (относительный импорт с точкой, потому что файлы в одной папке)
from .database import Base

# Класс модели для пользователей (таблица "users" в БД)
class User(Base):
    # Атрибут для имени таблицы в БД — SQLAlchemy использует его для создания таблицы с этим именем
    __tablename__ = "users"

    # Колонка id: уникальный идентификатор, целое число, первичный ключ (авто-инкремент), с индексом для быстрого поиска
    id = Column(Integer, primary_key=True, index=True)

    # Колонка username: строка, уникальная (не может повторяться), с индексом для быстрого поиска по имени
    username = Column(String, unique=True, index=True)

    # Колонка hashed_password: строка для хранения хэшированного пароля (не plaintext для безопасности)
    hashed_password = Column(String)

# Класс модели для задач (таблица "todos" в БД)
class TodoItem(Base):
    # Атрибут для имени таблицы в БД
    __tablename__ = "todos"

    # Колонка id: уникальный идентификатор, как в User
    id = Column(Integer, primary_key=True, index=True)

    # Колонка title: строка для заголовка задачи, с индексом для поиска
    title = Column(String, index=True)

    # Колонка description: строка для описания, nullable=True значит может быть пустой (NULL в БД)
    description = Column(String, nullable=True)

    # Колонка completed: булевое значение (True/False), по умолчанию False (задача не выполнена)
    completed = Column(Boolean, default=False)

    # Колонка owner_id: целое число, foreign key — ссылка на id из таблицы users, для связи "один пользователь — много задач"
    owner_id = Column(Integer, ForeignKey("users.id"))