"""
tests/test_pdf_extractor.py
----------------------------
Unit tests for the PDF extraction service.

WHY UNIT TESTS MATTER FOR INTERVIEWS:
Showing tests demonstrates production mindset — you don't just write code,
you verify it works. This is a strong differentiator for internship candidates.

Run: pytest tests/ -v
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from services.pdf_extractor import PDFExtractor
from utils.text_cleaner import TextCleaner


class TestTextCleaner:
    """Tests for the text preprocessing pipeline."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_clean_removes_null_bytes(self):
        raw = "Hello\x00 World"
        result = self.cleaner.clean(raw)
        assert "\x00" not in result
        assert "Hello" in result

    def test_clean_normalizes_smart_quotes(self):
        raw = "\u201cThis is quoted\u201d"
        result = self.cleaner.clean(raw)
        assert '"This is quoted"' in result

    def test_clean_removes_multiple_newlines(self):
        raw = "Paragraph 1\n\n\n\n\nParagraph 2"
        result = self.cleaner.clean(raw)
        assert "\n\n\n" not in result

    def test_clean_removes_page_numbers(self):
        raw = "Some text\n\n1\n\nMore text"
        result = self.cleaner.clean(raw)
        assert result.count("\n1\n") == 0

    def test_clean_empty_string(self):
        result = self.cleaner.clean("")
        assert result == ""

    def test_clean_whitespace_only(self):
        result = self.cleaner.clean("   \n  \t  ")
        assert result == ""

    def test_split_into_chunks_short_text(self):
        text = "Short text that fits in one chunk"
        chunks = self.cleaner.split_into_chunks(text, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_into_chunks_long_text(self):
        text = "A" * 20000
        chunks = self.cleaner.split_into_chunks(text, chunk_size=8000)
        assert len(chunks) > 1
        # Each chunk should not exceed chunk_size significantly
        for chunk in chunks:
            assert len(chunk) <= 9000  # Allow small overage

    def test_fix_hyphenation(self):
        raw = "termin-\nation clause applies"
        result = self.cleaner.clean(raw)
        assert "termination" in result.lower()


class TestPDFExtractor:
    """Tests for PDF extraction service."""

    def setup_method(self):
        self.extractor = PDFExtractor()

    def test_extract_raises_on_missing_file(self):
        """Should raise ValueError for non-existent file."""
        with pytest.raises((ValueError, Exception)):
            self.extractor.extract(Path("nonexistent_file.pdf"))

    @patch("fitz.open")
    def test_extract_raises_on_encrypted_pdf(self, mock_open):
        """Should raise ValueError with helpful message for encrypted PDFs."""
        mock_doc = MagicMock()
        mock_doc.is_encrypted = True
        mock_doc.page_count = 5
        mock_open.return_value = mock_doc

        with pytest.raises(ValueError, match="password-protected"):
            self.extractor.extract(Path("encrypted.pdf"))

    @patch("fitz.open")
    def test_extract_raises_on_empty_pdf(self, mock_open):
        """Should raise ValueError for PDFs with no pages."""
        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.page_count = 0
        mock_open.return_value = mock_doc

        with pytest.raises(ValueError, match="no pages"):
            self.extractor.extract(Path("empty.pdf"))

    @patch("fitz.open")
    def test_extract_returns_structured_data(self, mock_open):
        """Should return dict with expected keys."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is a payment terms clause. The vendor shall pay within 30 days."

        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.page_count = 1
        mock_doc.__getitem__ = lambda self, i: mock_page
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.metadata = {"title": "Test Contract", "author": "Test"}
        mock_open.return_value = mock_doc

        result = self.extractor.extract(Path("test.pdf"))

        assert "full_text" in result
        assert "total_pages" in result
        assert "word_count" in result
        assert "metadata" in result
        assert result["total_pages"] == 1
        assert result["word_count"] > 0
