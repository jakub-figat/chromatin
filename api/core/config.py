from enum import Enum
from pydantic_settings import BaseSettings

from core.consts import MEGABYTE


class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Chromatin"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"

    DEBUG: bool = True

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # For Alembic (sync)
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # JWT/Auth (for later)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Sequence Storage
    ENVIRONMENT: str = "DEV"  # DEV or PROD
    SEQUENCE_SIZE_THRESHOLD: int = (
        10000  # bytes - sequences larger than this use file storage
    )

    # FASTA Upload Limits
    MAX_FASTA_FILE_SIZE: int = 100 * MEGABYTE  # 100MB per file
    MAX_FASTA_UPLOAD_TOTAL_SIZE: int = 500 * MEGABYTE  # 500MB total per upload

    # Local storage (DEV)
    LOCAL_STORAGE_PATH: str = "/tmp/chromatin/sequences"

    # S3 storage (PROD)
    S3_BUCKET: str | None = None
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None

    @property
    def USE_FILE_STORAGE(self) -> bool:
        """Returns True if environment supports file storage (not just database)"""
        return self.ENVIRONMENT in ("DEV", "PROD")

    @property
    def STORAGE_BACKEND(self) -> StorageBackend:
        """Returns StorageBackend.LOCAL for DEV, StorageBackend.S3 for PROD"""
        return StorageBackend.LOCAL if self.ENVIRONMENT == "DEV" else StorageBackend.S3

    class Config:
        env_file = "../.env"
        case_sensitive = True


settings = Settings()
