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

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute similarity search against Qdrant collection with optional payload filtering.
        
        Args:
            query_vector: 384-dimensional normalized vector.
            top_k: Max candidate results to return.
            filters: Optional payload filter key-value pairs (department, document_type, access_level, document_id).
            
        Returns:
            List of dicts: [{"point_id": str, "score": float, "payload": dict}]
        """
        if len(query_vector) != self.expected_dimension:
            err_msg = (
                f"Query vector dimension mismatch: expected {self.expected_dimension}, "
                f"got {len(query_vector)}"
            )
            logger.error(err_msg)
            raise ValueError(err_msg)

        if top_k <= 0:
            raise ValueError(f"top_k must be a positive integer > 0, got {top_k}")

        self.verify_collection()
        client = self._get_client()

        qdrant_filter: Optional[qmodels.Filter] = None
        if filters:
            must_conditions = []
            for key, val in filters.items():
                if val is not None:
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=str(val)),
                        )
                    )
            if must_conditions:
                qdrant_filter = qmodels.Filter(must=must_conditions)

        try:
            response = client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
            )
            search_results = response.points if hasattr(response, "points") else response
        except Exception as err:
            logger.error(f"Qdrant vector search failed: {err}")
            raise RuntimeError(f"Qdrant search failure: {err}") from err


        results: List[Dict[str, Any]] = []
        for point in search_results:
            results.append({
                "point_id": str(point.id),
                "score": float(point.score),
                "payload": point.payload or {},
            })

        logger.info(f"Qdrant search returned {len(results)} matches for query.")
        return results

    def delete_vectors_by_document(self, document_id: str) -> bool:
        """Delete all vectors matching document_id in collection payload."""
        if not document_id:
            return False
        client = self._get_client()
        try:
            client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                ),
                wait=True,
            )
            logger.info(f"Deleted vector points for document '{document_id}' from Qdrant.")
            return True
        except Exception as err:
            logger.warning(f"Could not delete vectors for document '{document_id}' from Qdrant: {err}")
            return False


qdrant_vector_store = QdrantVectorStore()
qdrant_store = qdrant_vector_store


