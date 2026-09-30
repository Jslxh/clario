import pytest
from app.services.verification.mock_verifier import MockNLIVerifier
from app.services.verification.service import VerificationService
from app.services.verification.claim_extractor import ExtractedClaim
from app.schemas.generation import ContextChunk
from app.schemas.verification import ClaimLabel, FaithfulnessStatus


@pytest.fixture
def base_context():
    return [
        ContextChunk(
            source_index=1,
            source_tag="[Doc-1]",
            chunk_id="c1",
            document_id="d1",
            filename="leave_policy.pdf",
            access_level="internal",
            content="Employees receive 20 days of paid annual leave per calendar year.",
            token_count=15,
            score=0.95,
        ),
        ContextChunk(
            source_index=2,
            source_tag="[Doc-2]",
            chunk_id="c2",
            document_id="d2",
            filename="contract.pdf",
            access_level="internal",
            content="Contractors are not eligible for paid annual leave.",
            token_count=12,
            score=0.85,
        ),
    ]


def test_archetype_1_exact_entailment(base_context):
    """Archetype 1: Exact / near-exact entailment."""
    verifier = MockNLIVerifier()
    service = VerificationService(verifier=verifier)
    raw_text = "Employees receive 20 days of paid annual leave per calendar year [Doc-1]."
    result = service.verify_generation(raw_text, base_context, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.VERIFIED_FAITHFUL
    assert result.faithfulness_score == 1.0
    assert result.total_claims == 1
    assert result.supported_claims == 1
    assert result.claims[0].label == ClaimLabel.SUPPORTED


def test_archetype_2_paraphrased_entailment(base_context):
    """Archetype 2: Paraphrased statement entailed by context."""
    verifier = MockNLIVerifier()
    service = VerificationService(verifier=verifier)
    raw_text = "Full-time employees get twenty days of paid leave annually [Doc-1]."
    result = service.verify_generation(raw_text, base_context, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.VERIFIED_FAITHFUL
    assert result.faithfulness_score == 1.0
    assert result.supported_claims == 1


def test_archetype_3_direct_factual_contradiction(base_context):
    """Archetype 3: Direct factual contradiction."""
    verifier = MockNLIVerifier()
    service = VerificationService(verifier=verifier)
    raw_text = "Employees receive false untrue contradictory 50 days of leave [Doc-1]."
    result = service.verify_generation(raw_text, base_context, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.CONTRADICTED
    assert result.contradicted_claims == 1
    assert result.claims[0].label == ClaimLabel.CONTRADICTED


def test_archetype_4_numeric_or_insufficient_evidence(base_context):
    """Archetype 4: Claim with insufficient/hallucinated details."""
    verifier = MockNLIVerifier(default_entailment=0.20, default_contradiction=0.10, default_neutral=0.70)
    service = VerificationService(verifier=verifier)
    raw_text = "Employees receive an additional winter holiday bonus of $2,000 [Doc-1]."
    result = service.verify_generation(raw_text, base_context, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.UNSUPPORTED
    assert result.insufficient_claims == 1
    assert result.claims[0].label == ClaimLabel.INSUFFICIENT


def test_archetype_5_unmapped_citation_tag(base_context):
    """Archetype 5: Answer references unmapped tag [Doc-99]."""
    verifier = MockNLIVerifier()
    service = VerificationService(verifier=verifier)
    raw_text = "Employees receive standard dental benefits [Doc-99]."
    result = service.verify_generation(raw_text, base_context, has_sufficient_context=True)

    assert "[Doc-99]" in result.unmapped_citation_tags
    assert result.claims[0].unmapped_tags == ["[Doc-99]"]


def test_archetype_6_conflicting_chunks(base_context):
    """Archetype 6: One chunk entails while another chunk contradicts."""
    conflicting_context = [
        ContextChunk(
            source_index=1,
            source_tag="[Doc-1]",
            chunk_id="c1",
            document_id="d1",
            filename="policy_v1.pdf",
            access_level="internal",
            content="Working from home is allowed 3 days per week.",
            token_count=10,
            score=0.95,
        ),
        ContextChunk(
            source_index=2,
            source_tag="[Doc-2]",
            chunk_id="c2",
            document_id="d2",
            filename="policy_v2.pdf",
            access_level="internal",
            content="Working from home is strictly prohibited and untrue conflict contradict.",
            token_count=12,
            score=0.90,
        ),
    ]

    verifier = MockNLIVerifier()
    service = VerificationService(verifier=verifier)
    raw_text = "Working from home is permitted three days a week [Doc-1]."
    result = service.verify_generation(raw_text, conflicting_context, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.CONTRADICTED
    assert result.claims[0].has_conflicting_evidence is True
    assert result.claims[0].label == ClaimLabel.CONTRADICTED


def test_archetype_7_zero_claims_in_context(base_context):
    """Archetype 7: Context present but answer text contains no factual claims."""
    service = VerificationService(verifier=MockNLIVerifier())
    result = service.verify_generation("Hello! How can I help you today?", base_context, has_sufficient_context=True)

    assert result.status == FaithfulnessStatus.NO_CLAIMS_FOUND
    assert result.faithfulness_score is None
    assert result.total_claims == 0


def test_archetype_8_empty_context_abstention():
    """Archetype 8: Empty context supplied / pipeline abstention."""
    service = VerificationService(verifier=MockNLIVerifier())
    result = service.verify_generation("", [], has_sufficient_context=False)

    assert result.status == FaithfulnessStatus.INSUFFICIENT_EVIDENCE
    assert result.faithfulness_score is None
    assert result.total_claims == 0
