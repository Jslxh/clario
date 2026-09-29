from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class FusedCandidate:
    point_id: str
    rrf_score: float
    source_ranks: Dict[str, int] = field(default_factory=dict)
    source_scores: Dict[str, float] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)


def reciprocal_rank_fusion(
    ranked_lists: Dict[str, List[Dict[str, Any]]],
    k: int = 60,
    top_k: Optional[int] = None,
) -> List[FusedCandidate]:
    """Combine multiple ranked candidate lists using Reciprocal Rank Fusion (RRF).
    
    Formula:
        RRF_score(d) = sum_{r in retrievers} (1 / (k + rank_r(d)))
    
    where rank_r(d) is the 1-based position of candidate d in retriever r's ranked list.
    
    Args:
        ranked_lists: Mapping from retriever name (e.g. 'semantic', 'bm25') to a list of
                      candidate dictionaries [{"point_id": str, "score": float, "payload": dict}].
        k: RRF smoothing constant (default: 60).
        top_k: Maximum number of fused candidate results to return (if None, returns all).
        
    Returns:
        List of FusedCandidate instances sorted by descending RRF score with deterministic tie-breaking.
    """
    if k <= 0:
        raise ValueError(f"RRF constant k must be a positive integer > 0, got {k}")

    fused_map: Dict[str, FusedCandidate] = {}

    for retriever_name, candidates in ranked_lists.items():
        for zero_based_idx, candidate in enumerate(candidates):
            one_based_rank = zero_based_idx + 1
            cid = candidate["point_id"]
            score = candidate.get("score", 0.0)
            payload = candidate.get("payload", {})

            if cid not in fused_map:
                fused_map[cid] = FusedCandidate(
                    point_id=cid,
                    rrf_score=0.0,
                    source_ranks={},
                    source_scores={},
                    payload=payload,
                )

            # Accumulate 1-based RRF score
            fused_map[cid].rrf_score += 1.0 / (k + one_based_rank)
            fused_map[cid].source_ranks[retriever_name] = one_based_rank
            fused_map[cid].source_scores[retriever_name] = score
            if payload and not fused_map[cid].payload:
                fused_map[cid].payload = payload

    # Deterministic sorting:
    # 1. Primary: Higher RRF score descending (-c.rrf_score)
    # 2. Secondary: Multi-retriever agreement count descending (-len(c.source_ranks))
    # 3. Tertiary: Deterministic chunk ID string ascending for reproducible ordering
    sorted_candidates = sorted(
        fused_map.values(),
        key=lambda c: (
            -c.rrf_score,
            -len(c.source_ranks),
            c.point_id,
        ),
    )

    if top_k is not None and top_k > 0:
        return sorted_candidates[:top_k]
    return sorted_candidates
