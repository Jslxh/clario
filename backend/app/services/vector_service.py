import logging
from typing import Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.schemas.vector import QdrantVectorPayload

logger = logging.getLogger(__name__)


class QdrantVectorService:
    """Service abstraction for interacting with the Qdrant vector store."""

    def __init__(self, url: Optional[str] = None, collection_name: Optional[str] = None):
        self.url = url or settings.QDRANT_URL
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self._client: Optional[QdrantClient] = None

    def get_client(self) -> QdrantClient:
        """Lazy initialization of Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(url=self.url, timeout=10.0, check_compatibility=False)
        return self._client

    def check_health(self) -> bool:
        """Verify connectivity to Qdrant server."""
        try:
            client = self.get_client()
            # Fetch cluster/server collections to test connection
            client.get_collections()
            return True
        except Exception as err:
            logger.warning(f"Qdrant health check failed: {err}")
            return False

    def ensure_collection_exists(self, vector_size: Optional[int] = None) -> bool:
        """Create the clario_documents collection if it does not already exist."""
        size = vector_size or settings.QDRANT_VECTOR_SIZE
        try:
            client = self.get_client()
            collections = client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' with vector size {size}...")
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=size,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Collection '{self.collection_name}' created successfully.")
            return True
        except Exception as err:
            logger.error(f"Failed to ensure Qdrant collection '{self.collection_name}': {err}")
            return False

    def validate_payload(self, payload_dict: Dict[str, Any]) -> QdrantVectorPayload:
        """Validate payload metadata structure against the approved Clario schema."""
        return QdrantVectorPayload(**payload_dict)


vector_service = QdrantVectorService()
