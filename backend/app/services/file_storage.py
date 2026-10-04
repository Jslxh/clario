import os
import re
import shutil
import tempfile
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseFileStorage(ABC):
    """Abstract base class defining the document file storage interface."""

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal and illegal characters."""
        if not filename:
            return "unnamed_file"
        clean = os.path.basename(filename.replace("\\", "/"))
        clean = clean.replace("\0", "")
        clean = re.sub(r"\.\.+[/\\]", "", clean)
        clean = re.sub(r"[^\w\s\.-]", "_", clean)
        return clean.strip() or "unnamed_file"

    @abstractmethod
    def save_file(self, document_id: str, file_bytes: bytes, extension: str) -> str:
        """Store original uploaded file and return the stored URI or path."""
        pass

    @abstractmethod
    def delete_file_directory(self, document_id: str) -> None:
        """Clean up stored file and its associated directory/prefix."""
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Verify existence of file at specified path or URI."""
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """Read and return raw bytes for the file at the specified path or URI."""
        pass

    @abstractmethod
    def get_local_filepath(self, file_path: str) -> str:
        """Return a readable local filesystem path for parsers."""
        pass


class LocalFileStorage(BaseFileStorage):
    """Local filesystem implementation of document file storage."""

    def __init__(self, base_dir: str = settings.STORAGE_DIR):
        self.base_dir = Path(base_dir) / "documents"

    def save_file(self, document_id: str, file_bytes: bytes, extension: str) -> str:
        """Store original uploaded file under storage/documents/<document_id>/original.<ext>."""
        ext = extension.lstrip(".").lower()
        doc_dir = self.base_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        target_file = doc_dir / f"original.{ext}"

        # Safety check: path traversal prevention
        if not target_file.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError("Path traversal attempt detected in storage path.")

        with open(target_file, "wb") as f:
            f.write(file_bytes)

        logger.info(f"Saved document file locally: {target_file}")
        return str(target_file).replace("\\", "/")

    def delete_file_directory(self, document_id: str) -> None:
        """Clean up stored file directory if database operation fails."""
        doc_dir = self.base_dir / document_id
        if doc_dir.exists() and doc_dir.is_dir():
            shutil.rmtree(doc_dir, ignore_errors=True)
            logger.info(f"Cleaned up local directory: {doc_dir}")

    def file_exists(self, file_path: str) -> bool:
        """Verify existence of file at specified path."""
        path = Path(file_path)
        return path.exists() and path.is_file()

    def read_file(self, file_path: str) -> bytes:
        """Read raw bytes from local filesystem."""
        with open(file_path, "rb") as f:
            return f.read()

    def get_local_filepath(self, file_path: str) -> str:
        """For local storage, the file path is already a local filesystem path."""
        return file_path


class S3FileStorage(BaseFileStorage):
    """S3-compatible object storage provider suitable for Cloudflare R2, AWS S3, and MinIO."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        temp_dir: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME or "clario-documents"
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        self.region_name = region_name or settings.S3_REGION_NAME or "auto"
        self.temp_dir = Path(temp_dir or Path(settings.STORAGE_DIR) / "temp_cache")
        self._s3_client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Lazy initialization of boto3 S3 client."""
        if self._s3_client is None:
            try:
                import boto3
                self._s3_client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=self.region_name,
                )
            except Exception as err:
                logger.error(f"Failed to initialize S3/R2 storage client: {err}")
                raise RuntimeError(f"S3/R2 storage client initialization failed: {err}") from err
        return self._s3_client

    def _extract_key(self, file_path: str) -> str:
        """Normalize s3://bucket/key or raw key string."""
        if file_path.startswith("s3://"):
            parts = file_path[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else parts[0]
        return file_path.lstrip("/")

    def save_file(self, document_id: str, file_bytes: bytes, extension: str) -> str:
        """Store original uploaded file in S3/R2 bucket."""
        ext = extension.lstrip(".").lower()
        key = f"documents/{document_id}/original.{ext}"
        client = self._get_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_bytes,
        )
        uri = f"s3://{self.bucket_name}/{key}"
        logger.info(f"Saved document file to S3/R2: {uri}")
        return uri

    def delete_file_directory(self, document_id: str) -> None:
        """Delete all objects under prefix documents/<document_id>/."""
        client = self._get_client()
        prefix = f"documents/{document_id}/"
        try:
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                items = page.get("Contents", [])
                if items:
                    delete_keys = [{"Key": obj["Key"]} for obj in items]
                    client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={"Objects": delete_keys},
                    )
            logger.info(f"Deleted S3/R2 objects for prefix: {prefix}")
        except Exception as err:
            logger.warning(f"Error deleting S3/R2 objects under {prefix}: {err}")

    def file_exists(self, file_path: str) -> bool:
        """Check if object exists in S3/R2 bucket via head_object."""
        client = self._get_client()
        key = self._extract_key(file_path)
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def read_file(self, file_path: str) -> bytes:
        """Download raw object bytes from S3/R2."""
        client = self._get_client()
        key = self._extract_key(file_path)
        resp = client.get_object(Bucket=self.bucket_name, Key=key)
        return resp["Body"].read()

    def get_local_filepath(self, file_path: str) -> str:
        """Download remote object to temporary local cache for file parsers."""
        key = self._extract_key(file_path)
        local_target = self.temp_dir / key
        local_target.parent.mkdir(parents=True, exist_ok=True)

        if not local_target.exists():
            file_bytes = self.read_file(file_path)
            with open(local_target, "wb") as f:
                f.write(file_bytes)

        return str(local_target)


def get_file_storage_service() -> BaseFileStorage:
    """Storage factory resolving provider based on application configuration."""
    backend = (settings.STORAGE_BACKEND or "local").lower().strip()
    if backend in ("s3", "r2", "cloudflare"):
        logger.info("Initializing S3/Cloudflare R2 document storage backend.")
        return S3FileStorage()
    return LocalFileStorage()


# Default singleton instance and backwards-compatible aliases
file_storage_service: BaseFileStorage = get_file_storage_service()
LocalFileStorageService = LocalFileStorage
FileStorageProtocol = BaseFileStorage
