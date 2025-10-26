"""
Storage service for handling sequence file storage.

Supports both local filesystem (DEV) and S3 (PROD) backends.
"""

from pathlib import Path
from typing import Protocol, AsyncIterator
import uuid

import aiofiles

from core.config import settings, StorageBackend


class StorageService(Protocol):
    """Protocol for storage backends"""

    async def save(self, content: str, filename: str) -> str:
        """
        Save content to storage.

        Args:
            content: String content to save
            filename: Desired filename (will be prefixed with UUID)

        Returns:
            Storage path/key for retrieval
        """
        ...

    async def read(self, path: str) -> str:
        """
        Read content from storage.

        Args:
            path: Storage path/key returned from save()

        Returns:
            String content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    async def read_chunks(self, path: str, chunk_size: int = 8192):
        """
        Read content from storage in chunks (async generator).

        Args:
            path: Storage path/key returned from save()
            chunk_size: Size of chunks in bytes (default 8KB)

        Yields:
            Chunks of file content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    async def delete(self, path: str) -> None:
        """
        Delete file from storage.

        Args:
            path: Storage path/key returned from save()
        """
        ...

    async def exists(self, path: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            path: Storage path/key

        Returns:
            True if file exists
        """
        ...


class LocalStorageService:
    """Local filesystem storage for development using aiofiles"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, content: str, filename: str) -> str:
        """Save to local filesystem"""
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = self.base_path / unique_filename

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)

        return str(file_path.relative_to(self.base_path))

    async def read(self, path: str) -> str:
        """Read from local filesystem"""
        file_path = self.base_path / path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            return await f.read()

    async def read_chunks(
        self, path: str, chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Read from local filesystem in chunks"""
        file_path = self.base_path / path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(chunk_size):
                yield chunk

    async def delete(self, path: str) -> None:
        """Delete from local filesystem"""
        file_path = self.base_path / path

        if file_path.exists():
            file_path.unlink()

    async def exists(self, path: str) -> bool:
        """Check if file exists in local filesystem"""
        file_path = self.base_path / path
        return file_path.exists()


class S3StorageService:
    """S3 storage for production using aioboto3"""

    def __init__(
        self,
        bucket: str,
        region: str,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ):
        self.bucket = bucket
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key

        # Import aioboto3 only when needed (not required for dev)
        try:
            import aioboto3
            from botocore.exceptions import ClientError

            self.aioboto3 = aioboto3
            self.ClientError = ClientError
        except ImportError:
            raise RuntimeError(
                "aioboto3 is required for S3 storage. Install with: uv add aioboto3"
            )

    def _get_session(self):
        """Create aioboto3 session"""
        session_kwargs = {}
        if self.access_key_id and self.secret_access_key:
            session_kwargs = {
                "aws_access_key_id": self.access_key_id,
                "aws_secret_access_key": self.secret_access_key,
            }
        return self.aioboto3.Session(**session_kwargs)

    async def save(self, content: str, filename: str) -> str:
        """Save to S3"""
        unique_key = f"sequences/{uuid.uuid4()}_{filename}"

        session = self._get_session()
        async with session.client("s3", region_name=self.region) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=unique_key,
                Body=content.encode("utf-8"),
                ContentType="text/plain",
            )

        return unique_key

    async def read(self, path: str) -> str:
        """Read from S3"""
        session = self._get_session()
        try:
            async with session.client("s3", region_name=self.region) as s3:
                response = await s3.get_object(Bucket=self.bucket, Key=path)
                async with response["Body"] as stream:
                    return (await stream.read()).decode("utf-8")
        except self.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {path}")
            raise

    async def read_chunks(
        self, path: str, chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Read from S3 in chunks"""
        session = self._get_session()
        try:
            async with session.client("s3", region_name=self.region) as s3:
                response = await s3.get_object(Bucket=self.bucket, Key=path)
                async with response["Body"] as stream:
                    while chunk := await stream.read(chunk_size):
                        yield chunk
        except self.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {path}")
            raise

    async def delete(self, path: str) -> None:
        """Delete from S3"""
        session = self._get_session()
        async with session.client("s3", region_name=self.region) as s3:
            await s3.delete_object(Bucket=self.bucket, Key=path)

    async def exists(self, path: str) -> bool:
        """Check if file exists in S3"""
        session = self._get_session()
        try:
            async with session.client("s3", region_name=self.region) as s3:
                await s3.head_object(Bucket=self.bucket, Key=path)
                return True
        except self.ClientError:
            return False


def get_storage_service() -> StorageService:
    """
    Factory function to get the appropriate storage service based on configuration.

    Returns:
        StorageService instance (LocalStorageService or S3StorageService)
    """
    backend = settings.STORAGE_BACKEND

    if backend == StorageBackend.LOCAL:
        return LocalStorageService(settings.LOCAL_STORAGE_PATH)
    elif backend == StorageBackend.S3:
        if not settings.S3_BUCKET:
            raise ValueError("S3_BUCKET must be set for S3 storage backend")

        return S3StorageService(
            bucket=settings.S3_BUCKET,
            region=settings.S3_REGION,
            access_key_id=settings.S3_ACCESS_KEY_ID,
            secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
    else:
        raise ValueError(f"Unknown storage backend: {backend}")
