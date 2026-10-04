import os
import uuid
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.file_storage import (
    BaseFileStorage,
    LocalFileStorage,
    S3FileStorage,
    get_file_storage_service,
)


def test_local_storage_crud_and_traversal_protection(tmp_path):
    """Test LocalFileStorage save, read, exists, local path, and path traversal protection."""
    storage = LocalFileStorage(base_dir=str(tmp_path))
    doc_id = str(uuid.uuid4())
    content = b"Local file storage test payload."

    # 1. Save file
    saved_path = storage.save_file(document_id=doc_id, file_bytes=content, extension="txt")
    assert os.path.exists(saved_path)
    assert storage.file_exists(saved_path) is True

    # 2. Read file
    read_bytes = storage.read_file(saved_path)
    assert read_bytes == content

    # 3. Get local filepath
    local_path = storage.get_local_filepath(saved_path)
    assert local_path == saved_path

    # 4. Path traversal attempt raises ValueError
    with pytest.raises(ValueError, match="Path traversal attempt"):
        storage.save_file(document_id="../escaped_dir", file_bytes=content, extension="txt")

    # 5. Delete directory
    storage.delete_file_directory(doc_id)
    assert storage.file_exists(saved_path) is False


def test_s3_storage_crud_mocked(tmp_path):
    """Test S3FileStorage save, exists, read, local cache download, and directory cleanup."""
    import sys
    mock_boto3 = MagicMock()
    mock_boto3_client = MagicMock()
    mock_boto3.client.return_value = mock_boto3_client

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        s3_storage = S3FileStorage(
            bucket_name="test-clario-bucket",
            endpoint_url="https://fake-account-id.r2.cloudflarestorage.com",
            access_key_id="fake-key",
            secret_access_key="fake-secret",
            temp_dir=str(tmp_path / "temp_cache"),
        )

        doc_id = str(uuid.uuid4())
        content = b"S3/R2 mock file bytes content."

        # 1. Save file
        uri = s3_storage.save_file(document_id=doc_id, file_bytes=content, extension="pdf")
        assert uri == f"s3://test-clario-bucket/documents/{doc_id}/original.pdf"
        mock_boto3_client.put_object.assert_called_once_with(
            Bucket="test-clario-bucket",
            Key=f"documents/{doc_id}/original.pdf",
            Body=content,
        )

        # 2. File exists
        mock_boto3_client.head_object.return_value = {"ContentLength": len(content)}
        assert s3_storage.file_exists(uri) is True
        mock_boto3_client.head_object.assert_called_with(
            Bucket="test-clario-bucket",
            Key=f"documents/{doc_id}/original.pdf",
        )

        # 3. Read file
        mock_body = MagicMock()
        mock_body.read.return_value = content
        mock_boto3_client.get_object.return_value = {"Body": mock_body}
        downloaded = s3_storage.read_file(uri)
        assert downloaded == content

        # 4. Get local filepath (downloads remote S3 object into local cache)
        local_fp = s3_storage.get_local_filepath(uri)
        assert os.path.exists(local_fp)
        with open(local_fp, "rb") as f:
            assert f.read() == content

        # 5. Delete directory (paginates objects and deletes)
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": f"documents/{doc_id}/original.pdf"}]}
        ]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        s3_storage.delete_file_directory(doc_id)
        mock_boto3_client.delete_objects.assert_called_once_with(
            Bucket="test-clario-bucket",
            Delete={"Objects": [{"Key": f"documents/{doc_id}/original.pdf"}]},
        )


def test_storage_factory_selection(monkeypatch):
    """Test get_file_storage_service resolves LocalFileStorage or S3FileStorage based on STORAGE_BACKEND."""
    # 1. Default local
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    service_local = get_file_storage_service()
    assert isinstance(service_local, LocalFileStorage)

    # 2. S3/R2 backend
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "r2")
    service_r2 = get_file_storage_service()
    assert isinstance(service_r2, S3FileStorage)

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    service_s3 = get_file_storage_service()
    assert isinstance(service_s3, S3FileStorage)
