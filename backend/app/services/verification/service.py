import re
import time
import logging
from typing import List, Dict, Tuple, Optional, Set

from app.core.config import settings
from app.schemas.generation import ContextChunk
from app.schemas.verification import (
    ClaimLabel,
    FaithfulnessStatus,
    ClaimVerification,
    VerificationResult,
)
from app.services.verification.base import BaseNLIVerifier
from app.services.verification.claim_extractor import ClaimExtractor, ExtractedClaim, claim_extractor
from app.services.verification.nli_verifier import local_nli_verifier

logger = logging.getLogger(__name__)


class VerificationService:
    """End-to-end Grounding & Faithfulness Verification Service."""

    def __init__(
        self,
        verifier: Optional[BaseNLIVerifier] = None,
        extractor: Optional[ClaimExtractor] = None,
        max_pairs: Optional[int] = None,
        entailment_threshold: Optional[float] = None,
        contradiction_threshold: Optional[float] = None,
    ):
        self.verifier = verifier or local_nli_verifier
        self.extractor = extractor or claim_extractor
        self.max_pairs = max_pairs if max_pairs is not None else settings.VERIFICATION_MAX_PAIRS
        self.entailment_threshold = (
            entailment_threshold
            if entailment_threshold is not None
            else settings.VERIFICATION_ENTAILMENT_THRESHOLD
        )
        self.contradiction_threshold = (
            contradiction_threshold
            if contradiction_threshold is not None
            else settings.VERIFICATION_CONTRADICTION_THRESHOLD
        )

    def prioritize_candidate_pairs(
        self,
        claims: List[ExtractedClaim],
        context_chunks: List[ContextChunk],
        max_global_pairs: int,
    ) -> Tuple[List[Tuple[ExtractedClaim, ContextChunk]], Dict[str, bool]]:
        """Constructs and orders candidate pairs deterministically from existing Phase 9 context.
        
        Returns:
            Tuple of (selected_pairs, is_fully_evaluated_map)
        """
        if not claims or not context_chunks:
            return [], {c.id: True for c in claims}

        chunk_order = {c.chunk_id: idx for idx, c in enumerate(context_chunks)}
        
        all_candidate_pairs: List[Tuple[Tuple[int, float, int], ExtractedClaim, ContextChunk]] = []
        claim_total_candidates: Dict[str, int] = {}

        for claim in claims:
            claim_tokens = set(re.findall(r"\w+", claim.text.lower()))
            candidates_for_claim = []

            for chunk in context_chunks:
                # Tier 1: Explicit citation match
                is_cited = chunk.chunk_id in claim.cited_chunk_ids

                # Tier 2: Local token overlap (Jaccard)
                chunk_tokens = set(re.findall(r"\w+", chunk.content.lower()))
                union_len = len(claim_tokens | chunk_tokens)
                overlap_ratio = (len(claim_tokens & chunk_tokens) / union_len) if union_len > 0 else 0.0

                # Tier 3: Packed context rank
                packed_rank = chunk_order.get(chunk.chunk_id, 999)

                # Composite priority tuple: (Tier 1, Tier 2, -Tier 3)
                priority = (
                    1 if is_cited else 0,
                    round(overlap_ratio, 4),
                    -packed_rank
                )
                candidates_for_claim.append((priority, claim, chunk))

            # Sort claim's candidates descending by priority
            candidates_for_claim.sort(key=lambda x: x[0], reverse=True)
            claim_total_candidates[claim.id] = len(candidates_for_claim)
            all_candidate_pairs.extend(candidates_for_claim)

        # Global deterministic ordering across all candidate pairs
        all_candidate_pairs.sort(key=lambda x: x[0], reverse=True)

        # Select top pairs up to max_global_pairs
        selected = all_candidate_pairs[:max_global_pairs]
        selected_pairs = [(c, k) for (_, c, k) in selected]

        # Calculate evaluated pair counts per claim
        pairs_evaluated_per_claim: Dict[str, int] = {}
        for claim, _ in selected_pairs:
            pairs_evaluated_per_claim[claim.id] = pairs_evaluated_per_claim.get(claim.id, 0) + 1

        # A claim is fully evaluated if all context chunks were evaluated against it
        is_fully_evaluated_map = {
            claim.id: pairs_evaluated_per_claim.get(claim.id, 0) >= claim_total_candidates.get(claim.id, 0)
            for claim in claims
        }

        return selected_pairs, is_fully_evaluated_map

    def verify_generation(
        self,
        raw_answer: str,
        context_chunks: List[ContextChunk],
        has_sufficient_context: bool = True,
    ) -> VerificationResult:
        """Run post-generation verification over raw LLM output against supplied context chunks."""
        t0 = time.perf_counter()
        model_name = getattr(self.verifier, "model_name", "nli-verifier")

        # Precedence 2: Insufficient context / empty context supplied
        if not has_sufficient_context or not context_chunks:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return VerificationResult(
                status=FaithfulnessStatus.INSUFFICIENT_EVIDENCE,
                faithfulness_score=None,
                total_claims=0,
                supported_claims=0,
                contradicted_claims=0,
                insufficient_claims=0,
                unverified_claims=0,
                claims=[],
                total_pairs_evaluated=0,
                pair_cap_reached=False,
                unmapped_citation_tags=[],
                malformed_citation_tags=[],
                verification_latency_ms=latency_ms,
                model_name=model_name,
            )

        try:
            # 1. Extract atomic claims & pre-sanitization citation tags
            extracted_claims = self.extractor.extract_claims(
                raw_text=raw_answer,
                supplied_chunks=context_chunks,
            )

            # Aggregate unmapped and malformed tags across all extracted claims and raw text
            all_unmapped_tags: List[str] = []
            all_malformed_tags: List[str] = []
            for claim in extracted_claims:
                all_unmapped_tags.extend(claim.unmapped_tags)
                all_malformed_tags.extend(claim.malformed_tags)

            all_unmapped_tags = list(dict.fromkeys(all_unmapped_tags))
            all_malformed_tags = list(dict.fromkeys(all_malformed_tags))

            # Precedence 3: No claims extracted from non-empty context
            if not extracted_claims:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                return VerificationResult(
                    status=FaithfulnessStatus.NO_CLAIMS_FOUND,
                    faithfulness_score=None,
                    total_claims=0,
                    supported_claims=0,
                    contradicted_claims=0,
                    insufficient_claims=0,
                    unverified_claims=0,
                    claims=[],
                    total_pairs_evaluated=0,
                    pair_cap_reached=False,
                    unmapped_citation_tags=all_unmapped_tags,
                    malformed_citation_tags=all_malformed_tags,
                    verification_latency_ms=latency_ms,
                    model_name=model_name,
                )

            # 2. Bounded Candidate Pair Prioritization
            candidate_pairs, is_fully_evaluated_map = self.prioritize_candidate_pairs(
                claims=extracted_claims,
                context_chunks=context_chunks,
                max_global_pairs=self.max_pairs,
            )

            total_pairs_evaluated = len(candidate_pairs)
            total_possible_pairs = len(extracted_claims) * len(context_chunks)
            pair_cap_reached = total_possible_pairs > self.max_pairs and total_pairs_evaluated >= self.max_pairs

            # 3. Batched NLI Inference
            nli_pairs = [(chunk.content, claim.text) for (claim, chunk) in candidate_pairs]
            nli_scores = self.verifier.predict_batch(nli_pairs) if nli_pairs else []

            # Map NLI scores back to (claim_id, chunk_id)
            claim_scores_map: Dict[str, List[Tuple[str, Dict[str, float]]]] = {
                claim.id: [] for claim in extracted_claims
            }
            for (claim, chunk), score_dict in zip(candidate_pairs, nli_scores):
                claim_scores_map[claim.id].append((chunk.chunk_id, score_dict))

            # 4. Evaluate each claim individually
            claim_verifications: List[ClaimVerification] = []
            supported_count = 0
            contradicted_count = 0
            insufficient_count = 0
            unverified_count = 0

            for claim in extracted_claims:
                is_full = is_fully_evaluated_map.get(claim.id, True)
                evaluated_chunks = claim_scores_map.get(claim.id, [])

                evaluated_chunk_ids = [cid for cid, _ in evaluated_chunks]
                supporting_chunk_ids = []
                contradicting_chunk_ids = []
                max_ent = 0.0
                max_contra = 0.0

                for chunk_id, scores in evaluated_chunks:
                    ent = scores.get("entailment", 0.0)
                    contra = scores.get("contradiction", 0.0)

                    max_ent = max(max_ent, ent)
                    max_contra = max(max_contra, contra)

                    if ent >= self.entailment_threshold:
                        supporting_chunk_ids.append(chunk_id)
                    if contra >= self.contradiction_threshold:
                        contradicting_chunk_ids.append(chunk_id)

                has_conflicting = len(supporting_chunk_ids) > 0 and len(contradicting_chunk_ids) > 0

                # Determine ClaimLabel
                if len(contradicting_chunk_ids) > 0:
                    # Contradiction found in evaluated context
                    label = ClaimLabel.CONTRADICTED
                    contradicted_count += 1
                elif len(supporting_chunk_ids) > 0:
                    if is_full:
                        label = ClaimLabel.SUPPORTED
                        supported_count += 1
                    else:
                        # Cannot certify supported if candidate context was truncated by pair cap
                        label = ClaimLabel.UNVERIFIED
                        unverified_count += 1
                elif not is_full:
                    label = ClaimLabel.UNVERIFIED
                    unverified_count += 1
                else:
                    label = ClaimLabel.INSUFFICIENT
                    insufficient_count += 1

                claim_verifications.append(
                    ClaimVerification(
                        claim_id=claim.id,
                        claim_text=claim.text,
                        label=label,
                        cited_chunk_ids=claim.cited_chunk_ids,
                        supporting_chunk_ids=supporting_chunk_ids,
                        contradicting_chunk_ids=contradicting_chunk_ids,
                        evaluated_chunk_ids=evaluated_chunk_ids,
                        raw_citation_tags=claim.raw_tags,
                        unmapped_tags=claim.unmapped_tags,
                        malformed_tags=claim.malformed_tags,
                        entailment_score=round(max_ent, 4),
                        contradiction_score=round(max_contra, 4),
                        is_fully_evaluated=is_full,
                        has_conflicting_evidence=has_conflicting,
                    )
                )

            total_claims = len(extracted_claims)
            # Enforce exact accounting invariant
            assert (
                supported_count + contradicted_count + insufficient_count + unverified_count
                == total_claims
            ), "Claim counts do not sum to total_claims"

            # 5. Determine Answer-Level Status via Precedence
            if contradicted_count >= 1:
                # Precedence 4: Contradicted
                status = FaithfulnessStatus.CONTRADICTED
                score = round(supported_count / total_claims, 4)
            elif supported_count == total_claims and total_claims >= 1:
                # Precedence 5: Verified Faithful (100% supported and fully evaluated)
                status = FaithfulnessStatus.VERIFIED_FAITHFUL
                score = 1.0
            elif supported_count >= 1:
                # Precedence 6: Partially Supported
                status = FaithfulnessStatus.PARTIALLY_SUPPORTED
                score = round(supported_count / total_claims, 4)
            elif unverified_count >= 1:
                # Precedence 7: Incomplete Verification
                status = FaithfulnessStatus.INCOMPLETE_VERIFICATION
                score = 0.0
            else:
                # Precedence 8: Unsupported (0 supported, 0 contradicted, 0 unverified, all insufficient)
                status = FaithfulnessStatus.UNSUPPORTED
                score = 0.0

            latency_ms = (time.perf_counter() - t0) * 1000.0

            return VerificationResult(
                status=status,
                faithfulness_score=score,
                total_claims=total_claims,
                supported_claims=supported_count,
                contradicted_claims=contradicted_count,
                insufficient_claims=insufficient_count,
                unverified_claims=unverified_count,
                claims=claim_verifications,
                total_pairs_evaluated=total_pairs_evaluated,
                pair_cap_reached=pair_cap_reached,
                unmapped_citation_tags=all_unmapped_tags,
                malformed_citation_tags=all_malformed_tags,
                verification_latency_ms=round(latency_ms, 2),
                model_name=model_name,
            )

        except Exception as err:
            logger.error(f"Operational error in verification pipeline: {err}", exc_info=True)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return VerificationResult(
                status=FaithfulnessStatus.VERIFICATION_FAILED,
                faithfulness_score=None,
                total_claims=0,
                supported_claims=0,
                contradicted_claims=0,
                insufficient_claims=0,
                unverified_claims=0,
                claims=[],
                total_pairs_evaluated=0,
                pair_cap_reached=False,
                unmapped_citation_tags=[],
                malformed_citation_tags=[],
                verification_latency_ms=round(latency_ms, 2),
                model_name=model_name,
            )


verification_service = VerificationService()
