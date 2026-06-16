"""
routers/analysis.py
--------------------
FastAPI router for contract analysis endpoints.

API DESIGN:
POST /analyze/{file_id}  → Run full analysis on uploaded contract
GET  /analyze/status     → Check analysis service status

SYNCHRONOUS vs ASYNC ANALYSIS:
Currently synchronous (waits for full analysis before responding).
For production, this would be async with WebSockets or polling:
  POST /analyze/{file_id} → returns job_id immediately
  GET  /jobs/{job_id}     → poll for status/results

Interview talking point: "I designed the API to be sync-first for simplicity,
but the architecture is ready for async: the orchestrator can be called from
a Celery task with no code changes."
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from services.contract_analyzer import contract_analyzer
from utils.file_handler import file_handler
from utils.logger import logger, format_api_error
from models.contract import ContractAnalysisResult
from app.config import settings

router = APIRouter(prefix="/analyze", tags=["Contract Analysis"])


@router.post(
    "/{file_id}",
    summary="Analyze a contract",
    description=(
        "Run the full AI analysis pipeline on an uploaded contract. "
        "This triggers: clause extraction, risk analysis, missing clause detection, "
        "and executive summary generation."
    ),
    response_model=ContractAnalysisResult,
)
def analyze_contract(
    file_id: str,
    background_tasks: BackgroundTasks,
    original_filename: str = "contract.pdf",
    delete_after_analysis: bool = True,
) -> ContractAnalysisResult:
    """
    Run complete AI contract analysis.

    - **file_id**: The file_id returned from POST /upload/
    - **original_filename**: Original display name (from upload response)
    - **delete_after_analysis**: Auto-delete file after analysis (GDPR compliance)

    Returns a complete ContractAnalysisResult with:
    - Extracted clauses with classifications
    - Risk assessment per clause (score 0-100, level, reason, recommendation)
    - Missing clause detection
    - Executive summary
    """
    # Reconstruct filename from file_id
    saved_filename = f"{file_id}.pdf"

    # Verify file exists
    try:
        file_path = file_handler.get_file_path(saved_filename)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"File '{file_id}' not found. "
                "Please upload the file first using POST /upload/"
            )
        )

    logger.info(f"Analysis request: file_id={file_id}, filename='{original_filename}'")

    try:
        # Run the full pipeline
        result = contract_analyzer.analyze(file_path, original_filename)

        # Schedule file deletion in background (after response is sent)
        if delete_after_analysis:
            background_tasks.add_task(
                _cleanup_file,
                saved_filename,
                file_id
            )

        logger.info(f"Analysis complete for {file_id}: {result.total_clauses_found} clauses found")
        return result

    except ValueError as e:
        # PDF-level errors (encrypted, empty, unreadable)
        logger.error("PDF processing error for {}: {}", file_id, e)
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        # Do not use f-strings with {e}: Gemini errors contain `{description: ...}`
        # which Loguru treats as format placeholders and raises KeyError.
        logger.exception("Analysis failed for file_id={}", file_id)
        user_message = format_api_error(e)
        status_code = 429 if "quota" in user_message.lower() else 500
        raise HTTPException(status_code=status_code, detail=user_message)


@router.get(
    "/status",
    summary="Check analysis service status",
)
async def analysis_status() -> JSONResponse:
    """
    Check if the analysis service is operational.
    Verifies Gemini API key is configured.
    """
    gemini_configured = settings.validate_gemini_key()

    return JSONResponse(content={
        "status": "operational" if gemini_configured else "misconfigured",
        "gemini_configured": gemini_configured,
        "model": settings.gemini_model,
        "message": (
            "Ready to analyze contracts."
            if gemini_configured
            else "GEMINI_API_KEY not configured. Set it in .env file."
        )
    })


def _cleanup_file(saved_filename: str, file_id: str):
    """Background task to delete file after analysis (data minimization)."""
    try:
        file_handler.delete_file(saved_filename)
        logger.info(f"Cleaned up file after analysis: {file_id}")
    except Exception as e:
        logger.warning("Failed to delete file {}: {}", file_id, e)
