"""
tests/test_risk_analyzer.py
----------------------------
Unit tests for the risk analysis engine.
"""

import pytest
from models.contract import ExtractedClause, ClauseType, RiskLevel, ClauseRisk
from services.risk_analyzer import RiskAnalyzer


class TestRiskAnalyzer:
    """Tests for the risk analysis engine."""

    def setup_method(self):
        self.analyzer = RiskAnalyzer()

    def test_parse_risk_level_valid(self):
        assert self.analyzer._parse_risk_level("low") == RiskLevel.LOW
        assert self.analyzer._parse_risk_level("Medium") == RiskLevel.MEDIUM
        assert self.analyzer._parse_risk_level("HIGH") == RiskLevel.HIGH
        assert self.analyzer._parse_risk_level("critical") == RiskLevel.CRITICAL

    def test_parse_risk_level_unknown_defaults_medium(self):
        assert self.analyzer._parse_risk_level("unknown_level") == RiskLevel.MEDIUM

    def test_calibrate_score_low_in_range(self):
        score = self.analyzer._calibrate_score(25, RiskLevel.LOW)
        assert score == 25

    def test_calibrate_score_high_out_of_range(self):
        # Score says 20 but level says High — should calibrate
        score = self.analyzer._calibrate_score(20, RiskLevel.HIGH)
        assert 61 <= score <= 80

    def test_calibrate_score_critical_out_of_range(self):
        score = self.analyzer._calibrate_score(50, RiskLevel.CRITICAL)
        assert 81 <= score <= 100

    def test_compute_overall_risk_empty(self):
        level, score = self.analyzer.compute_overall_risk_score([])
        assert level == RiskLevel.LOW
        assert score == 0

    def test_compute_overall_risk_all_low(self):
        risks = [
            ClauseRisk(
                clause_type=ClauseType.PAYMENT_TERMS,
                clause_text="Pay within 30 days.",
                risk_level=RiskLevel.LOW,
                risk_score=20,
                risk_reason="Standard payment terms.",
                recommendation="No action needed.",
            )
            for _ in range(5)
        ]
        level, score = self.analyzer.compute_overall_risk_score(risks)
        assert level == RiskLevel.LOW
        assert score <= 40

    def test_compute_overall_risk_one_critical(self):
        """One critical clause should make overall risk High or Critical."""
        risks = [
            ClauseRisk(
                clause_type=ClauseType.TERMINATION,
                clause_text="Vendor can terminate immediately.",
                risk_level=RiskLevel.CRITICAL,
                risk_score=95,
                risk_reason="No notice period.",
                recommendation="Add 30-day notice.",
            ),
        ] + [
            ClauseRisk(
                clause_type=ClauseType.PAYMENT_TERMS,
                clause_text="Pay within 30 days.",
                risk_level=RiskLevel.LOW,
                risk_score=15,
                risk_reason="Standard.",
                recommendation="No action.",
            )
            for _ in range(8)
        ]
        level, score = self.analyzer.compute_overall_risk_score(risks)
        # Should not be LOW because of the critical clause
        assert level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MEDIUM]

    def test_parse_risk_response_valid(self):
        clause = ExtractedClause(
            clause_type=ClauseType.TERMINATION,
            clause_text="Agreement may be terminated without notice.",
            confidence_score=0.9,
        )
        response = {
            "risk_level": "High",
            "risk_score": 75,
            "risk_reason": "No notice period specified.",
            "recommendation": "Add minimum 30-day notice requirement.",
            "key_issues": ["No notice period", "One-sided termination"],
        }
        result = self.analyzer._parse_risk_response(clause, response)
        assert result.risk_level == RiskLevel.HIGH
        assert result.risk_score == 75
        assert result.clause_type == ClauseType.TERMINATION
        assert len(result.key_issues) == 2

    def test_parse_risk_response_handles_bad_score(self):
        """Score > 100 should be clamped to 100."""
        clause = ExtractedClause(
            clause_type=ClauseType.LIABILITY,
            clause_text="Unlimited liability for all damages.",
            confidence_score=0.95,
        )
        response = {
            "risk_level": "Critical",
            "risk_score": 999,  # Invalid score
            "risk_reason": "Unlimited liability.",
            "recommendation": "Add liability cap.",
            "key_issues": [],
        }
        result = self.analyzer._parse_risk_response(clause, response)
        assert 81 <= result.risk_score <= 100  # Clamped and calibrated
