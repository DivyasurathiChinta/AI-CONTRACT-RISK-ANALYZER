"""
prompts/risk_analysis.py
------------------------
Optimized Gemini prompts for risk detection and scoring.

PROMPT ENGINEERING TECHNIQUE: Structured Scoring Rubric
We provide an explicit scoring rubric (0-100 scale definitions) to ensure
the AI scores consistently. Without this, scores can drift between calls.

Interview talking point: "I designed a rubric-based scoring prompt to ensure
consistent, calibrated risk scores across different contracts and API calls."
"""


def get_risk_analysis_prompt(clause_type: str, clause_text: str) -> str:
    """
    Analyze risk level of a single extracted clause.
    
    Design: We analyze ONE clause at a time for:
    1. Higher accuracy (focused context window)
    2. Granular error handling (if one clause fails, others still succeed)
    3. Better audit trail (can trace exactly which prompt caused what output)
    """
    return f"""You are an expert legal risk analyst with 20 years of experience reviewing commercial contracts.
Analyze the following contract clause and assess its risk level.

CLAUSE TYPE: {clause_type}
CLAUSE TEXT:
---
{clause_text}
---

RISK SCORING RUBRIC (use this exact scale):
- 0-20 (Low): Standard industry clause, balanced obligations, clear terms
- 21-40 (Low-Medium): Slightly favorable to one party but acceptable
- 41-60 (Medium): One-sided but not unusual, missing some protections
- 61-80 (High): Significantly unfavorable, missing important safeguards
- 81-100 (Critical): Extremely one-sided, major legal exposure, dangerous terms

RISK LEVEL MAPPING:
- Score 0-40 → Risk Level: "Low"
- Score 41-60 → Risk Level: "Medium"
- Score 61-80 → Risk Level: "High"
- Score 81-100 → Risk Level: "Critical"

REQUIRED OUTPUT FORMAT (strict JSON):
{{
  "clause_type": "{clause_type}",
  "risk_level": "Low|Medium|High|Critical",
  "risk_score": 0-100,
  "risk_reason": "Plain English explanation of why this clause is risky. Write as if explaining to a non-lawyer executive. Be specific about what could go wrong.",
  "recommendation": "Specific, actionable recommendation to reduce the risk. Start with an action verb.",
  "key_issues": [
    "First specific issue with this clause",
    "Second specific issue",
    "Third specific issue if applicable"
  ],
  "favorable_to": "Vendor|Client|Neutral",
  "missing_protections": ["List any standard protections that are absent"]
}}

ANALYSIS GUIDELINES:
- Consider industry standard practices for this clause type
- Identify power imbalances between parties
- Flag vague or ambiguous language that could be exploited
- Check for missing standard protections (notice periods, liability caps, etc.)
- Consider worst-case interpretations of ambiguous terms

Return ONLY the JSON object. Start with {{ and end with }}."""


def get_batch_risk_analysis_prompt(clauses: list) -> str:
    """
    Analyze multiple clauses in a single API call (more efficient for short clauses).
    
    Trade-off: Fewer API calls vs potentially less focused analysis.
    Use this for contracts with many short clauses.
    """
    clauses_formatted = "\n\n".join([
        f"CLAUSE {i+1} ({c.get('clause_type', 'Unknown')}):\n{c.get('clause_text', '')}"
        for i, c in enumerate(clauses)
    ])

    return f"""You are an expert legal risk analyst with 20 years of experience reviewing commercial contracts.
Analyze ALL of the following contract clauses and assess their risk levels.

{clauses_formatted}

RISK SCORING RUBRIC (use this exact scale):
- 0-20 (Low): Standard industry clause, balanced obligations, clear terms
- 21-40 (Low-Medium): Slightly favorable to one party but acceptable
- 41-60 (Medium): One-sided but not unusual, missing some protections
- 61-80 (High): Significantly unfavorable, missing important safeguards
- 81-100 (Critical): Extremely one-sided, major legal exposure, dangerous terms

RISK LEVEL MAPPING:
- Score 0-40 → Risk Level: "Low"
- Score 41-60 → Risk Level: "Medium"
- Score 61-80 → Risk Level: "High"
- Score 81-100 → Risk Level: "Critical"

REQUIRED OUTPUT FORMAT (strict JSON):
{{
  "analyses": [
    {{
      "clause_type": "exact clause type from above",
      "risk_level": "Low|Medium|High|Critical",
      "risk_score": 0-100,
      "risk_reason": "Plain English explanation of why this clause is risky. Write as if explaining to a non-lawyer executive. Be specific about what could go wrong.",
      "recommendation": "Specific, actionable recommendation to reduce the risk. Start with an action verb.",
      "key_issues": [
        "First specific issue with this clause",
        "Second specific issue"
      ],
      "favorable_to": "Vendor|Client|Neutral",
      "missing_protections": ["List any standard protections that are absent"]
    }}
  ]
}}

ANALYSIS GUIDELINES:
- Consider industry standard practices for this clause type
- Identify power imbalances between parties
- Flag vague or ambiguous language that could be exploited
- Check for missing standard protections (notice periods, liability caps, etc.)

Analyze ALL {len(clauses)} clauses. Return ONLY the JSON object. Start with {{ and end with }}."""
