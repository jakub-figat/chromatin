# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chromatin is a fullstack bioinformatics application for managing biological sequences (DNA, RNA, protein) and organizing them into projects. The backend is built with FastAPI and uses SQLAlchemy with async PostgreSQL for data persistence. The frontend is built with React, TypeScript, and Tailwind CSS. The application includes JWT-based authentication and a modern, responsive UI.

## Repository Structure

The project is split into two main directories:

- **`api/`** - FastAPI backend application
  - All backend code, tests, and configuration
  - Run commands from this directory with `uv run`

- **`client/`** - React frontend application
  - All frontend code and assets
  - Run commands from this directory with `npm`

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

### Background Workers (Celery)

The application uses Celery with Redis for background job processing (alignments, analysis, etc.). Run these commands from the `api/` directory:

```bash
# Start a Celery worker (single process)
uv run celery -A core.celery_app worker --loglevel=info

# Start worker with concurrency (multiple processes for CPU-bound work)
uv run celery -A core.celery_app worker --loglevel=info --concurrency=4

# Start worker with auto-reload (for development - reloads on code changes)
uv run watchfiles "celery -A core.celery_app worker --loglevel=info" .

# Monitor Celery tasks (events)
uv run celery -A core.celery_app events

# Inspect active tasks
uv run celery -A core.celery_app inspect active

# Purge all tasks from queue (careful!)
uv run celery -A core.celery_app purge
```

**Note**: Workers require PostgreSQL and Redis to be running (`docker-compose up -d`).

### Frontend Development

The frontend uses npm for package management. Run these commands from the `client/` directory:

```bash
# Install dependencies
npm install

# Run development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

The Vite dev server proxies `/api` requests to `http://localhost:8000` (FastAPI backend).

## API Conventions

### CamelCase JSON Responses

The API uses **snake_case** in Python code but returns **camelCase** in JSON responses:

- **Backend (Python)**: `user_id`, `is_public`, `created_at`, `sequence_data`
- **Frontend (JSON)**: `userId`, `isPublic`, `createdAt`, `sequenceData`

This is achieved using a `CamelCaseModel` base class in `core/schemas.py`:

```python
class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Accept both snake_case and camelCase in requests
        from_attributes=True,
    )
```

All Pydantic schemas inherit from `CamelCaseModel` instead of `BaseModel`.

### OAuth2 Login Endpoint

The `/api/auth/login` endpoint uses `OAuth2PasswordRequestForm`, which requires:
- **Content-Type**: `application/x-www-form-urlencoded` (NOT JSON)
- **Fields**: `username` and `password` (form fields, not JSON)

The `username` field accepts either email or username for flexible authentication.

**Frontend example**:
```typescript
const formData = new URLSearchParams()
formData.append('username', data.username)
formData.append('password', data.password)

await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: formData,
})
```

## Architecture

### Backend Architecture

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
  - `models.py`: Sequence model with hybrid storage support (DB for small sequences, files for large ones)
  - `enums.py`: SequenceType enum (DNA, RNA, PROTEIN)
  - `routes.py`: Sequence CRUD endpoints including streaming download
  - `service.py`: Sequence business logic with storage service integration
  - `schemas.py`: Sequence request/response schemas (`SequenceListOutput` vs `SequenceDetailOutput`)
  - `fasta_parser.py`: FASTA file parsing utilities

- **`jobs/`** - Background job processing module
  - `models.py`: Job model with status tracking
  - `enums.py`: JobStatus and JobType enums
  - `routes.py`: Job CRUD endpoints (create, list, get, cancel, delete)
  - `service.py`: Job business logic with ownership validation
  - `schemas.py`: Job request/response schemas with discriminated union for job-specific params
  - `tasks.py`: Celery tasks for async job processing

- **`core/storage.py`** - Storage abstraction layer
  - Protocol-based design with `LocalStorageService` (aiofiles) and `S3StorageService` (aioboto3)
  - Async file I/O with streaming support for memory efficiency

- **`core/celery_app.py`** - Celery application configuration
  - Celery app instance with Redis broker and backend
  - Task configuration (serialization, time limits, acks, retries)

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
- **Flexible login**: Users can authenticate with either email or username

### Frontend Architecture

**Tech Stack**:
- **React 18** with TypeScript
- **Vite** for build tooling and dev server
- **Tailwind CSS v3** for styling
- **Shadcn/ui** for UI components (Radix UI primitives)
- **TanStack Query (React Query)** for server state management
- **Zustand** for client state (auth state with localStorage persistence)
- **React Router v6** for routing
- **React Hook Form + Zod** for form validation

**Directory Structure** (`client/src/`):
- **`components/`** - Reusable React components
  - `ui/` - Shadcn/ui components (Button, Input, Card, Dialog, etc.)
  - Feature-specific components (e.g., `project-form-dialog.tsx`)
- **`pages/`** - Route pages (LoginPage, ProjectsPage, etc.)
- **`hooks/`** - Custom React hooks
  - `use-auth.ts` - Authentication hooks (useLogin, useRegister, useLogout)
  - `use-projects.ts` - Project CRUD hooks using TanStack Query
- **`stores/`** - Zustand stores
  - `auth-store.ts` - Authentication state with localStorage persistence
- **`lib/`** - Utilities and configuration
  - `api-client.ts` - API request wrapper with automatic JWT injection
  - `query-provider.tsx` - TanStack Query setup
  - `utils.ts` - Utility functions (e.g., `cn()` for class merging)
- **`types/`** - TypeScript type definitions (auth, projects, sequences)

**Key Features**:
- **Type-safe API client**: All API calls are typed with TypeScript
- **Automatic auth injection**: API client automatically adds JWT token to requests
- **Query caching**: TanStack Query caches server data and handles refetching
- **Protected routes**: `ProtectedRoute` component redirects unauthenticated users
- **Form validation**: Zod schemas validate forms before submission
- **Responsive design**: Tailwind utilities for mobile-first responsive layouts

### Background Jobs Architecture

The application uses **Celery** with **Redis** for asynchronous background job processing (e.g., sequence alignments, analysis):

**Components:**
- **PostgreSQL**: Durable storage for job records (status, params, results)
- **Redis**: Task queue - workers poll for new jobs
- **Celery Workers**: Separate Python processes executing jobs
- **FastAPI**: Creates jobs and dispatches to Celery

**Job Lifecycle:**
1. **API receives request** → Creates job in DB with `PENDING` status
2. **Job dispatched to Celery** → `celery_app.send_task("jobs.process_job", args=[job_id])`
3. **Worker picks up task** → Updates status to `RUNNING` (committed immediately)
4. **Job executes** → Worker processes the job (e.g., runs alignment)
5. **Completion** → Status updated to `COMPLETED` with results, or `FAILED` with error message

**Job Schema (Discriminated Union):**
```python
# Each job type has its own params schema
class PairwiseAlignmentParams(CamelCaseModel):
    job_type: Literal["PAIRWISE_ALIGNMENT"]
    sequence_id_1: int
    sequence_id_2: int

# Union discriminated by job_type field
JobParams = Annotated[
    PairwiseAlignmentParams | OtherJobParams,
    Field(discriminator="job_type"),
]
```

**Task Implementation Pattern:**
```python
# tasks.py
async def _process_job_async(job_id: int):
    async with get_celery_db() as db:
        # Update to RUNNING and commit immediately
        await service.update_job_status(job_id, JobStatus.RUNNING, db)
        await db.commit()

        # Get job and validate params with Pydantic
        job = await service.get_job_internal(job_id, db)
        params = PairwiseAlignmentParams.model_validate(job.params)

        # Process with typed params
        result = await process_pairwise_alignment(params, db)

        # Mark completed and commit
        await service.mark_job_completed(job_id, result, db)
        await db.commit()
```

**Key Features:**
- **Separate DB sessions**: Workers use `@asynccontextmanager get_celery_db()` (not FastAPI deps)
- **Immediate commits**: Status changes committed separately for visibility
- **Type-safe params**: Pydantic schemas validate job params before processing
- **Error handling**: `JobTask` base class auto-marks failed jobs in DB
- **Ownership separation**: `get_job_internal()` bypasses ownership checks for workers

### Hybrid Storage Architecture

Sequences use a **hybrid storage system** to optimize for both small and large sequences:

**Storage Strategy:**
- **Small sequences (< 10KB)**: Stored directly in PostgreSQL `sequence_data` column (VARCHAR 10000)
- **Large sequences (≥ 10KB)**: Stored in files with metadata in database
  - **Development**: Local filesystem using `aiofiles` (`/tmp/chromatin/sequences`)
  - **Production**: S3-compatible object storage using `aioboto3`

**Database Schema:**
```python
class Sequence(Base):
    # Metadata (always in DB)
    name: Mapped[str]
    length: Mapped[int]  # Pre-calculated
    gc_content: Mapped[float | None]  # Pre-calculated
    molecular_weight: Mapped[float | None]  # Pre-calculated
    sequence_type: Mapped[SequenceType]

    # Hybrid storage fields
    sequence_data: Mapped[str | None]  # For sequences < 10KB
    file_path: Mapped[str | None]  # For sequences ≥ 10KB

    @property
    def uses_file_storage(self) -> bool:
        return self.file_path is not None
```

**API Endpoints:**
- `POST /api/sequences/`: Single sequence upload (max 10KB, enforced by Pydantic validator)
- `POST /api/sequences/upload/fasta`: Bulk FASTA upload (any size, hybrid storage per sequence)
- `GET /api/sequences/`: List endpoint returns `SequenceListOutput` (metadata only, no sequence_data)
- `GET /api/sequences/{id}`: Detail endpoint returns `SequenceDetailOutput` (includes sequence_data only if stored in DB)
- `GET /api/sequences/{id}/download`: Streaming FASTA download (works for both DB and file storage)

**Storage Service:**
The `core/storage.py` module provides a protocol-based abstraction:

```python
class StorageService(Protocol):
    async def save(self, content: str, filename: str) -> str: ...
    async def read(self, path: str) -> str: ...
    async def read_chunks(self, path: str, chunk_size: int = 8192) -> AsyncIterator[bytes]: ...
    async def delete(self, path: str) -> None: ...
    async def exists(self, path: str) -> bool: ...
```

**Implementations:**
- `LocalStorageService`: Uses `aiofiles` for async filesystem I/O
- `S3StorageService`: Uses `aioboto3` for async S3 operations

**Memory Efficiency:**
- Downloads use streaming via `StreamingResponse` and `read_chunks()`
- FASTA uploads read files in chunks (FastAPI's `UploadFile` handles this)
- No large sequences are loaded entirely into memory

**File Cleanup:**
- Automatic cleanup on sequence update (if switching from file to DB storage)
- Automatic cleanup on sequence deletion (if file_path exists)
- Best-effort cleanup (failures don't prevent update/delete operations)

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

**Database:**
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`

**Redis/Celery:**
- `REDIS_HOST` (default: localhost)
- `REDIS_PORT` (default: 6379)
- `REDIS_DB` (default: 0)

**Authentication:**
- `SECRET_KEY` (for JWT signing)
- `ALGORITHM` (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30)

**Application:**
- `DEBUG` (default: True)
- `ENVIRONMENT` (DEV or PROD, default: DEV)

**Sequence Storage:**
- `SEQUENCE_SIZE_THRESHOLD` (bytes, default: 10000) - sequences larger than this use file storage

**Local Storage (DEV):**
- `LOCAL_STORAGE_PATH` (default: /tmp/chromatin/sequences)

**S3 Storage (PROD):**
- `S3_BUCKET` (required for PROD environment)
- `S3_REGION` (default: us-east-1)
- `S3_ACCESS_KEY_ID` (optional, uses boto3 default credential chain if not set)
- `S3_SECRET_ACCESS_KEY` (optional, uses boto3 default credential chain if not set)
