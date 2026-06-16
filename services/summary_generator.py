"""
services/summary_generator.py
------------------------------
Generates executive summaries and detects missing clauses.
"""

from typing import List, Dict, Any
from models.contract import (
    ExecutiveSummary, MissingClause, ClauseRisk,
    ExtractedClause, RiskLevel, ClauseType
)
from services.gemini_service import get_gemini_service
from prompts.missing_clauses import get_missing_clauses_prompt
from prompts.summary import get_executive_summary_prompt
from utils.logger import logger


class SummaryGenerator:
    """
    Generates two outputs:
    1. Missing clause detection
    2. Executive summary synthesis

    DESIGN DECISION: These are separate methods but in the same service class
    because they share context — both need the full analysis results.
    """

    def detect_missing_clauses(
        self,
        contract_text: str,
        found_clauses: List[ExtractedClause]
    ) -> List[MissingClause]:
        """
        Identify standard legal clauses absent from the contract.

        Args:
            contract_text: Full contract text for context
            found_clauses: Already-extracted clauses to avoid false positives
        """
        found_types = [c.clause_type.value for c in found_clauses]
        logger.info(f"Detecting missing clauses. Found types: {found_types}")

        gemini = get_gemini_service()
        prompt = get_missing_clauses_prompt(contract_text, found_types)

        fallback = {"missing_clauses": [], "completeness_score": 50}
        response = gemini.generate_json(prompt, fallback=fallback)

        raw_missing = response.get("missing_clauses", [])
        missing_clauses = self._parse_missing_clauses(raw_missing)

        logger.info(f"Detected {len(missing_clauses)} missing clauses")
        return missing_clauses

    def generate_executive_summary(
        self,
        contract_text: str,
        found_clauses: List[ExtractedClause],
        clause_risks: List[ClauseRisk],
        missing_clauses: List[MissingClause],
        overall_risk_level: RiskLevel,
        overall_risk_score: int
    ) -> ExecutiveSummary:
        """
        Generate the executive summary from all analysis results.
        """
        logger.info("Generating executive summary...")

        # Build structured data for the prompt
        clauses_data = [
            {"clause_type": c.clause_type.value, "clause_text": c.clause_text[:300]}
            for c in found_clauses
        ]
        risks_data = [
            {
                "clause_type": r.clause_type.value,
                "risk_level": r.risk_level.value,
                "risk_score": r.risk_score,
                "risk_reason": r.risk_reason,
            }
            for r in clause_risks
        ]
        missing_data = [
            {
                "clause_type": m.clause_type.value,
                "importance": m.importance.value,
                "risk_of_absence": m.description,
            }
            for m in missing_clauses
        ]

        gemini = get_gemini_service()
        prompt = get_executive_summary_prompt(
            contract_text_preview=contract_text[:2000],
            found_clauses=clauses_data,
            risk_analyses=risks_data,
            missing_clauses=missing_data,
        )

        fallback = {
            "contract_type": "Commercial Agreement",
            "parties_involved": ["Party A", "Party B"],
            "overall_risk_level": overall_risk_level.value,
            "overall_risk_score": overall_risk_score,
            "summary_text": "Contract analysis complete. Please review the detailed findings below.",
            "key_obligations": ["Review detailed clause analysis for obligations"],
            "key_risks": [f"Overall risk score: {overall_risk_score}/100"],
            "recommended_actions": ["Consult a legal professional for review"],
            "red_flags": []
        }

        response = gemini.generate_json(prompt, fallback=fallback)

        return self._parse_executive_summary(response, overall_risk_level, overall_risk_score)

    def _parse_missing_clauses(self, raw_list):
        """Parse raw AI response into MissingClause models."""
    
        parsed = []

        for raw in raw_list:
            try:
                if not isinstance(raw, dict):
                    logger.warning("Skipping non-dict missing clause entry: {}", raw)
                    continue

                # Clean all keys returned by Gemini
                cleaned = {
                    str(k).strip(): v
                    for k, v in raw.items()
                }

                clause_type_str = cleaned.get(
                    "clause_type",
                    "Unknown Clause"
                )

                clause_type = self._normalize_clause_type(
                    clause_type_str
                )

                importance_str = cleaned.get(
                    "importance",
                    "Medium"
                )

                importance = self._parse_risk_level(
                    importance_str
                )

                description = (
                    cleaned.get("description")
                    or cleaned.get("risk_of_absence")
                    or "No description provided"
                )

                recommendation = cleaned.get(
                    "recommendation",
                    "Add this clause before signing."
                )

                missing = MissingClause(
                    clause_type=clause_type,
                    importance=importance,
                    description=description,
                    recommendation=recommendation,
                )

                parsed.append(missing)

            except Exception as e:
                logger.warning(
                    f"Failed to parse missing clause: {raw}. Error: {e}"
                )

        return parsed

    def _parse_executive_summary(
        self,
        response: Dict,
        overall_risk_level: RiskLevel,
        overall_risk_score: int
    ) -> ExecutiveSummary:
        """Parse AI response into ExecutiveSummary model."""
        try:
            risk_level_str = response.get("overall_risk_level", overall_risk_level.value)
            risk_level = self._parse_risk_level(risk_level_str)

            return ExecutiveSummary(
                overall_risk_level=risk_level,
                overall_risk_score=response.get("overall_risk_score", overall_risk_score),
                summary_text=response.get("summary_text", "Analysis complete."),
                key_obligations=response.get("key_obligations", []),
                key_risks=response.get("key_risks", []),
                recommended_actions=response.get("recommended_actions", []),
                contract_type=response.get("contract_type", "Commercial Agreement"),
                parties_involved=response.get("parties_involved", []),
            )
        except Exception as e:
            logger.error("Failed to parse executive summary: {}", e)
            return ExecutiveSummary(
                overall_risk_level=overall_risk_level,
                overall_risk_score=overall_risk_score,
                summary_text="Summary generation encountered an error. Review detailed findings below.",
                key_obligations=[],
                key_risks=[],
                recommended_actions=["Consult a legal professional"],
                contract_type="Unknown",
                parties_involved=[],
            )

    def _normalize_clause_type(self, raw: str) -> ClauseType:
        type_map = {ct.value.lower(): ct for ct in ClauseType}
        normalized = raw.strip().lower()
        if normalized in type_map:
            return type_map[normalized]
        for key, ct in type_map.items():
            if normalized in key or key in normalized:
                return ct
        return ClauseType.UNKNOWN

    def _parse_risk_level(self, raw: str) -> RiskLevel:
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        return mapping.get(raw.lower().strip(), RiskLevel.MEDIUM)


# Singleton
summary_generator = SummaryGenerator()
