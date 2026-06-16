"""
services/contract_analyzer.py
------------------------------
Main orchestrator — coordinates the full analysis pipeline.

PIPELINE DESIGN:
PDF Extract → Clean Text → Extract Clauses → Analyze Risk →
Detect Missing Clauses → Generate Summary → Return Results

WHY AN ORCHESTRATOR:
Each service does ONE thing well (SRP). The orchestrator composes them
into a complete pipeline. This makes each step independently testable
and replaceable without touching the others.

Interview talking point: "I followed the Single Responsibility Principle —
each service has exactly one reason to change. The orchestrator wires them
together without any business logic of its own."
"""

import uuid
from pathlib import Path
from typing import Dict, Any

from models.contract import ContractAnalysisResult
from services.pdf_extractor import pdf_extractor
from services.clause_extractor import clause_extractor
from services.risk_analyzer import risk_analyzer
from services.summary_generator import summary_generator
from utils.logger import logger


class ContractAnalyzer:
    """
    Orchestrates the complete contract analysis pipeline.

    Step 1: Extract text from PDF (PyMuPDF)
    Step 2: Extract & classify clauses (Gemini)
    Step 3: Analyze risk per clause (Gemini)
    Step 4: Detect missing clauses (Gemini)
    Step 5: Generate executive summary (Gemini)
    Step 6: Assemble and return structured result
    """

    def analyze(self, file_path: Path, original_filename: str) -> ContractAnalysisResult:
        """
        Run the full analysis pipeline on a contract PDF.

        Args:
            file_path: Path to the saved PDF file
            original_filename: Original filename from upload (for display)

        Returns:
            ContractAnalysisResult with all analysis data

        Raises:
            ValueError: If PDF cannot be processed
            RuntimeError: If AI analysis fails critically
        """
        analysis_id = str(uuid.uuid4())[:8].upper()
        logger.info(f"[{analysis_id}] Starting analysis: {original_filename}")

        # ── STEP 1: PDF Text Extraction ──────────────────────────────────
        logger.info(f"[{analysis_id}] Step 1/5: Extracting PDF text...")
        extraction_data = pdf_extractor.extract(file_path)

        contract_text = extraction_data["full_text"]
        total_pages = extraction_data["total_pages"]
        word_count = extraction_data["word_count"]

        logger.info(
            f"[{analysis_id}] Extracted: {total_pages} pages, "
            f"{word_count} words, {len(contract_text)} chars"
        )

        # ── STEP 2: Clause Extraction ─────────────────────────────────────
        logger.info(f"[{analysis_id}] Step 2/5: Extracting clauses...")
        extracted_clauses = clause_extractor.extract_clauses(contract_text)
        logger.info(f"[{analysis_id}] Found {len(extracted_clauses)} clauses")

        # ── STEP 3: Risk Analysis ─────────────────────────────────────────
        logger.info(f"[{analysis_id}] Step 3/5: Analyzing clause risks...")
        clause_risks = risk_analyzer.analyze_all(extracted_clauses)

        overall_risk_level, overall_risk_score = risk_analyzer.compute_overall_risk_score(clause_risks)
        logger.info(
            f"[{analysis_id}] Overall risk: {overall_risk_level.value} "
            f"(score={overall_risk_score})"
        )

        # ── STEP 4: Missing Clause Detection ──────────────────────────────
        logger.info(f"[{analysis_id}] Step 4/5: Detecting missing clauses...")
        missing_clauses = summary_generator.detect_missing_clauses(
            contract_text, extracted_clauses
        )
        logger.info(f"[{analysis_id}] Missing clauses: {len(missing_clauses)}")

        # ── STEP 5: Executive Summary ─────────────────────────────────────
        logger.info(f"[{analysis_id}] Step 5/5: Generating executive summary...")
        executive_summary = summary_generator.generate_executive_summary(
            contract_text=contract_text,
            found_clauses=extracted_clauses,
            clause_risks=clause_risks,
            missing_clauses=missing_clauses,
            overall_risk_level=overall_risk_level,
            overall_risk_score=overall_risk_score,
        )

        # ── STEP 6: Assemble Result ───────────────────────────────────────
        result = ContractAnalysisResult(
            filename=original_filename,
            analysis_id=analysis_id,
            total_pages=total_pages,
            word_count=word_count,
            extracted_clauses=extracted_clauses,
            clause_risks=clause_risks,
            missing_clauses=missing_clauses,
            executive_summary=executive_summary,
        )

        # Populate computed stats
        result.compute_stats()

        logger.info(
            f"[{analysis_id}] Analysis complete: "
            f"{result.total_clauses_found} clauses, "
            f"{result.high_risk_count} high/critical risks, "
            f"{result.total_missing_clauses} missing clauses"
        )

        return result


# Singleton
contract_analyzer = ContractAnalyzer()
