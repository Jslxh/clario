import enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ClaimLabel(str, enum.Enum):
    """Mutually exclusive atomic evaluation outcome for an individual extracted claim."""
    SUPPORTED = "supported"        # Entailed by evaluated context, no contradiction, fully evaluated
    CONTRADICTED = "contradicted"  # Contradicted by evaluated context (or conflicting evaluated context)
    INSUFFICIENT = "insufficient"  # Fully evaluated against all relevant chunks, but evidence is neutral/below threshold
    UNVERIFIED = "unverified"      # Incomplete evaluation due to global pair-cap truncation or component error


class FaithfulnessStatus(str, enum.Enum):
    """Answer-level aggregate verification status derived deterministically via strict precedence."""
    VERIFICATION_FAILED = "verification_failed"          # Precedence 1: Operational failure/timeout in verifier
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"      # Precedence 2: Context was empty or pipeline abstained
    NO_CLAIMS_FOUND = "no_claims_found"                  # Precedence 3: Context present, but 0 factual claims extracted
    CONTRADICTED = "contradicted"                        # Precedence 4: At least one claim has detected contradiction
    VERIFIED_FAITHFUL = "verified_faithful"              # Precedence 5: 100% of claims are SUPPORTED and fully evaluated (N >= 1)
    PARTIALLY_SUPPORTED = "partially_supported"          # Precedence 6: >=1 claim SUPPORTED, 0 CONTRADICTED, some INSUFFICIENT or UNVERIFIED
    INCOMPLETE_VERIFICATION = "incomplete_verification"  # Precedence 7: 0 SUPPORTED, 0 CONTRADICTED, >=1 UNVERIFIED due to pair cap
    UNSUPPORTED = "unsupported"                          # Precedence 8: 100% of claims fully evaluated and INSUFFICIENT


class ClaimVerification(BaseModel):
    """Granular verification record for a single atomic claim."""
    claim_id: str = Field(..., description="Deterministic claim identifier (e.g. 'claim-1')")
    claim_text: str = Field(..., description="Normalized atomic claim statement")
    label: ClaimLabel = Field(..., description="Mutually exclusive claim-level label")
    
    # Evidence linkages
    cited_chunk_ids: List[str] = Field(
        default_factory=list, 
        description="Chunk IDs parsed from citation tags ([Doc-N]) attached to this claim"
    )
    supporting_chunk_ids: List[str] = Field(
        default_factory=list, 
        description="Evaluated chunk IDs where NLI entailment score >= entailment_threshold"
    )
    contradicting_chunk_ids: List[str] = Field(
        default_factory=list, 
        description="Evaluated chunk IDs where NLI contradiction score >= contradiction_threshold"
    )
    evaluated_chunk_ids: List[str] = Field(
        default_factory=list, 
        description="All chunk IDs explicitly evaluated against this claim by NLI"
    )
    
    # Diagnostic tag retention (pre-sanitization)
    raw_citation_tags: List[str] = Field(
        default_factory=list, 
        description="Original citation strings in raw text before Phase 9 sanitization (e.g. ['[Doc-1]', '[Doc-99]'])"
    )
    unmapped_tags: List[str] = Field(
        default_factory=list, 
        description="Citation strings referencing chunks absent from supplied context"
    )
    malformed_tags: List[str] = Field(
        default_factory=list, 
        description="Malformed or invalid tag syntaxes (e.g. '[Doc-]', '[Document-1]')"
    )
    
    # Quantitative scores & bounds
    entailment_score: float = Field(
        0.0, description="Highest entailment probability across evaluated pairs (0.0 to 1.0)"
    )
    contradiction_score: float = Field(
        0.0, description="Highest contradiction probability across evaluated pairs (0.0 to 1.0)"
    )
    is_fully_evaluated: bool = Field(
        True, description="False if pair-cap truncation prevented evaluating all relevant candidate chunks"
    )
    has_conflicting_evidence: bool = Field(
        False, description="True if both supporting and contradicting chunks were detected in evaluated context"
    )

    model_config = ConfigDict(from_attributes=True)


class VerificationResult(BaseModel):
    """Comprehensive verification payload attached to GenerationResponse."""
    status: FaithfulnessStatus = Field(..., description="Aggregate answer-level faithfulness status")
    faithfulness_score: Optional[float] = Field(
        None, description="Ratio of fully supported claims to total extracted claims (0.0 to 1.0); None for non-claim/error statuses"
    )
    
    # Exact accounting aggregates (must sum to total_claims)
    total_claims: int = Field(0, description="Total atomic factual claims extracted")
    supported_claims: int = Field(0, description="Count of claims labeled SUPPORTED")
    contradicted_claims: int = Field(0, description="Count of claims labeled CONTRADICTED")
    insufficient_claims: int = Field(0, description="Count of claims labeled INSUFFICIENT")
    unverified_claims: int = Field(0, description="Count of claims labeled UNVERIFIED")
    
    # Claim details
    claims: List[ClaimVerification] = Field(default_factory=list, description="Claim-level verification records")
    
    # Execution & diagnostic telemetry
    total_pairs_evaluated: int = Field(0, description="Total (claim, chunk) pairs scored by NLI model")
    pair_cap_reached: bool = Field(False, description="True if VERIFICATION_MAX_PAIRS bounded the evaluation")
    unmapped_citation_tags: List[str] = Field(
        default_factory=list, description="All unmapped citation tags stripped from response text"
    )
    malformed_citation_tags: List[str] = Field(
        default_factory=list, description="All malformed citation tags stripped from response text"
    )
    verification_latency_ms: float = Field(0.0, description="Execution duration of verification pipeline in ms")
    model_name: str = Field(..., description="Name of NLI model or verifier used")

    model_config = ConfigDict(from_attributes=True)
