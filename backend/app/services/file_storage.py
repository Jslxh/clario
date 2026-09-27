import os
import re
import shutil
import logging
from pathlib import Path
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileStorageProtocol(Protocol):
    """Abstract protocol for document file storage providers."""
    
    def save_file(self, document_id: str, file_bytes: bytes, extension: str) -> str:
        ...

    def delete_file_directory(self, document_id: str) -> None:
        ...

    def file_exists(self, file_path: str) -> bool:
        ...


class LocalFileStorageService:
    """Local filesystem implementation of document file storage."""

    def __init__(self, base_dir: str = settings.STORAGE_DIR):
        self.base_dir = Path(base_dir) / "documents"

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal and illegal characters."""
        if not filename:
            return "unnamed_file"
        
        # Remove path separators and null bytes
        clean = os.path.basename(filename.replace("\\", "/"))
        clean = clean.replace("\0", "")
        # Remove any path traversal constructs
        clean = re.sub(r"\.\.+[/\\]", "", clean)
        # Keep alphanumeric, dots, dashes, underscores, spaces
        clean = re.sub(r"[^\w\s\.-]", "_", clean)
        return clean.strip() or "unnamed_file"

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

        logger.info(f"Saved document file: {target_file}")
        return str(target_file)

    def delete_file_directory(self, document_id: str) -> None:
        """Clean up stored file directory if database operation fails."""
        doc_dir = self.base_dir / document_id
        if doc_dir.exists() and doc_dir.is_dir():
            shutil.rmtree(doc_dir, ignore_errors=True)
            logger.info(f"Cleaned up directory: {doc_dir}")

    def file_exists(self, file_path: str) -> bool:
        """Verify existence of file at specified path."""
        path = Path(file_path)
        return path.exists() and path.is_file()


file_storage_service = LocalFileStorageService()
