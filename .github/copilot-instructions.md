# Copilot Instructions for my_todo_app

## Project Overview
**my_todo_app** is a FastAPI REST API for managing TODO tasks with user authentication. It uses async PostgreSQL (SQLAlchemy 2.0) and is containerized with Docker.

### Architecture
- **Framework**: FastAPI with async/await throughout
- **Database**: PostgreSQL + SQLAlchemy 2.0 async ORM
- **Authentication**: JWT tokens (Bearer scheme) with Argon2 password hashing
- **Deployment**: Docker Compose with Postgres service and API service
- **Code Organization**: 
  - `main.py` → Route handlers and lifespan events
  - `database.py` → Async engine, session factory, get_db dependency
  - `models.py` → SQLAlchemy ORM models (User, TodoItem)
  - `schemas.py` → Pydantic models for request/response validation
  - `auth.py` → JWT token creation, password hashing, user authentication
  - `crud.py` → Database operations (Create, Read, Update, Delete)

## Critical Patterns & Conventions

### Async/Await Requirements
**ALL database operations, route handlers, and anything using AsyncSession MUST be async.**
```python
# ✓ Correct: Functions with database calls are async
async def get_todos(db: AsyncSession, current_user: User, skip: int = 0, limit: int = 100):
    query = select(TodoItem).filter(TodoItem.owner_id == current_user.id).offset(skip).limit(limit)
    result = await db.execute(query)  # ← AWAIT is critical
    return result.scalars().all()

# ✗ Wrong: Missing async/await will cause "coroutine was never awaited" errors
def get_todos(db: AsyncSession, current_user: User):  # Missing async
    result = db.execute(query)  # Missing await
```

### SQLAlchemy 2.0 Async Query Pattern
Use `select()` with modern filtering syntax, never `filter_by()` in async context:
```python
# ✓ Correct
query = select(TodoItem).filter(TodoItem.owner_id == current_user.id)
result = await db.execute(query)
todos = result.scalars().all()  # For multiple rows
todo = result.scalar_one_or_none()  # For single row

# When committing changes
db.add(new_item)  # or db.delete(item)
await db.commit()
await db.refresh(item)  # Re-fetch updated fields from DB
```

### Route Handler Dependency Injection
All protected routes use `Depends()` with dependencies that must be awaited if async:
```python
@app.get("/todos/", response_model=list[Todo])
async def read_todos(
    skip: int = 0,
    current_user: User = Depends(get_current_user),  # Async dependency
    db: AsyncSession = Depends(get_db)  # Async dependency
):
    todos = await get_todos(db, current_user, skip=skip)  # ← Await CRUD function
    return todos
```

### Authentication Flow
1. **Register/Login**: Username/password → JWT token with `{"sub": username}` claim
2. **Protected Routes**: Token validation via `get_current_user` dependency
3. **Token Expiry**: 30 minutes (ACCESS_TOKEN_EXPIRE_MINUTES in auth.py)
4. **Secrets**: `SECRET_KEY` and credentials in `.env` (use `python-dotenv`)

### Database Session Lifecycle
Use `async with` for transaction control; leverage FastAPI's dependency injection:
```python
async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db  # FastAPI handles request scope
    finally:
        await db.close()  # Always cleanup
```

### Pydantic Schema Structure
- `TodoBase`: Common fields (title, description, completed)
- `TodoCreate`: Inherits TodoBase (for POST requests)
- `TodoUpdate`: All fields Optional (for PATCH requests)
- `Todo`: Inherits TodoBase + id, owner_id (for GET responses)
- Use `from_attributes = True` in Config to convert SQLAlchemy models to Pydantic

## Data Isolation & Security
- **User Isolation**: All CRUD operations filter by `current_user.id` — never return tasks across users
- **Lazy Loading**: Avoid printing SQLAlchemy objects; use `logging` instead (detached session issue)
- **Password Storage**: Never log plain passwords; always use `get_password_hash()`

## Build & Deployment Workflows

### Local Development
```bash
# 1. Create .env with local DATABASE_URL
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/todo_db

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run locally
uvicorn my_todo_app.main:app --reload

# 4. Access docs at http://localhost:8000/docs
```

### Docker Deployment
```bash
# Build and start services (creates tables on first run via lifespan event)
docker-compose up --build

# Database health check via docker-compose ensures API waits for Postgres
# API runs on http://localhost:8000
```

### Database Initialization
Tables are created automatically via FastAPI's `lifespan` event in `main.py`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
```
No manual migration needed for basic operations; use Alembic if schema versioning required.

## Common Pitfalls & Fixes
| Issue | Cause | Fix |
|-------|-------|-----|
| `RuntimeError: Event loop is closed` | Missing `greenlet` on Windows | Already in `requirements.txt` |
| `Coroutine was never awaited` | Route/CRUD function missing `async` | Add `async def` + `await` for all async calls |
| `User isolation failure` | Missing `filter(TodoItem.owner_id == current_user.id)` | Always add owner check in CRUD |
| `Detached session error` | Printing SQLAlchemy object after session close | Use logging module instead |

## File-Specific Notes
- **auth.py** (line ~45): `pwd_context` uses Argon2 (preferred over bcrypt for this project)
- **database.py** (line ~7): Load `DATABASE_URL` from env; defaults to local Postgres
- **main.py** (line ~60): `/login` endpoint expects `application/x-www-form-urlencoded` (OAuth2PasswordRequestForm)
- **models.py** (line ~17): Foreign key `owner_id` enforces user-task relationship
- **schemas.py** (line ~32): `TodoUpdate` has all optional fields for partial updates

## Future Enhancement Patterns
When adding features, follow these established patterns:
- New CRUD operations → Add async functions to `crud.py`, reuse in `main.py` routes
- New validation → Extend Pydantic schemas in `schemas.py` with `Field()` constraints
- New auth checks → Add to `auth.py`, inject via `Depends()` in routes
- New DB tables → Add SQLAlchemy models to `models.py`, extend `Base.metadata.create_all()`
