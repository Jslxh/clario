import os
import uuid
import tempfile
import pytest
from pypdf import PdfWriter
import docx

from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.docx_parser import DOCXParser
from app.services.parsers.txt_parser import TXTParser
from app.services.parsers.factory import ParserFactory
from app.core.exceptions import UnsupportedParserError, CorruptFileError


def create_test_pdf_with_pages(tmp_path) -> str:
    """Helper to create a valid 3-page PDF fixture (Page 1: text, Page 2: empty, Page 3: text)."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    
    pdf_path = tmp_path / "multi_page_test.pdf"
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return str(pdf_path)


def test_1_2_3_pdf_parsing_pages_and_boundaries(tmp_path):
    """1, 2, 3. Verify PDF parser page boundaries, multi-page parsing, and empty page handling."""
    pdf_path = create_test_pdf_with_pages(tmp_path)
    parser = PDFParser()
    doc_id = str(uuid.uuid4())
    
    parsed = parser.parse(pdf_path, doc_id, "multi_page_test.pdf")
    
    assert parsed.document_id == doc_id
    assert parsed.document_type == "pdf"
    assert parsed.total_pages == 3
    assert len(parsed.pages) == 3
    assert parsed.pages[0].page_number == 1
    assert parsed.pages[1].page_number == 2
    assert parsed.pages[2].page_number == 3


def test_4_5_docx_paragraphs_and_headings(tmp_path):
    """4 & 5. Verify DOCX paragraph order and heading extraction in sections."""
    doc = docx.Document()
    doc.add_heading("Executive Summary", level=1)
    doc.add_paragraph("First paragraph detailing project objectives.")
    doc.add_heading("System Architecture", level=2)
    doc.add_paragraph("Second paragraph detailing database design.")
    
    docx_path = tmp_path / "test_doc.docx"
    doc.save(docx_path)
    
    parser = DOCXParser()
    doc_id = str(uuid.uuid4())
    parsed = parser.parse(str(docx_path), doc_id, "test_doc.docx")
    
    assert parsed.document_type == "docx"
    assert parsed.has_usable_text is True
    assert len(parsed.pages) == 1
    assert "Executive Summary" in parsed.pages[0].sections
    assert "System Architecture" in parsed.pages[0].sections
    assert "First paragraph detailing project objectives." in parsed.pages[0].text
    assert "Second paragraph detailing database design." in parsed.pages[0].text


def test_6_txt_extraction(tmp_path):
    """6. Verify plain text extraction."""
    txt_path = tmp_path / "sample.txt"
    txt_content = "Clario Enterprise Knowledge Platform\nLine 2 text."
    txt_path.write_text(txt_content, encoding="utf-8")
    
    parser = TXTParser()
    doc_id = str(uuid.uuid4())
    parsed = parser.parse(str(txt_path), doc_id, "sample.txt")
    
    assert parsed.document_type == "txt"
    assert parsed.has_usable_text is True
    assert parsed.total_pages == 1
    assert parsed.pages[0].text == txt_content


def test_7_empty_txt_extraction(tmp_path):
    """7. Verify empty TXT file returns has_usable_text=False."""
    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("", encoding="utf-8")
    
    parser = TXTParser()
    doc_id = str(uuid.uuid4())
    parsed = parser.parse(str(empty_path), doc_id, "empty.txt")
    
    assert parsed.has_usable_text is False
    assert parsed.pages[0].text == ""


def test_8_corrupt_pdf_handling(tmp_path):
    """8. Verify corrupt/invalid PDF raises CorruptFileError."""
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-1.4 Not a valid PDF structure random bytes")
    
    parser = PDFParser()
    with pytest.raises(CorruptFileError) as exc_info:
        parser.parse(str(corrupt_pdf), str(uuid.uuid4()), "corrupt.pdf")
    assert "corrupt" in str(exc_info.value).lower()


def test_9_corrupt_docx_handling(tmp_path):
    """9. Verify corrupt/invalid DOCX raises CorruptFileError."""
    corrupt_docx = tmp_path / "corrupt.docx"
    corrupt_docx.write_bytes(b"PK\x03\x04 invalid zip archive content")
    
    parser = DOCXParser()
    with pytest.raises(CorruptFileError) as exc_info:
        parser.parse(str(corrupt_docx), str(uuid.uuid4()), "corrupt.docx")
    assert "corrupt" in str(exc_info.value).lower()


def test_10_unsupported_parser_type():
    """10. Verify unsupported parser/type raises UnsupportedParserError."""
    with pytest.raises(UnsupportedParserError) as exc_info:
        ParserFactory.get_parser("xlsx")
    assert "No parser available" in str(exc_info.value)


def test_11_unicode_text_extraction(tmp_path):
    """11. Verify multi-byte Unicode text extraction across languages and symbols."""
    unicode_path = tmp_path / "unicode.txt"
    unicode_text = "Clario Knowledge Platform — 日本語テキスト • Café, Naïve & €1000 — 🚀 Multi-byte"
    unicode_path.write_text(unicode_text, encoding="utf-8")
    
    parser = TXTParser()
    parsed = parser.parse(str(unicode_path), str(uuid.uuid4()), "unicode.txt")
    
    assert parsed.has_usable_text is True
    assert "日本語テキスト" in parsed.pages[0].text
    assert "Café, Naïve & €1000" in parsed.pages[0].text
