"""
utils/text_cleaner.py
---------------------
Text preprocessing pipeline for extracted PDF content.

WHY THIS MATTERS:
Raw PDF text is noisy — it contains headers, footers, page numbers, 
and encoding artifacts. Cleaning it before sending to Gemini:
1. Reduces token usage (cheaper API calls)
2. Improves AI accuracy (less noise = better signal)
3. Normalizes inconsistent formatting across different PDF sources

Interview talking point: "I built a preprocessing pipeline to normalize 
contract text before AI analysis, which improved extraction accuracy significantly."
"""

import re
from typing import List
from utils.logger import logger


class TextCleaner:
    """
    Multi-stage text cleaning pipeline for legal contract text.
    Each stage targets a specific type of noise found in PDFs.
    """

    # Common legal document noise patterns
    PAGE_NUMBER_PATTERNS = [
        r'^\s*\d+\s*$',                    # Standalone page numbers
        r'Page\s+\d+\s+of\s+\d+',          # "Page 1 of 10"
        r'^\s*-\s*\d+\s*-\s*$',            # "- 1 -" style
    ]

    HEADER_FOOTER_PATTERNS = [
        r'CONFIDENTIAL\s+[-–]\s+DO NOT DISTRIBUTE',
        r'DRAFT\s+[-–]\s+NOT FOR EXECUTION',
        r'©\s+\d{4}.*?All Rights Reserved',
    ]

    def clean(self, raw_text: str) -> str:
        """
        Main cleaning pipeline. Applies all cleaning stages in order.
        
        Args:
            raw_text: Raw text extracted from PDF
            
        Returns:
            Cleaned, normalized text ready for AI analysis
        """
        if not raw_text or not raw_text.strip():
            return ""

        text = raw_text

        # Stage 1: Fix encoding artifacts
        text = self._fix_encoding(text)

        # Stage 2: Remove page numbers and headers/footers
        text = self._remove_page_artifacts(text)

        # Stage 3: Normalize whitespace
        text = self._normalize_whitespace(text)

        # Stage 4: Fix hyphenation (PDF line-break hyphens)
        text = self._fix_hyphenation(text)

        # Stage 5: Remove excessive punctuation artifacts
        text = self._remove_noise_patterns(text)

        # Stage 6: Final trim
        text = text.strip()

        logger.debug(f"Text cleaned: {len(raw_text)} → {len(text)} chars "
                     f"({100 - round(len(text)/max(len(raw_text),1)*100)}% reduction)")

        return text

    def _fix_encoding(self, text: str) -> str:
        """Fix common PDF encoding artifacts."""
        replacements = {
            '\x00': '',         # Null bytes
            '\uf0b7': '•',      # Bullet point artifact
            '\u2019': "'",      # Smart apostrophe
            '\u201c': '"',      # Left smart quote
            '\u201d': '"',      # Right smart quote
            '\u2013': '-',      # En dash
            '\u2014': '--',     # Em dash
            '\u00a0': ' ',      # Non-breaking space
            '\t': ' ',          # Tab to space
        }
        for artifact, replacement in replacements.items():
            text = text.replace(artifact, replacement)
        return text

    def _remove_page_artifacts(self, text: str) -> str:
        """Remove page numbers, headers, and footers."""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            should_remove = False

            # Check page number patterns
            for pattern in self.PAGE_NUMBER_PATTERNS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    should_remove = True
                    break

            # Check header/footer patterns
            if not should_remove:
                for pattern in self.HEADER_FOOTER_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_remove = True
                        break

            if not should_remove:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace while preserving paragraph structure.
        Legal documents use paragraph breaks as semantic separators.
        """
        # Replace 3+ newlines with double newline (preserve paragraphs)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)

        # Clean up spaces around newlines
        text = re.sub(r' \n', '\n', text)
        text = re.sub(r'\n ', '\n', text)

        return text

    def _fix_hyphenation(self, text: str) -> str:
        """
        Fix PDF line-break hyphenation.
        PDFs often break words like "termin-\nation" across lines.
        """
        # Join hyphenated words across lines
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        return text

    def _remove_noise_patterns(self, text: str) -> str:
        """Remove common legal document noise patterns."""
        # Remove sequences of underscores (signature lines)
        text = re.sub(r'_{5,}', '', text)

        # Remove sequences of dots (table of contents leaders)
        text = re.sub(r'\.{5,}', '', text)

        # Remove lines that are just special characters
        text = re.sub(r'^[^\w\s]+$', '', text, flags=re.MULTILINE)

        return text

    def split_into_chunks(self, text: str, chunk_size: int = 8000) -> List[str]:
        """
        Split long contracts into overlapping chunks for AI processing.
        
        WHY OVERLAPPING CHUNKS:
        - Gemini has a context window limit
        - Clauses can span multiple chunks — overlap ensures we don't miss them
        - 500 char overlap provides continuity between chunks
        
        Args:
            text: Full contract text
            chunk_size: Max characters per chunk
            
        Returns:
            List of text chunks with overlap
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        overlap = 500
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at paragraph boundary to preserve context
            if end < len(text):
                paragraph_break = text.rfind('\n\n', start, end)
                if paragraph_break > start + chunk_size // 2:
                    end = paragraph_break

            chunks.append(text[start:end])
            start = end - overlap  # Overlap with previous chunk

        logger.info(f"Contract split into {len(chunks)} chunks (size={chunk_size}, overlap={overlap})")
        return chunks


# Singleton instance for use across the app
text_cleaner = TextCleaner()
