"""
services/risk_analyzer.py
--------------------------
Risk analysis engine — evaluates risk for each extracted clause.

DESIGN PATTERN: Pipeline Pattern
Input: List[ExtractedClause] → Process each → Output: List[ClauseRisk]

WHY ANALYZE CLAUSES INDIVIDUALLY (not as a batch):
1. More focused context window per call = better accuracy
2. If one clause analysis fails, others succeed (fault isolation)
3. Cleaner error reporting per clause
4. Easier to add clause-specific prompt customization later

Trade-off: More API calls but higher quality output.
"""

from typing import List
from models.contract import ExtractedClause, ClauseRisk, RiskLevel
from services.gemini_service import get_gemini_service
from prompts.risk_analysis import get_risk_analysis_prompt, get_batch_risk_analysis_prompt
from utils.logger import logger


class RiskAnalyzer:
    """
    Analyzes risk level of each extracted contract clause.
    """

    # Default fallback risk when AI analysis fails
    DEFAULT_FALLBACK_RISK = {
        "risk_level": "Medium",
        "risk_score": 50,
        "risk_reason": "Risk analysis could not be completed for this clause. Manual review recommended.",
        "recommendation": "Have a legal professional review this clause.",
        "key_issues": ["Unable to complete automated analysis"],
        "favorable_to": "Unknown",
        "missing_protections": []
    }

    def analyze_all(self, clauses: List[ExtractedClause]) -> List[ClauseRisk]:
        """
        Analyze risk for all extracted clauses.
        
        Args:
            clauses: List of extracted clause objects
            
        Returns:
            List of ClauseRisk objects with full risk assessment
        """
        if not clauses:
            logger.warning("No clauses provided for risk analysis")
            return []

        logger.info(f"Starting batch risk analysis for {len(clauses)} clauses")
        
        # Prepare list of dicts for the prompt
        clauses_data = [
            {"clause_type": c.clause_type.value, "clause_text": c.clause_text}
            for c in clauses
        ]
        
        gemini = get_gemini_service()
        prompt = get_batch_risk_analysis_prompt(clauses_data)
        
        fallback = {"analyses": []}
        response = gemini.generate_json(prompt, fallback=fallback)
        analyses = response.get("analyses", [])
        
        # Map back to ClauseRisk objects, aligning by clause type (or position as fallback)
        results = []
        matched_indices = set()
        
        for raw_analysis in analyses:

            if isinstance(raw_analysis, dict):
                raw_analysis = {
                    str(k).strip(): v
                    for k, v in raw_analysis.items()
                }

            raw_type_str = raw_analysis.get("clause_type", "")
            
            # Find an unmatched clause with a similar type
            match_index = None
            for idx, c in enumerate(clauses):
                if idx not in matched_indices:
                    if (c.clause_type.value.lower() in raw_type_str.lower() or 
                            raw_type_str.lower() in c.clause_type.value.lower()):
                        match_index = idx
                        break
            
            # Fallback to the first unmatched index if no type match is found
            if match_index is None:
                for idx in range(len(clauses)):
                    if idx not in matched_indices:
                        match_index = idx
                        break
            
            if match_index is not None:
                matched_indices.add(match_index)
                clause = clauses[match_index]
                risk = self._parse_risk_response(clause, raw_analysis)
                if risk:
                    results.append(risk)
                    
        # For any clauses that weren't matched (or if AI returned incomplete results), use fallback
        for idx, clause in enumerate(clauses):
            if idx not in matched_indices:
                logger.warning(f"Clause {clause.clause_type.value} was not analyzed in batch, using fallback.")
                risk = self._parse_risk_response(clause, self.DEFAULT_FALLBACK_RISK)
                results.append(risk)

        # Sort by risk score descending (highest risk first)
        results.sort(key=lambda r: r.risk_score, reverse=True)

        # Log risk distribution
        self._log_risk_summary(results)

        return results

    def _analyze_single_clause(self, clause: ExtractedClause) -> ClauseRisk:
        """
        Analyze a single clause and return risk assessment.
        Falls back gracefully if AI call fails.
        (Kept as fallback or for direct individual calls)
        """
        gemini = get_gemini_service()
        prompt = get_risk_analysis_prompt(
            clause_type=clause.clause_type.value,
            clause_text=clause.clause_text
        )

        response = gemini.generate_json(prompt, fallback=self.DEFAULT_FALLBACK_RISK)

        return self._parse_risk_response(clause, response)

    def _parse_risk_response(self, clause: ExtractedClause, response: dict) -> ClauseRisk:
        """
        Convert AI response dict to ClauseRisk model.
        Validates and sanitizes all fields.
        """

        if isinstance(response, dict):
            response = {
                str(k).strip(): v
                for k, v in response.items()
            }

        try:
            # Parse risk level — normalize AI response to enum
            risk_level_str = response.get("risk_level", "Medium")
            risk_level = self._parse_risk_level(risk_level_str)

            # Parse and clamp risk score
            raw_score = response.get("risk_score", 50)
            risk_score = max(0, min(100, int(raw_score)))

            # Cross-validate: score should match level
            risk_score = self._calibrate_score(risk_score, risk_level)

            # Build ClauseRisk
            return ClauseRisk(
                clause_type=clause.clause_type,
                clause_text=clause.clause_text,
                risk_level=risk_level,
                risk_score=risk_score,
                risk_reason=response.get("risk_reason", "Analysis unavailable"),
                recommendation=response.get("recommendation", "Manual review recommended"),
                key_issues=response.get("key_issues", []),
            )

        except Exception as e:
            logger.error("Failed to parse risk response for {}: {}", clause.clause_type, e)
            # Return minimum viable risk assessment
            return ClauseRisk(
                clause_type=clause.clause_type,
                clause_text=clause.clause_text,
                risk_level=RiskLevel.MEDIUM,
                risk_score=50,
                risk_reason="Analysis error — manual review recommended.",
                recommendation="Consult a legal professional for this clause.",
                key_issues=["Automated analysis failed"],
            )

    def _parse_risk_level(self, raw: str) -> RiskLevel:
        """Map AI-returned risk level string to enum."""
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        return mapping.get(raw.lower().strip(), RiskLevel.MEDIUM)

    def _calibrate_score(self, score: int, level: RiskLevel) -> int:
        """
        Ensure score is within the expected range for the risk level.
        
        If AI says "High" but gives score 30, we calibrate to 65+ (minimum for High).
        This prevents conflicting signals to the user.
        """
        ranges = {
            RiskLevel.LOW: (0, 40),
            RiskLevel.MEDIUM: (41, 60),
            RiskLevel.HIGH: (61, 80),
            RiskLevel.CRITICAL: (81, 100),
        }
        min_score, max_score = ranges[level]
        if not (min_score <= score <= max_score):
            # Calibrate to midpoint of expected range
            calibrated = (min_score + max_score) // 2
            logger.debug(f"Calibrated risk score: {score} → {calibrated} (level={level})")
            return calibrated
        return score

    def _log_risk_summary(self, results: List[ClauseRisk]) -> None:
        """Log risk distribution for monitoring."""
        counts = {level: 0 for level in RiskLevel}
        for r in results:
            counts[r.risk_level] += 1

        avg_score = sum(r.risk_score for r in results) / max(len(results), 1)
        logger.info(
            f"Risk analysis complete: "
            f"Critical={counts[RiskLevel.CRITICAL]}, "
            f"High={counts[RiskLevel.HIGH]}, "
            f"Medium={counts[RiskLevel.MEDIUM]}, "
            f"Low={counts[RiskLevel.LOW]}, "
            f"Avg Score={avg_score:.1f}"
        )

    def compute_overall_risk_score(self, clause_risks: List[ClauseRisk]) -> tuple:
        """
        Compute overall contract risk score from individual clause scores.
        
        ALGORITHM: Weighted average with extra weight on highest risks.
        Top 3 highest risks count for 60% of the overall score.
        Remaining clauses count for 40%.
        
        WHY NOT SIMPLE AVERAGE:
        A contract with one critical clause (score 95) and 10 low-risk clauses
        should be HIGH risk, not MEDIUM. Simple average would understate the risk.
        """
        if not clause_risks:
            return RiskLevel.LOW, 0

        scores = sorted([r.risk_score for r in clause_risks], reverse=True)

        if len(scores) <= 3:
            overall_score = sum(scores) / len(scores)
        else:
            # Top 3 weighted at 60%, rest at 40%
            top_3_avg = sum(scores[:3]) / 3
            rest_avg = sum(scores[3:]) / len(scores[3:])
            overall_score = (top_3_avg * 0.6) + (rest_avg * 0.4)

        overall_score = round(overall_score)

        # Floor overall risk based on the single highest risk clause to prevent understating risk
        if scores:
            max_score = scores[0]
            if max_score >= 81:    # Critical clause exists -> overall risk at least High (61)
                overall_score = max(overall_score, 61)
            elif max_score >= 61:  # High clause exists -> overall risk at least Medium (41)
                overall_score = max(overall_score, 41)

        # Map score to level
        if overall_score >= 81:
            level = RiskLevel.CRITICAL
        elif overall_score >= 61:
            level = RiskLevel.HIGH
        elif overall_score >= 41:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        return level, overall_score


# Singleton
risk_analyzer = RiskAnalyzer()
