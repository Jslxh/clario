import pytest
from app.services.verification.claim_extractor import ClaimExtractor
from app.schemas.generation import ContextChunk


@pytest.fixture
def sample_context_chunks():
    return [
        ContextChunk(
            source_index=1,
            source_tag="[Doc-1]",
            chunk_id="chunk-uuid-1",
            document_id="doc-uuid-1",
            filename="policy.pdf",
            access_level="internal",
            content="Employees receive 20 days of paid annual leave each calendar year.",
            token_count=15,
            score=0.92,
        ),
        ContextChunk(
            source_index=2,
            source_tag="[Doc-2]",
            chunk_id="chunk-uuid-2",
            document_id="doc-uuid-2",
            filename="travel.pdf",
            access_level="internal",
            content="Travel expenses above $500 require prior approval from the department director.",
            token_count=16,
            score=0.88,
        ),
    ]


def test_1_extract_claims_single_and_multiple_sentences(sample_context_chunks):
    extractor = ClaimExtractor()
    text = "Employees receive 20 days of annual leave [Doc-1]. Travel expenses over $500 need director approval [Doc-2]."
    claims = extractor.extract_claims(text, sample_context_chunks)

    assert len(claims) == 2
    assert claims[0].id == "claim-1"
    assert "Employees receive 20 days" in claims[0].text
    assert claims[0].cited_chunk_ids == ["chunk-uuid-1"]
    assert claims[0].raw_tags == ["[Doc-1]"]
    assert claims[0].unmapped_tags == []
    assert claims[0].malformed_tags == []

    assert claims[1].id == "claim-2"
    assert "Travel expenses over $500" in claims[1].text
    assert claims[1].cited_chunk_ids == ["chunk-uuid-2"]
    assert claims[1].raw_tags == ["[Doc-2]"]


def test_2_extract_claims_preserves_unmapped_and_malformed_tags(sample_context_chunks):
    extractor = ClaimExtractor()
    # [Doc-99] is unmapped; [Doc-] and [Document-1] are malformed
    text = "Company health plans cover dental care [Doc-99]. Gym memberships are subsidized [Doc-] and parking is free [Document-1]."
    claims = extractor.extract_claims(text, sample_context_chunks)

    assert len(claims) == 2
    # First claim has unmapped tag
    assert claims[0].unmapped_tags == ["[Doc-99]"]
    assert claims[0].cited_chunk_ids == []

    # Second claim has malformed tags
    assert "[Doc-]" in claims[1].malformed_tags
    assert "[Document-1]" in claims[1].malformed_tags


def test_3_extract_claims_zero_claims_or_empty_text(sample_context_chunks):
    extractor = ClaimExtractor()
    assert extractor.extract_claims("", sample_context_chunks) == []
    assert extractor.extract_claims("   \n  ", sample_context_chunks) == []
    # Short conversational text without substantive claims
    assert extractor.extract_claims("Hello! Thank you.", sample_context_chunks) == []


def test_4_compound_clause_splitting(sample_context_chunks):
    extractor = ClaimExtractor()
    text = (
        "Employees receive twenty days of paid time off per calendar year and standard medical insurance; "
        "however, all international travel bookings must be approved by the finance director before ticketing."
    )
    claims = extractor.extract_claims(text, sample_context_chunks)
    assert len(claims) >= 2
