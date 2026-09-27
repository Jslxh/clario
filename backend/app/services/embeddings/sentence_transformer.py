import logging
from typing import List, Optional
import numpy as np

from app.core.config import settings
from app.services.embeddings.base import BaseEmbeddingService

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """Embedding service utilizing SentenceTransformers models.
    
    Defaults to BAAI/bge-small-en-v1.5 producing 384-dimensional normalized vectors.
    Loads model once and reuses it for CPU or GPU execution.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        device: Optional[str] = None,
        expected_dimension: Optional[int] = None,
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        self.expected_dimension = expected_dimension or settings.EMBEDDING_DIMENSION
        self.device_setting = device or settings.EMBEDDING_DEVICE
        
        self._model = None

    def _resolve_device(self) -> str:
        """Resolve 'auto' device setting to 'cuda' if GPU available, otherwise 'cpu'."""
        if self.device_setting == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        return self.device_setting

    def _get_model(self):
        """Lazy load and reuse the SentenceTransformer model instance."""
        if self._model is None:
            resolved_device = self._resolve_device()
            logger.info(
                f"Loading embedding model '{self.model_name}' on device '{resolved_device}'..."
            )
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=resolved_device)
            except Exception as err:
                logger.error(f"Failed to load embedding model '{self.model_name}': {err}")
                raise RuntimeError(f"Embedding model loading failed for {self.model_name}: {err}") from err
        return self._model

    def get_dimension(self) -> int:
        return self.expected_dimension

    def _validate_embeddings(self, embeddings: List[List[float]]) -> List[List[float]]:
        """Verify generated embedding vector dimension matches exact expectation (384)."""
        for idx, vec in enumerate(embeddings):
            if len(vec) != self.expected_dimension:
                err_msg = (
                    f"Embedding dimension mismatch at index {idx}: "
                    f"expected {self.expected_dimension}, got {len(vec)}"
                )
                logger.error(err_msg)
                raise ValueError(err_msg)
        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate 384-dimensional normalized embeddings for a list of document chunk texts.
        
        Uses explicit batching and cosine normalization. Preserves deterministic order.
        """
        if not texts:
            return []

        model = self._get_model()

        # Sanitize texts: replace empty or whitespace-only texts with a single space placeholder
        cleaned_texts = [t if t and t.strip() else " " for t in texts]

        try:
            raw_embeddings = model.encode(
                cleaned_texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as err:
            logger.error(f"Error generating document embeddings: {err}")
            raise RuntimeError(f"Document embedding generation failed: {err}") from err

        if isinstance(raw_embeddings, np.ndarray):
            embeddings_list = raw_embeddings.tolist()
        else:
            embeddings_list = [list(vec) for vec in raw_embeddings]

        return self._validate_embeddings(embeddings_list)

    def embed_query(self, query: str) -> List[float]:
        """Generate a 384-dimensional normalized embedding for a search query.
        
        BGE v1.5 recommendation: Document chunks are encoded as-is, while search queries
        can optionally include instruction prefixes if required by specific downstream models.
        For BAAI/bge-small-en-v1.5, default query encoding uses direct input or standard prefix.
        """
        if not query or not query.strip():
            query = " "

        embeddings = self.embed_documents([query])
        return embeddings[0]
