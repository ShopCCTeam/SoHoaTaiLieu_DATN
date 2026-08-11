"""Storage service abstraction (MinIO S3 & Local / Memory fallback)."""

from __future__ import annotations

import io
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from structlog import get_logger

from app.core.config import get_settings

logger = get_logger(__name__)


class StorageService(ABC):
    @abstractmethod
    async def upload_file(
        self, file_bytes: bytes, object_key: str, content_type: str = "application/pdf"
    ) -> str:
        """Upload file bytes and return file URL or object key."""
        pass

    @abstractmethod
    async def download_file(self, object_key: str) -> bytes:
        """Download file bytes by object key."""
        pass

    @abstractmethod
    async def delete_file(self, object_key: str) -> None:
        """Delete object key."""
        pass


class LocalStorageService(StorageService):
    """Local disk storage implementation (used for dev/testing/fallback)."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is None:
            base_dir = Path(tempfile.gettempdir()) / "ctsv-storage"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self, file_bytes: bytes, object_key: str, content_type: str = "application/pdf"
    ) -> str:
        target_path = self.base_dir / object_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(file_bytes)
        logger.info("local_storage_upload", path=str(target_path), size=len(file_bytes))
        return f"/storage/{object_key}"

    async def download_file(self, object_key: str) -> bytes:
        clean_key = object_key.replace("/storage/", "")
        target_path = self.base_dir / clean_key
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {object_key}")
        return target_path.read_bytes()

    async def delete_file(self, object_key: str) -> None:
        clean_key = object_key.replace("/storage/", "")
        target_path = self.base_dir / clean_key
        if target_path.exists():
            target_path.unlink()
            logger.info("local_storage_delete", path=str(target_path))


class MinioStorageService(StorageService):
    """MinIO S3 storage implementation."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def upload_file(
        self, file_bytes: bytes, object_key: str, content_type: str = "application/pdf"
    ) -> str:
        try:
            from minio import Minio  # type: ignore[import-not-found]

            client = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key.get_secret_value(),
                secure=self.settings.minio_secure,
            )
            bucket = self.settings.minio_bucket
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)

            client.put_object(
                bucket_name=bucket,
                object_name=object_key,
                data=io.BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type,
            )
            return f"s3://{bucket}/{object_key}"
        except Exception as e:
            logger.warning("minio_upload_fallback_local", error=str(e))
            fallback = LocalStorageService()
            return await fallback.upload_file(file_bytes, object_key, content_type)

    async def download_file(self, object_key: str) -> bytes:
        try:
            from minio import Minio

            client = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key.get_secret_value(),
                secure=self.settings.minio_secure,
            )
            bucket = self.settings.minio_bucket
            clean_key = object_key.replace(f"s3://{bucket}/", "").replace("/storage/", "")
            response = client.get_object(bucket, clean_key)
            try:
                return bytes(response.read())
            finally:
                response.close()
                response.release_conn()
        except Exception as e:
            logger.warning("minio_download_fallback_local", error=str(e))
            fallback = LocalStorageService()
            return await fallback.download_file(object_key)

    async def delete_file(self, object_key: str) -> None:
        try:
            from minio import Minio

            client = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key.get_secret_value(),
                secure=self.settings.minio_secure,
            )
            bucket = self.settings.minio_bucket
            clean_key = object_key.replace(f"s3://{bucket}/", "").replace("/storage/", "")
            client.remove_object(bucket, clean_key)
        except Exception as e:
            logger.warning("minio_delete_fallback_local", error=str(e))
            fallback = LocalStorageService()
            await fallback.delete_file(object_key)


_storage_instance: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        settings = get_settings()
        if settings.app_env == "test":
            _storage_instance = LocalStorageService()
        else:
            _storage_instance = MinioStorageService()
    return _storage_instance
