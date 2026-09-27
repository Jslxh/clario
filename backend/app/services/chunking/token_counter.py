from app.core.config import settings


class TokenCounter:
    """Isolated token counting service.
    
    Currently uses character-based token estimation (4.0 characters per token).
    Can be replaced in future phases with tiktoken or model-aware tokenizers.
    """

    def __init__(self, chars_per_token: float = settings.CHARS_PER_TOKEN):
        self.chars_per_token = chars_per_token

    def count_tokens(self, text: str) -> int:
        """Estimate token count for a string of text."""
        if not text:
            return 0
        return max(1, int(len(text) / self.chars_per_token))

    def max_chars_for_tokens(self, tokens: int) -> int:
        """Convert token count to maximum character length."""
        return int(tokens * self.chars_per_token)


token_counter = TokenCounter()
