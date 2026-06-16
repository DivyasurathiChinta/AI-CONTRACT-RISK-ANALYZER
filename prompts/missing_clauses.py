"""
prompts/missing_clauses.py
--------------------------
Prompt for detecting standard clauses absent from a contract.

KEY INSIGHT: Missing clause detection is separate from risk analysis.
A contract with no termination clause isn't just "risky" — it's legally dangerous
in a way that clause-level analysis can't capture. This requires knowing what
SHOULD be in a contract and what ISN'T.

Interview talking point: "I treated missing clause detection as a separate
analytical task with its own specialized prompt, rather than conflating it
with clause risk analysis."
"""


def get_missing_clauses_prompt(contract_text: str, found_clause_types: list) -> str:
    """
    Detect standard legal clauses that are missing from the contract.
    
    Args:
        contract_text: Full contract text
        found_clause_types: List of clause types already identified
    """
    found_clauses_str = "\n".join([f"- {ct}" for ct in found_clause_types]) if found_clause_types else "- None identified yet"

    return f"""You are a senior contract lawyer reviewing a contract for completeness.
Your task is to identify MISSING standard clauses that should be in this type of contract.

CLAUSES ALREADY FOUND IN THIS CONTRACT:
{found_clauses_str}

STANDARD CLAUSES CHECKLIST (check which are missing):
1. Payment Terms — Payment schedule, amounts, late payment penalties
2. Termination Clause — How either party can end the agreement
3. Confidentiality Clause — Protection of sensitive information (NDA provisions)
4. Liability Clause — Limitation of liability, exclusions
5. Indemnification Clause — Who indemnifies whom for what losses
6. Governing Law Clause — Which jurisdiction's laws apply
7. Intellectual Property Clause — Ownership of created IP
8. Data Protection Clause — GDPR/CCPA compliance, data handling
9. Dispute Resolution Clause — Arbitration vs litigation, venue
10. Force Majeure Clause — Acts of God, pandemic, war provisions
11. Non-Compete Clause — Restrictions after contract ends (if applicable)
12. Amendment Clause — How contract can be modified

IMPORTANT: Compare the checklist against CLAUSES ALREADY FOUND.
Only report clauses that are TRULY ABSENT from the contract text.

CONTRACT TEXT:
---
{contract_text[:6000]}
---

OUTPUT FORMAT (strict JSON):
{{
  "missing_clauses": [
    {{
      "clause_type": "exact name from checklist above",
      "importance": "Low|Medium|High|Critical",
      "description": "What this clause would protect the parties from",
      "risk_of_absence": "Specific legal or business risk if this clause is missing",
      "recommendation": "Suggested action or sample clause language to add"
    }}
  ],
  "completeness_score": 0-100,
  "assessment": "Overall completeness assessment in 1-2 sentences"
}}

IMPORTANCE GUIDE:
- Critical: Absence creates immediate legal exposure
- High: Missing protection could be exploited easily
- Medium: Standard protection but may not apply to all contracts
- Low: Best practice but not always required

Return ONLY valid JSON."""
