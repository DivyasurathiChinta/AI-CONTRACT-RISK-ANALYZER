"""
models/contract.py
------------------
Pydantic data models (schemas) for all contract-related entities.

WHY PYDANTIC:
- Automatic validation and serialization
- Auto-generated OpenAPI docs in FastAPI
- Type safety across the entire pipeline
- Interview talking point: "Pydantic models act as contracts between layers"
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


# ─────────────────────────────────────────────
# ENUMS — strongly typed constants
# ─────────────────────────────────────────────

class RiskLevel(str, Enum):
    """
    Using str + Enum means JSON serialization gives "High" not 2.
    FastAPI automatically validates that only these values are accepted.
    """
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ClauseType(str, Enum):
    """Standard legal clause categories we extract from contracts."""
    PAYMENT_TERMS = "Payment Terms"
    TERMINATION = "Termination Clause"
    CONFIDENTIALITY = "Confidentiality Clause"
    LIABILITY = "Liability Clause"
    INDEMNIFICATION = "Indemnification Clause"
    GOVERNING_LAW = "Governing Law Clause"
    INTELLECTUAL_PROPERTY = "Intellectual Property Clause"
    DATA_PROTECTION = "Data Protection Clause"
    DISPUTE_RESOLUTION = "Dispute Resolution Clause"
    FORCE_MAJEURE = "Force Majeure Clause"
    NON_COMPETE = "Non-Compete Clause"
    AMENDMENT = "Amendment Clause"
    UNKNOWN = "Unknown Clause"


# ─────────────────────────────────────────────
# CORE MODELS
# ─────────────────────────────────────────────

class ExtractedClause(BaseModel):
    """
    Represents a single clause extracted from a contract.
    This is the atomic unit of our analysis pipeline.
    """
    clause_type: ClauseType = Field(..., description="Category of the legal clause")
    clause_text: str = Field(..., description="The actual text of the clause from the contract")
    page_number: Optional[int] = Field(None, description="Page where clause was found")
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="AI confidence in clause classification (0.0 - 1.0)"
    )


class ClauseRisk(BaseModel):
    """
    Risk assessment for a single extracted clause.
    Maps 1:1 with ExtractedClause after risk analysis.
    """
    clause_type: ClauseType
    clause_text: str
    risk_level: RiskLevel
    risk_score: int = Field(..., ge=0, le=100, description="Numeric risk score 0-100")
    risk_reason: str = Field(..., description="Plain English explanation of why this is risky")
    recommendation: str = Field(..., description="Specific action to mitigate the risk")
    key_issues: List[str] = Field(default_factory=list, description="Bullet points of specific issues")


class MissingClause(BaseModel):
    """
    Represents a standard clause that is absent from the contract.
    Missing clauses are their own risk category.
    """
    clause_type: ClauseType
    importance: RiskLevel = Field(..., description="How critical it is that this clause exists")
    description: str = Field(..., description="What this clause would protect")
    recommendation: str = Field(..., description="Suggested clause text or action")


class ExecutiveSummary(BaseModel):
    """
    High-level AI-generated summary of the entire contract analysis.
    This is what a senior lawyer or executive would read first.
    """
    overall_risk_level: RiskLevel
    overall_risk_score: int = Field(..., ge=0, le=100)
    summary_text: str = Field(..., description="2-3 paragraph executive summary")
    key_obligations: List[str] = Field(
        default_factory=list,
        description="Top obligations for each party"
    )
    key_risks: List[str] = Field(
        default_factory=list,
        description="Most critical risks identified"
    )
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Prioritized action items"
    )
    contract_type: str = Field(default="Unknown", description="Inferred contract type")
    parties_involved: List[str] = Field(default_factory=list, description="Contract parties")


class ContractAnalysisResult(BaseModel):
    """
    The complete analysis result returned to the frontend.
    This is the top-level response object for the /analyze endpoint.
    
    DESIGN DECISION: We bundle everything into one response rather than
    multiple API calls. This reduces network round trips and simplifies
    frontend state management.
    """
    # Metadata
    filename: str
    analysis_id: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    total_pages: int
    word_count: int

    # Core Analysis Results
    extracted_clauses: List[ExtractedClause] = Field(default_factory=list)
    clause_risks: List[ClauseRisk] = Field(default_factory=list)
    missing_clauses: List[MissingClause] = Field(default_factory=list)
    executive_summary: Optional[ExecutiveSummary] = None

    # Computed Stats
    total_clauses_found: int = 0
    total_missing_clauses: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0

    def compute_stats(self):
        """Populate computed fields from analysis results."""
        self.total_clauses_found = len(self.extracted_clauses)
        self.total_missing_clauses = len(self.missing_clauses)
        self.high_risk_count = sum(
            1 for r in self.clause_risks if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        self.medium_risk_count = sum(
            1 for r in self.clause_risks if r.risk_level == RiskLevel.MEDIUM
        )
        self.low_risk_count = sum(
            1 for r in self.clause_risks if r.risk_level == RiskLevel.LOW
        )


# ─────────────────────────────────────────────
# API REQUEST / RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class AnalysisStatusResponse(BaseModel):
    """Response for health check and status endpoints."""
    status: str
    message: str
    version: str


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    error: str
    detail: str
    status_code: int
