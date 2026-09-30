import re
from typing import List, Dict, Set, Optional
from pydantic import BaseModel, Field

from app.schemas.generation import ContextChunk


class ExtractedClaim(BaseModel):
    """Internal representation of an atomic factual claim extracted from LLM text."""
    id: str
    text: str
    cited_chunk_ids: List[str] = Field(default_factory=list)
    raw_tags: List[str] = Field(default_factory=list)
    unmapped_tags: List[str] = Field(default_factory=list)
    malformed_tags: List[str] = Field(default_factory=list)


class ClaimExtractor:
    """Deterministic extractor of factual claims and pre-sanitization citation diagnostics."""

    # Sentence boundary regex handling common punctuation
    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\[])|\n+")
    
    # Valid tag pattern: [Doc-1], [Doc-12]
    VALID_TAG_REGEX = re.compile(r"\[Doc-(\d+)\]")
    
    # Malformed or unrecognized tag patterns
    MALFORMED_TAG_REGEX = re.compile(
        r"\[Doc\s*-\s*\]|\[Document-\d+\]|\[Doc\s+\d+\]|\[Doc:[^\]]+\]", 
        re.IGNORECASE
    )

    def extract_claims(
        self,
        raw_text: str,
        supplied_chunks: List[ContextChunk],
    ) -> List[ExtractedClaim]:
        """Split generated answer into atomic claims and extract citation diagnostics before sanitization."""
        if not raw_text or not raw_text.strip():
            return []

        chunk_index_to_id: Dict[int, str] = {c.source_index: c.chunk_id for c in supplied_chunks}

        # 1. Split text into candidate sentences
        raw_sentences = self.SENTENCE_SPLIT_REGEX.split(raw_text.strip())
        
        claims: List[ExtractedClaim] = []
        claim_counter = 1

        for raw_sentence in raw_sentences:
            sentence = raw_sentence.strip()
            if not sentence:
                continue

            # Detect all citation patterns in this sentence
            raw_tags: List[str] = []
            cited_chunk_ids: List[str] = []
            unmapped_tags: List[str] = []
            malformed_tags: List[str] = []

            # Check valid tag matches
            for match in self.VALID_TAG_REGEX.finditer(sentence):
                full_tag = match.group(0)
                raw_tags.append(full_tag)
                idx = int(match.group(1))
                if idx in chunk_index_to_id:
                    cited_chunk_ids.append(chunk_index_to_id[idx])
                else:
                    unmapped_tags.append(full_tag)

            # Check malformed tag matches
            for match in self.MALFORMED_TAG_REGEX.finditer(sentence):
                malformed_tags.append(match.group(0))

            # Strip citation tags from the claim statement text for clean NLI evaluation
            clean_text = self.VALID_TAG_REGEX.sub("", sentence)
            clean_text = self.MALFORMED_TAG_REGEX.sub("", clean_text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            # Ignore conversational greetings, questions, or trivial phrases
            lower_clean = clean_text.lower().strip(" .!?,;:")
            conversational_phrases = {
                "hello", "hi", "hey", "thank you", "thanks", "you're welcome", 
                "how can i help you today", "how can i help you", "good morning", "good afternoon",
                "let me know if you need anything else", "hope this helps"
            }
            if (
                len(clean_text) < 15
                or lower_clean in conversational_phrases
                or clean_text.endswith("?")
                or not re.search(r"[a-zA-Z0-9]", clean_text)
            ):
                continue

            # Split compound clauses on major coordinating contrastive conjunctions if long enough
            sub_clauses = self._split_compound_clause(clean_text)

            for sub_clause in sub_clauses:
                sub_clean = sub_clause.strip()
                if len(sub_clean) < 10:
                    continue

                claims.append(
                    ExtractedClaim(
                        id=f"claim-{claim_counter}",
                        text=sub_clean,
                        cited_chunk_ids=list(dict.fromkeys(cited_chunk_ids)),  # preserve order, deduplicate
                        raw_tags=list(dict.fromkeys(raw_tags)),
                        unmapped_tags=list(dict.fromkeys(unmapped_tags)),
                        malformed_tags=list(dict.fromkeys(malformed_tags)),
                    )
                )
                claim_counter += 1

        return claims

    def _split_compound_clause(self, text: str) -> List[str]:
        """Optionally split very long compound sentences on strong contrastive conjunctions."""
        if len(text) < 120:
            return [text]

        split_pattern = re.compile(
            r";\s*|\s*,\s*(?:however|furthermore|whereas|nevertheless)\s*,\s*",
            re.IGNORECASE
        )
        parts = split_pattern.split(text)
        return [p.strip() for p in parts if len(p.strip()) >= 10] or [text]


claim_extractor = ClaimExtractor()
