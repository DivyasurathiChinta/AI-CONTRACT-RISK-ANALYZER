"""
prompts/summary.py
------------------
Prompt for generating executive summaries of contract analysis results.

DESIGN PRINCIPLE: The summary prompt receives STRUCTURED DATA (the analysis results),
not raw contract text. This is more reliable than asking the AI to re-read the contract.

Interview talking point: "My summary generation works on the structured analysis output,
not re-reading the contract. This ensures the summary is grounded in the actual findings
rather than the AI's independent interpretation."
"""
import json
from typing import List, Dict, Any


def get_executive_summary_prompt(
    contract_text_preview: str,
    found_clauses: List[Dict],
    risk_analyses: List[Dict],
    missing_clauses: List[Dict]
) -> str:
    """
    Generate executive summary from structured analysis results.
    
    Args:
        contract_text_preview: First 2000 chars of contract for context
        found_clauses: List of extracted clause dicts
        risk_analyses: List of risk analysis result dicts
        missing_clauses: List of missing clause dicts
    """
    # Summarize findings for the prompt
    high_risks = [r for r in risk_analyses if r.get("risk_level") in ["High", "Critical"]]
    medium_risks = [r for r in risk_analyses if r.get("risk_level") == "Medium"]

    risk_summary = "\n".join([
        f"- [{r.get('risk_level')}] {r.get('clause_type')}: {r.get('risk_reason', '')[:150]}"
        for r in high_risks[:5]  # Top 5 high risks
    ]) or "No high risks identified"

    missing_summary = "\n".join([
        f"- [{m.get('importance')}] {m.get('clause_type')}: {m.get('risk_of_absence', '')[:100]}"
        for m in missing_clauses[:5]
    ]) or "No missing clauses detected"

    return f"""You are a senior contract risk advisor preparing an executive briefing document.
Based on the analysis results below, generate a comprehensive executive summary.

=== ANALYSIS RESULTS ===

CONTRACT PREVIEW (first section):
{contract_text_preview[:1500]}

TOTAL CLAUSES FOUND: {len(found_clauses)}
CLAUSES WITH HIGH/CRITICAL RISK: {len(high_risks)}
CLAUSES WITH MEDIUM RISK: {len(medium_risks)}
MISSING STANDARD CLAUSES: {len(missing_clauses)}

TOP RISKS IDENTIFIED:
{risk_summary}

MISSING CLAUSES:
{missing_summary}

=== YOUR TASK ===

Generate an executive summary that:
1. Identifies the contract type and parties (infer from text)
2. Summarizes overall risk posture in business language (not legal jargon)
3. Lists the 5 most important obligations for each party
4. Provides prioritized action items

OUTPUT FORMAT (strict JSON):
{{
  "contract_type": "Software License Agreement|Service Agreement|NDA|Employment Contract|...",
  "parties_involved": ["Party 1 name/role", "Party 2 name/role"],
  "overall_risk_level": "Low|Medium|High|Critical",
  "overall_risk_score": 0-100,
  "summary_text": "3-4 sentence executive summary that a CEO would understand. Be direct about risks.",
  "key_obligations": [
    "Party 1 must pay $X by Y date",
    "Party 2 must deliver Z within W days",
    "Both parties must maintain confidentiality for N years"
  ],
  "key_risks": [
    "Most critical risk and its business impact",
    "Second most important risk",
    "Third risk"
  ],
  "recommended_actions": [
    "IMMEDIATE: Action to take before signing",
    "BEFORE SIGNING: Negotiation point",
    "OPTIONAL: Nice-to-have improvement"
  ],
  "red_flags": ["List any serious red flags that require immediate legal counsel"]
}}

Write for a business executive audience. Use plain English.
Quantify risks where possible (e.g., "unlimited liability exposure" vs "liability").
Return ONLY valid JSON."""
