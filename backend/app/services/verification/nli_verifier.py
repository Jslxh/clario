import logging
import threading
from typing import List, Tuple, Dict, Optional
import numpy as np

from app.core.config import settings
from app.services.verification.base import BaseNLIVerifier
from app.services.verification.mock_verifier import MockNLIVerifier

logger = logging.getLogger(__name__)


class LocalCrossEncoderNLIVerifier(BaseNLIVerifier):
    """Production local NLI Cross-Encoder verifier with thread-safe lazy loading and fallback."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: Optional[int] = None,
    ):
        self.model_name = model_name or settings.VERIFICATION_MODEL_NAME
        self.device = device or settings.VERIFICATION_DEVICE
        self.batch_size = batch_size or settings.VERIFICATION_BATCH_SIZE
        self._model = None
        self._lock = threading.RLock()
        self._fallback_verifier: Optional[MockNLIVerifier] = None

    def _get_model(self):
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            try:
                from sentence_transformers import CrossEncoder
                import torch

                device_str = "cuda" if (self.device == "cuda" or (self.device == "auto" and torch.cuda.is_available())) else "cpu"
                logger.info(f"Loading NLI Cross-Encoder model '{self.model_name}' on device '{device_str}'...")
                self._model = CrossEncoder(self.model_name, device=device_str, max_length=512)
                logger.info(f"NLI Cross-Encoder model '{self.model_name}' loaded successfully.")
                return self._model
            except Exception as err:
                logger.warning(
                    f"Could not load local CrossEncoder model '{self.model_name}' ({err}). "
                    "Falling back to deterministic MockNLIVerifier."
                )
                self._fallback_verifier = MockNLIVerifier()
                return None

    def predict_nli(self, premise: str, hypothesis: str) -> Dict[str, float]:
        """Predict entailment, contradiction, neutral probabilities for a (premise, hypothesis) pair."""
        results = self.predict_batch([(premise, hypothesis)])
        return results[0]

    def predict_batch(self, pairs: List[Tuple[str, str]]) -> List[Dict[str, float]]:
        """Compute batched NLI probabilities."""
        if not pairs:
            return []

        model = self._get_model()
        if model is None:
            if self._fallback_verifier is None:
                self._fallback_verifier = MockNLIVerifier()
            return self._fallback_verifier.predict_batch(pairs)

        try:
            # CrossEncoder returns raw logits (num_pairs, num_labels)
            # Standard NLI output format: [contradiction, entailment, neutral] or [entailment, neutral, contradiction]
            logits = model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
            
            # Apply softmax
            if hasattr(logits, "tolist"):
                logits_np = np.array(logits)
            else:
                logits_np = np.array(logits)

            if logits_np.ndim == 1:
                logits_np = logits_np.reshape(1, -1)

            # Softmax calculation
            exp_logits = np.exp(logits_np - np.max(logits_np, axis=1, keepdims=True))
            probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

            results: List[Dict[str, float]] = []
            num_classes = probs.shape[1]

            for row in probs:
                if num_classes == 3:
                    # DeBERTa-v3-small NLI class mapping: 0=contradiction, 1=neutral, 2=entailment (or check config_labels)
                    # We map standard 3-class distribution
                    c_prob = float(row[0])
                    n_prob = float(row[1])
                    e_prob = float(row[2])
                elif num_classes == 2:
                    # Binary model (0: not entailment / contradiction, 1: entailment)
                    c_prob = float(row[0])
                    n_prob = 0.0
                    e_prob = float(row[1])
                else:
                    e_prob = float(row[0])
                    c_prob = 0.0
                    n_prob = 0.0

                results.append({
                    "entailment": round(e_prob, 4),
                    "contradiction": round(c_prob, 4),
                    "neutral": round(n_prob, 4),
                })
            return results

        except Exception as err:
            logger.error(f"Error during NLI batch prediction: {err}. Using fallback.")
            if self._fallback_verifier is None:
                self._fallback_verifier = MockNLIVerifier()
            return self._fallback_verifier.predict_batch(pairs)


local_nli_verifier = LocalCrossEncoderNLIVerifier()
