from typing import List, Dict, Any, Set
from dataclasses import dataclass


@dataclass
class EvaluationMetrics:
    precision_at_k: float
    recall_at_k: float
    mrr: float


def compute_retrieval_metrics(
    retrieved_chunk_ids: List[str],
    relevant_chunk_ids: Set[str],
    k: int = 5,
) -> EvaluationMetrics:
    """Calculate standard Information Retrieval metrics (Precision@K, Recall@K, MRR).
    
    Zero-relevant-query convention:
    When a query has no relevant documents in the ground-truth corpus (relevant_chunk_ids is empty),
    precision_at_k, recall_at_k, and mrr are defined as 0.0.
    
    Precision@K denominator:
    Precision@K consistently uses cutoff K as its denominator (precision = relevant_in_top_k / K),
    even when fewer than K results are returned by the retriever.
    
    Args:
        retrieved_chunk_ids: List of chunk ID strings returned by the retriever in ranked order.
        relevant_chunk_ids: Ground-truth set of relevant chunk ID strings for the test query.
        k: Cutoff rank for evaluation (e.g. 3 or 5).
        
    Returns:
        EvaluationMetrics with precision_at_k, recall_at_k, and mrr.
    """
    if not relevant_chunk_ids:
        return EvaluationMetrics(precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)

    top_k_retrieved = retrieved_chunk_ids[:k]
    if not top_k_retrieved:
        return EvaluationMetrics(precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)

    relevant_in_top_k = sum(1 for cid in top_k_retrieved if cid in relevant_chunk_ids)
    precision = relevant_in_top_k / float(k)
    recall = relevant_in_top_k / float(len(relevant_chunk_ids))

    mrr = 0.0
    for idx, cid in enumerate(top_k_retrieved):
        if cid in relevant_chunk_ids:
            mrr = 1.0 / float(idx + 1)
            break

    return EvaluationMetrics(
        precision_at_k=round(precision, 4),
        recall_at_k=round(recall, 4),
        mrr=round(mrr, 4),
    )


def compute_macro_retrieval_metrics(
    metrics_list: List[EvaluationMetrics],
) -> EvaluationMetrics:
    """Calculate macro-averaged Information Retrieval metrics across a list of query evaluations.
    
    Convention for zero-relevant queries:
    When a query has no relevant documents in the ground truth corpus, its per-query
    Precision@K, Recall@K, and MRR are defined as 0.0. In macro-averaging, these 0.0 values
    are included across the full N queries in the evaluation benchmark.
    
    Args:
        metrics_list: List of per-query EvaluationMetrics instances.
        
    Returns:
        EvaluationMetrics with macro-averaged precision_at_k, recall_at_k, and mrr.
    """
    if not metrics_list:
        return EvaluationMetrics(precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)

    n = len(metrics_list)
    macro_p = sum(m.precision_at_k for m in metrics_list) / float(n)
    macro_r = sum(m.recall_at_k for m in metrics_list) / float(n)
    macro_mrr = sum(m.mrr for m in metrics_list) / float(n)

    return EvaluationMetrics(
        precision_at_k=round(macro_p, 4),
        recall_at_k=round(macro_r, 4),
        mrr=round(macro_mrr, 4),
    )
