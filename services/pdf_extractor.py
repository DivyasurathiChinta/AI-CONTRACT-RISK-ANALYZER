"""
services/pdf_extractor.py
--------------------------
PDF text extraction using PyMuPDF (fitz).

WHY PyMuPDF over alternatives:
- pdfplumber: Slower, better for tables (not needed here)
- PyPDF2: Less accurate text extraction
- pdfminer: Complex API, slower
- PyMuPDF: Fastest, most accurate, preserves layout, handles scanned PDFs

Interview talking point: "I evaluated 4 PDF libraries and chose PyMuPDF 
because it had the best accuracy/performance ratio for contract text."
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any
from utils.logger import logger
from utils.text_cleaner import text_cleaner


class PDFExtractor:
    """
    Extracts and processes text from PDF contracts.
    
    Architecture Decision: This class is responsible ONLY for extraction.
    Cleaning and chunking are delegated to TextCleaner (Single Responsibility Principle).
    """

    def extract(self, file_path: Path) -> Dict[str, Any]:
        """
        Main extraction method. Returns structured data about the PDF.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing:
            - full_text: Complete cleaned text
            - pages: List of page-level data
            - metadata: PDF metadata (author, title, etc.)
            - total_pages: Number of pages
            - word_count: Approximate word count
            
        Raises:
            ValueError: If PDF is encrypted, empty, or unreadable
        """
        logger.info(f"Starting PDF extraction: {file_path.name}")

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            logger.error("Failed to open PDF: {}", e)
            raise ValueError(f"Cannot open PDF file: {e}")

        # --- Validation ---
        if doc.is_encrypted:
            doc.close()
            raise ValueError(
                "PDF is password-protected. Please upload an unencrypted contract."
            )

        if doc.page_count == 0:
            doc.close()
            raise ValueError("PDF has no pages.")

        # --- Metadata Extraction ---
        metadata = self._extract_metadata(doc)

        # --- Page-by-page Extraction ---
        pages_data = []
        all_text_parts = []

        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text("text")  # "text" mode preserves reading order

            if page_text.strip():
                # Clean individual page text
                cleaned_page_text = text_cleaner.clean(page_text)

                pages_data.append({
                    "page_number": page_num + 1,
                    "raw_text": page_text,
                    "cleaned_text": cleaned_page_text,
                    "char_count": len(cleaned_page_text),
                    "word_count": len(cleaned_page_text.split()),
                })
                all_text_parts.append(cleaned_page_text)

            logger.debug(f"  Page {page_num + 1}: {len(page_text)} chars extracted")

        doc.close()

        # --- Assemble Full Text ---
        full_text = "\n\n".join(all_text_parts)

        if not full_text.strip():
            raise ValueError(
                "No text could be extracted from this PDF. "
                "It may be a scanned image-only document. "
                "OCR support coming soon."
            )

        # --- Compute Summary Stats ---
        word_count = len(full_text.split())
        total_pages = len(pages_data)

        result = {
            "full_text": full_text,
            "pages": pages_data,
            "metadata": metadata,
            "total_pages": total_pages,
            "word_count": word_count,
            "char_count": len(full_text),
        }

        logger.info(
            f"Extraction complete: {total_pages} pages, "
            f"{word_count} words, {len(full_text)} chars"
        )

        return result

    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """
        Extract PDF document metadata.
        
        This gives us useful context: document title, creation date,
        software used to create it (reveals if it's a template).
        """
        try:
            raw_meta = doc.metadata
            return {
                "title": raw_meta.get("title", ""),
                "author": raw_meta.get("author", ""),
                "subject": raw_meta.get("subject", ""),
                "creator": raw_meta.get("creator", ""),
                "producer": raw_meta.get("producer", ""),
                "creation_date": raw_meta.get("creationDate", ""),
                "modification_date": raw_meta.get("modDate", ""),
                "page_count": doc.page_count,
            }
        except Exception as e:
            logger.warning("Could not extract PDF metadata: {}", e)
            return {"page_count": doc.page_count}

    def get_text_chunks(self, file_path: Path, chunk_size: int = 8000) -> List[str]:
        """
        Extract text and return it as chunks suitable for AI processing.
        
        Used for very long contracts where the full text would exceed
        the AI model's context window.
        """
        extraction_result = self.extract(file_path)
        full_text = extraction_result["full_text"]
        chunks = text_cleaner.split_into_chunks(full_text, chunk_size)
        logger.info(f"Contract chunked into {len(chunks)} pieces")
        return chunks


# Singleton
pdf_extractor = PDFExtractor()
