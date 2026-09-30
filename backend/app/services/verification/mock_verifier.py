from typing import List, Tuple, Dict, Optional, Callable
from app.services.verification.base import BaseNLIVerifier


class MockNLIVerifier(BaseNLIVerifier):
    """Deterministic offline NLI verifier for fast hermetic unit/integration tests."""

    def __init__(
        self,
        custom_predictor: Optional[Callable[[str, str], Dict[str, float]]] = None,
        default_entailment: float = 0.90,
        default_contradiction: float = 0.05,
        default_neutral: float = 0.05,
    ):
        self.custom_predictor = custom_predictor
        self.default_entailment = default_entailment
        self.default_contradiction = default_contradiction
        self.default_neutral = default_neutral
        self.call_count = 0
        self.should_fail = False

    def predict_nli(self, premise: str, hypothesis: str) -> Dict[str, float]:
        if self.should_fail:
            raise RuntimeError("Simulated NLI model inference crash / out of memory.")

        self.call_count += 1

        if self.custom_predictor:
            return self.custom_predictor(premise, hypothesis)

        premise_lower = premise.lower()
        hypo_lower = hypothesis.lower()

        # Deterministic keyword-based NLI heuristics for testing archetypes
        if "contradict" in hypo_lower or "untrue" in hypo_lower or "false" in hypo_lower:
            return {"entailment": 0.05, "contradiction": 0.92, "neutral": 0.03}
        
        if "conflict" in premise_lower and "contradict" in premise_lower:
            return {"entailment": 0.10, "contradiction": 0.88, "neutral": 0.02}

        if "insufficient" in hypo_lower or "unknown" in hypo_lower or "hallucinated" in hypo_lower:
            return {"entailment": 0.20, "contradiction": 0.10, "neutral": 0.70}

        # Check token intersection between premise and hypothesis
        hypo_words = set(hypo_lower.split())
        premise_words = set(premise_lower.split())
        overlap = hypo_words & premise_words

        if len(hypo_words) > 0 and (len(overlap) / len(hypo_words)) >= 0.4:
            return {"entailment": 0.88, "contradiction": 0.04, "neutral": 0.08}

        return {
            "entailment": self.default_entailment,
            "contradiction": self.default_contradiction,
            "neutral": self.default_neutral,
        }

    def predict_batch(self, pairs: List[Tuple[str, str]]) -> List[Dict[str, float]]:
        return [self.predict_nli(p, h) for p, h in pairs]
