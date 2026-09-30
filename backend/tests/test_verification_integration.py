import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.verification.service import VerificationService
from app.services.verification.mock_verifier import MockNLIVerifier
from app.services.verification.claim_extractor import ExtractedClaim
from app.schemas.generation import ContextChunk
from app.schemas.verification import ClaimLabel, FaithfulnessStatus

client = TestClient(app)


def test_1_candidate_pair_prioritization_and_global_cap():
    """Verify that candidate pairs are capped at 20 and prioritization is deterministic."""
    # Create 5 claims and 6 chunks = 30 potential pairs > 20 cap
    claims = [
        ExtractedClaim(id=f"claim-{i}", text=f"Claim text statement number {i}", cited_chunk_ids=[f"chunk-{i}"])
        for i in range(1, 6)
    ]
    chunks = [
        ContextChunk(
            source_index=i,
            source_tag=f"[Doc-{i}]",
            chunk_id=f"chunk-{i}",
            document_id=f"doc-{i}",
            filename=f"file_{i}.pdf",
            access_level="internal",
            content=f"Content for chunk number {i} with specific factual evidence.",
            token_count=10,
            score=0.9 - (i * 0.05),
        )
        for i in range(1, 7)
    ]

    service = VerificationService(max_pairs=20)
    selected_pairs, is_fully_evaluated_map = service.prioritize_candidate_pairs(
        claims=claims,
        context_chunks=chunks,
        max_global_pairs=20,
    )

    assert len(selected_pairs) == 20
    # Tier 1 cited pairs must be present
    cited_pairs = [(c.id, k.chunk_id) for c, k in selected_pairs if k.chunk_id in c.cited_chunk_ids]
    assert len(cited_pairs) >= 5


def test_2_incomplete_verification_due_to_pair_cap():
    """Verify that a claim with truncated evaluation is marked UNVERIFIED and answer becomes INCOMPLETE_VERIFICATION."""
    claims = [
        ExtractedClaim(id=f"claim-{i}", text=f"Unverified claim statement {i}", cited_chunk_ids=[])
        for i in range(1, 5)
    ]
    chunks = [
        ContextChunk(
            source_index=i,
            source_tag=f"[Doc-{i}]",
            chunk_id=f"chunk-{i}",
            document_id=f"doc-{i}",
            filename=f"file_{i}.pdf",
            access_level="internal",
            content=f"Context chunk {i}",
            token_count=10,
            score=0.9,
        )
        for i in range(1, 6)
    ]

    # Max pairs set to 3 so only 3 pairs are evaluated, leaving all claims partially unevaluated
    verifier = MockNLIVerifier(default_entailment=0.20, default_contradiction=0.05, default_neutral=0.75)
    service = VerificationService(verifier=verifier, max_pairs=3)
    raw_answer = (
        "This is the first unverified statement of the answer. "
        "This is the second unverified statement of the answer. "
        "This is the third unverified statement of the answer. "
        "This is the fourth unverified statement of the answer."
    )
    result = service.verify_generation(raw_answer, chunks, has_sufficient_context=True)

    assert result.pair_cap_reached is True
    assert result.status == FaithfulnessStatus.INCOMPLETE_VERIFICATION
    assert result.unverified_claims >= 1
    assert result.supported_claims == 0
    assert result.faithfulness_score == 0.0


def test_3_partially_supported_precedence():
    """Verify PARTIALLY_SUPPORTED when at least one claim is supported and others are insufficient."""
    chunks = [
        ContextChunk(
            source_index=1,
            source_tag="[Doc-1]",
            chunk_id="chunk-1",
            document_id="doc-1",
            filename="file_1.pdf",
            access_level="internal",
            content="Employees receive 20 days of paid leave.",
            token_count=10,
            score=0.95,
        ),
    ]

    def custom_predict(premise, hypothesis):
        if "leave" in hypothesis.lower():
            return {"entailment": 0.90, "contradiction": 0.05, "neutral": 0.05}
        return {"entailment": 0.10, "contradiction": 0.05, "neutral": 0.85}

    verifier = MockNLIVerifier(custom_predictor=custom_predict)
    service = VerificationService(verifier=verifier)
    raw_answer = "Employees receive 20 days of paid leave [Doc-1]. Employees also receive a free sports car."
    result = service.verify_generation(raw_answer, chunks, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.PARTIALLY_SUPPORTED
    assert result.supported_claims == 1
    assert result.insufficient_claims == 1
    assert result.contradicted_claims == 0
    assert result.faithfulness_score == 0.5


def test_4_verification_service_failure_tolerance():
    """Verify that verifier failure sets VERIFICATION_FAILED without crashing generation."""
    verifier = MockNLIVerifier()
    verifier.should_fail = True
    service = VerificationService(verifier=verifier)
    
    chunks = [
        ContextChunk(
            source_index=1,
            source_tag="[Doc-1]",
            chunk_id="c1",
            document_id="d1",
            filename="file.pdf",
            access_level="internal",
            content="Some text",
            token_count=5,
            score=0.9,
        )
    ]
    result = service.verify_generation("Some answer text here.", chunks, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.VERIFICATION_FAILED
    assert result.faithfulness_score is None


def test_5_query_endpoint_with_explicit_verify_toggle():
    """Verify POST /api/v1/query with verify=true vs verify=false."""
    # Test verify=False (default or explicit)
    resp_disabled = client.post(
        "/api/v1/query",
        json={"query": "leave policy", "verify": False},
    )
    assert resp_disabled.status_code == 200
    data_disabled = resp_disabled.json()
    assert data_disabled["verification"] is None

    # Test verify=True
    resp_enabled = client.post(
        "/api/v1/query",
        json={"query": "leave policy", "verify": True},
    )
    assert resp_enabled.status_code == 200
    data_enabled = resp_enabled.json()
    assert data_enabled["verification"] is not None
    assert "status" in data_enabled["verification"]
    assert "total_claims" in data_enabled["verification"]
