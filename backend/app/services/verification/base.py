from abc import ABC, abstractmethod
from typing import List, Tuple, Dict


class BaseNLIVerifier(ABC):
    """Abstract base class for Natural Language Inference (NLI) Cross-Encoder verifiers."""

    @abstractmethod
    def predict_nli(self, premise: str, hypothesis: str) -> Dict[str, float]:
        """Predict NLI probabilities for a single (premise, hypothesis) pair.
        
        Returns:
            Dict with keys: 'entailment', 'contradiction', 'neutral', values summing to ~1.0
        """
        pass

    @abstractmethod
    def predict_batch(self, pairs: List[Tuple[str, str]]) -> List[Dict[str, float]]:
        """Predict NLI probabilities for a batch of (premise, hypothesis) pairs."""
        pass
