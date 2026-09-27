class ParsingError(Exception):
    """Base exception for document parsing failures."""
    def __init__(self, message: str, document_type: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.document_type = document_type


class UnsupportedParserError(ParsingError):
    """Raised when no parser is registered for the specified document type."""
    pass


class CorruptFileError(ParsingError):
    """Raised when the document file is corrupted or unreadable by the parser."""
    pass


class NoExtractableTextError(ParsingError):
    """Raised when document contains no extractable text (e.g. image-only/scanned PDF or empty file)."""
    pass
