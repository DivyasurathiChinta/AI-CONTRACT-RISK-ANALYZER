"""
prompts/clause_extraction.py
-----------------------------
Optimized Gemini prompts for clause extraction.

PROMPT ENGINEERING PRINCIPLES used here:
1. Role Assignment: "You are a senior legal analyst..." — sets AI persona
2. Structured Output: JSON schema specified — ensures parseable responses
3. Few-shot Examples: Show the AI what good output looks like
4. Explicit Constraints: "ONLY output valid JSON" — reduces hallucination
5. Chain-of-Thought: "Think step by step" — improves accuracy on complex tasks

Interview talking point: "I engineered prompts using role-prompting, 
structured output constraints, and few-shot examples to get consistent, 
parseable JSON from the LLM."
"""


def get_clause_extraction_prompt(contract_text: str) -> str:
    """
    Prompt for identifying and classifying legal clauses.
    
    Design Decision: We use explicit JSON schema in the prompt so Gemini
    returns structured data we can parse without brittle regex.
    """
    return f"""You are a senior legal analyst and AI assistant specializing in contract review.
Your task is to carefully read the provided contract text and extract all legal clauses.

INSTRUCTIONS:
1. Identify all distinct legal clauses in the contract
2. Classify each clause into one of the provided categories
3. Extract the exact relevant text for each clause
4. Return ONLY valid JSON — no explanations, no markdown, no preamble

CLAUSE CATEGORIES (use exactly these names):
- "Payment Terms"
- "Termination Clause"
- "Confidentiality Clause"
- "Liability Clause"
- "Indemnification Clause"
- "Governing Law Clause"
- "Intellectual Property Clause"
- "Data Protection Clause"
- "Dispute Resolution Clause"
- "Force Majeure Clause"
- "Non-Compete Clause"
- "Amendment Clause"
- "Unknown Clause" (for clauses that don't fit above categories)

REQUIRED OUTPUT FORMAT (strict JSON):
{{
  "clauses": [
    {{
      "clause_type": "Payment Terms",
      "clause_text": "The exact relevant text from the contract...",
      "confidence_score": 0.95,
      "page_hint": "Section 3.1 or similar reference if visible"
    }}
  ],
  "total_clauses_found": 5,
  "notes": "Any observations about the contract structure"
}}

IMPORTANT RULES:
- Extract the ACTUAL text from the contract, do not paraphrase
- If a clause type appears multiple times, include each instance separately
- confidence_score must be between 0.0 and 1.0
- Do not invent clauses that aren't in the document
- If a section is ambiguous, classify as "Unknown Clause"

CONTRACT TEXT TO ANALYZE:
---
{contract_text}
---

Return ONLY the JSON object. Start your response with {{ and end with }}."""


def get_clause_extraction_prompt_chunked(chunk_text: str, chunk_index: int, total_chunks: int) -> str:
    """
    Variant prompt for processing one chunk of a multi-chunk contract.
    Includes context about position in the document.
    """
    return f"""You are a senior legal analyst reviewing contract documents.
This is chunk {chunk_index + 1} of {total_chunks} from a larger contract.

Extract all legal clauses from THIS SECTION ONLY.
Note: Some clauses may continue from the previous section or continue into the next.
If a clause appears incomplete (cut off), include what is visible and mark confidence_score lower.

CLAUSE CATEGORIES (use exactly these names):
- "Payment Terms", "Termination Clause", "Confidentiality Clause"
- "Liability Clause", "Indemnification Clause", "Governing Law Clause"
- "Intellectual Property Clause", "Data Protection Clause"
- "Dispute Resolution Clause", "Force Majeure Clause"
- "Non-Compete Clause", "Amendment Clause", "Unknown Clause"

OUTPUT FORMAT:
{{
  "clauses": [
    {{
      "clause_type": "string",
      "clause_text": "exact text from document",
      "confidence_score": 0.0-1.0,
      "page_hint": "section reference if visible",
      "is_complete": true
    }}
  ],
  "total_clauses_found": 0
}}

CONTRACT SECTION {chunk_index + 1}/{total_chunks}:
---
{chunk_text}
---

Return ONLY valid JSON."""
