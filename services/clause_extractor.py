"""
services/clause_extractor.py
-----------------------------
Orchestrates clause extraction from contract text using Gemini AI.

ORCHESTRATION PATTERN:
This service coordinates between:
1. Prompts layer (what to ask)
2. Gemini service (how to ask it)
3. Models layer (how to structure the answer)

It does NOT do the AI work itself — it orchestrates other services.
This is the "Service Orchestrator" pattern in microservices architecture.
"""

from typing import List, Dict, Any
from models.contract import ExtractedClause, ClauseType
from services.gemini_service import get_gemini_service
from prompts.clause_extraction import (
    get_clause_extraction_prompt,
    get_clause_extraction_prompt_chunked
)
from utils.text_cleaner import text_cleaner
from utils.logger import logger


class ClauseExtractor:
    """
    Extracts and classifies legal clauses from contract text.
    
    Handles both:
    - Short contracts: Single API call with full text
    - Long contracts: Chunked processing with deduplication
    """

    # Minimum text length to attempt extraction (avoid processing empty sections)
    MIN_TEXT_LENGTH = 100

    # Threshold for splitting into chunks
    CHUNK_THRESHOLD = 12000  # characters

    def extract_clauses(self, contract_text: str) -> List[ExtractedClause]:
        """
        Main entry point. Extracts all clauses from contract text.
        
        Args:
            contract_text: Full cleaned contract text
            
        Returns:
            List of ExtractedClause objects
        """
        if len(contract_text) < self.MIN_TEXT_LENGTH:
            logger.warning("Contract text too short for clause extraction")
            return []

        logger.info(f"Starting clause extraction: {len(contract_text)} chars")

        # Choose strategy based on contract length
        if len(contract_text) <= self.CHUNK_THRESHOLD:
            clauses = self._extract_single(contract_text)
        else:
            clauses = self._extract_chunked(contract_text)

        logger.info(f"Extracted {len(clauses)} clauses total")
        return clauses

    def _extract_single(self, contract_text: str) -> List[ExtractedClause]:
        """
        Extract clauses from short contracts in a single API call.
        More accurate than chunked — full context available to AI.
        """
        gemini = get_gemini_service()
        prompt = get_clause_extraction_prompt(contract_text)

        fallback = {"clauses": [], "total_clauses_found": 0}
        response = gemini.generate_json(prompt, fallback=fallback)

        return self._parse_clauses(response.get("clauses", []))

    def _extract_chunked(self, contract_text: str) -> List[ExtractedClause]:
        """
        Extract clauses from long contracts by processing chunks.
        
        DEDUPLICATION STRATEGY:
        The same clause can appear in multiple chunks (due to overlap).
        We deduplicate by clause type, keeping the most complete version.
        """
        chunks = text_cleaner.split_into_chunks(contract_text, chunk_size=8000)
        gemini = get_gemini_service()

        all_raw_clauses = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            prompt = get_clause_extraction_prompt_chunked(chunk, i, len(chunks))

            fallback = {"clauses": [], "total_clauses_found": 0}
            response = gemini.generate_json(prompt, fallback=fallback)
            chunk_clauses = response.get("clauses", [])

            all_raw_clauses.extend(chunk_clauses)
            logger.debug(f"Chunk {i+1}: Found {len(chunk_clauses)} clauses")

        # Deduplicate — keep longest text for each clause type
        deduplicated = self._deduplicate_clauses(all_raw_clauses)
        return self._parse_clauses(deduplicated)

    def _deduplicate_clauses(self, raw_clauses: List[Dict]) -> List[Dict]:
        """
        Remove duplicate clauses that appear due to chunk overlap.
        
        Strategy: For each clause type, keep the instance with the longest text
        (longer text = more complete clause).
        """
        # Group by clause type
        by_type: Dict[str, List[Dict]] = {}
        for clause in raw_clauses:
            ct = clause.get("clause_type", "Unknown Clause")
            if ct not in by_type:
                by_type[ct] = []
            by_type[ct].append(clause)

        # Keep the longest text for each type
        deduplicated = []
        for clause_type, instances in by_type.items():
            best = max(instances, key=lambda c: len(c.get("clause_text", "")))
            deduplicated.append(best)

        logger.debug(f"Deduplication: {sum(len(v) for v in by_type.values())} → {len(deduplicated)} clauses")
        return deduplicated

    def _parse_clauses(self, raw_clauses: List[Dict]) -> List[ExtractedClause]:
        """
        Convert raw API response dicts into typed ExtractedClause objects.
        
        Handles malformed/unexpected AI responses gracefully.
        """
        parsed = []

        for raw in raw_clauses:
            try:
                # Normalize clause type to match our enum
                raw_type = raw.get("clause_type", "Unknown Clause")
                clause_type = self._normalize_clause_type(raw_type)

                clause = ExtractedClause(
                    clause_type=clause_type,
                    clause_text=raw.get("clause_text", "").strip(),
                    page_number=None,  # Estimated from page_hint if available
                    confidence_score=float(raw.get("confidence_score", 0.8)),
                )

                # Skip empty or very short clause texts
                if len(clause.clause_text) < 10:
                    continue

                parsed.append(clause)

            except Exception as e:
                logger.warning("Failed to parse clause: {}. Error: {}", raw, e)
                continue

        return parsed

    def _normalize_clause_type(self, raw_type: str) -> ClauseType:
        """
        Map AI-returned clause type strings to our ClauseType enum.
        
        The AI might return "Payment Terms" or "payment terms" or "Payment terms".
        We normalize all variations to our canonical enum values.
        """
        # Build a case-insensitive lookup map
        type_map = {ct.value.lower(): ct for ct in ClauseType}

        normalized = raw_type.strip().lower()

        # Direct match
        if normalized in type_map:
            return type_map[normalized]

        # Partial match (e.g., "payment" → "Payment Terms")
        for key, clause_type in type_map.items():
            if normalized in key or key in normalized:
                return clause_type

        logger.debug(f"Unknown clause type '{raw_type}', defaulting to Unknown")
        return ClauseType.UNKNOWN


# Singleton
clause_extractor = ClauseExtractor()
