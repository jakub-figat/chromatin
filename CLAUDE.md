# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chromatin is a FastAPI-based bioinformatics application for managing biological sequences (DNA, RNA, protein) and organizing them into projects. It uses SQLAlchemy with async PostgreSQL for data persistence and includes JWT-based authentication.

## Development Commands

### Package Management
This project uses `uv` for dependency management. All commands should be run with `uv run`:

```bash
# Install dependencies (handled by uv automatically)
uv sync

# Run the development server
uv run fastapi dev main.py

# Run production server
uv run fastapi run main.py
```

### Testing
```bash
# Run all tests with verbose output
make test
# or: uv run pytest -v

# Run tests with coverage report (HTML and terminal)
make test-cov
# or: uv run pytest --cov=chromatin --cov-report=html --cov-report=term

# Run tests in fail-fast mode (stop on first failure, run failed tests first)
make test-fast
# or: uv run pytest -x --ff

# Run a specific test file
uv run pytest tests/projects/test_project_service.py -v

# Run a specific test function
uv run pytest tests/projects/test_project_service.py::test_function_name -v
```

### Linting and Formatting
```bash
# Check code with ruff
make lint
# or: uv run ruff check

# Format code with ruff
make format
# or: uv run ruff format
```

### Database Migrations
```bash
# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Run migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

### Docker Services
```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

## Architecture

### Module Structure
The codebase follows a feature-based modular architecture:

- **`core/`** - Core application infrastructure
  - `config.py`: Pydantic settings with environment variables (DATABASE_URL, JWT config)
  - `database.py`: SQLAlchemy async engine and `Base` class with auto-timestamped `id`, `created_at`, `updated_at`
  - `deps.py`: FastAPI dependency injection functions (e.g., `get_db()`)
  - `security.py`: JWT token handling, password hashing, `get_current_user()` dependency
  - `exceptions.py`: Custom exception classes (NotFoundError, PermissionDeniedError, ValidationError, ServiceException)

- **`common/`** - User authentication module
  - `models.py`: User model with relationships to sequences and projects
  - `routes.py`: Auth endpoints (register, login)
  - `service.py`: User CRUD and authentication logic
  - `schemas.py`: Pydantic schemas for user data

- **`projects/`** - Project management module
  - `models.py`: Project model with user and sequence relationships
  - `routes.py`: Project CRUD endpoints
  - `service.py`: Project business logic with ownership validation
  - `schemas.py`: Project request/response schemas

- **`sequences/`** - Biological sequence module
  - `models.py`: Sequence model with `@cached_property` methods for `length`, `gc_content`, `molecular_weight`
  - `enums.py`: SequenceType enum (DNA, RNA, PROTEIN)
  - `routes.py`: Sequence CRUD endpoints
  - `service.py`: Sequence business logic
  - `schemas.py`: Sequence request/response schemas

- **`main.py`** - FastAPI application setup with CORS middleware, router registration, and global exception handlers

### Database Architecture

- **ORM**: SQLAlchemy 2.0 with async support (asyncpg driver)
- **Relationships**: All relationships use `lazy="raise"` to prevent N+1 queries - must explicitly load with `selectinload()` or `joinedload()`
- **Base Model**: All models inherit from `Base` which provides `id`, `created_at`, `updated_at` fields automatically
- **Connection**: Async session management through context manager `get_db_session()`

### Testing Architecture

- **Database**: Tests use a separate `chromatin_test` database (automatically created by docker-compose)
- **Test Engine**: Session-scoped test engine with `NullPool` to avoid connection pooling issues
- **Transactions**: Each test runs in a transaction that's rolled back after completion
- **Fixtures** (in `tests/conftest.py`):
  - `test_session`: Function-scoped async session with automatic rollback
  - `client`: AsyncClient with test_session dependency override
  - `test_user`, `test_user_2`, `test_superuser`: Pre-created users
  - `auth_headers`, `superuser_headers`: Authentication headers for requests
  - `current_test_user`, `mock_superuser`: Dependency overrides to bypass authentication
  - `test_project`, `test_sequence`: Pre-created test data

### Authentication & Authorization

- **JWT tokens** generated on login using `python-jose`
- **Password hashing** with Argon2 via `argon2-cffi`
- **`get_current_user()`** dependency extracts and validates JWT tokens from Authorization header
- Services perform **ownership checks** - users can only access/modify their own resources (unless superuser)

## Key Patterns

### Service Layer Pattern
Each module has a service layer that encapsulates business logic:
- Takes `AsyncSession` and validated schemas as input
- Performs database operations and ownership/permission checks
- Raises custom exceptions (NotFoundError, PermissionDeniedError, etc.) which are caught by global handlers
- Returns Pydantic schemas (not ORM models) to routes

### Relationship Loading
Since all relationships use `lazy="raise"`, you must explicitly load related data:
```python
stmt = select(Sequence).where(Sequence.id == seq_id).options(selectinload(Sequence.user))
```

### Testing Pattern
- Use fixtures for common test data
- Override dependencies with `app.dependency_overrides` for bypassing auth
- Use `auth_headers` fixture for endpoint tests requiring authentication
- Always use `test_session` to ensure proper transaction isolation

## Environment Configuration

Required `.env` variables (see `core/config.py`):
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`
- `SECRET_KEY` (for JWT signing)
- `ALGORITHM` (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30)
- `DEBUG` (default: True)
