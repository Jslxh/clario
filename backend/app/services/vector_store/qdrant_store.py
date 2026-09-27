import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.schemas.vector import QdrantVectorPayload
from app.services.vector_store.base import BaseVectorStore
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class QdrantVectorStore(BaseVectorStore):
    """Vector store abstraction for Qdrant database integration."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        expected_dimension: Optional[int] = None,
    ):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.expected_dimension = expected_dimension or settings.EMBEDDING_DIMENSION

    def _get_client(self) -> QdrantClient:
        return vector_service.get_client()

    def verify_collection(self) -> bool:
        """Ensure Qdrant collection exists with proper 384-dimension configuration."""
        try:
            return vector_service.ensure_collection_exists(vector_size=self.expected_dimension)
        except Exception as err:
            logger.error(f"Collection verification failed for '{self.collection_name}': {err}")
            raise RuntimeError(f"Qdrant collection verification failed: {err}") from err

    def upsert_chunk_vectors(
        self,
        chunk_points: List[Dict[str, Any]],
    ) -> bool:
        """Upsert a list of chunk points to Qdrant idempotently using chunk UUID as Point ID.
        
        Each point item in chunk_points must contain:
        - "point_id": str (chunk UUID)
        - "vector": List[float] (384-dim vector)
        - "payload": Dict[str, Any] matching QdrantVectorPayload
        """
        if not chunk_points:
            return True

        self.verify_collection()

        qdrant_points: List[qmodels.PointStruct] = []
        for idx, item in enumerate(chunk_points):
            point_id = item["point_id"]
            vector = item["vector"]
            raw_payload = item["payload"]

            # Validate vector dimension
            if len(vector) != self.expected_dimension:
                err_msg = (
                    f"Vector dimension mismatch at point {point_id}: "
                    f"expected {self.expected_dimension}, got {len(vector)}"
                )
                logger.error(err_msg)
                raise ValueError(err_msg)

            # Validate payload schema
            validated_payload = vector_service.validate_payload(raw_payload)

            qdrant_points.append(
                qmodels.PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload=validated_payload.model_dump(),
                )
            )

        client = vector_service.get_client()
        try:
            client.upsert(
                collection_name=self.collection_name,
                points=qdrant_points,
                wait=True,
            )
            logger.info(
                f"Successfully upserted {len(qdrant_points)} vector points to Qdrant collection '{self.collection_name}'."
            )
            return True
        except Exception as err:
            logger.error(f"Failed to upsert vector points to Qdrant: {err}")
            raise RuntimeError(f"Qdrant vector upsert failure: {err}") from err

    def upsert_vectors(self, points: List[Dict[str, Any]]) -> bool:
        return self.upsert_chunk_vectors(points)


qdrant_vector_store = QdrantVectorStore()
