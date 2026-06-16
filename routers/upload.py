"""
routers/upload.py
-----------------
FastAPI router for file upload endpoints.

REST API DESIGN:
POST /upload/ → Upload a PDF and receive a file_id for tracking
GET  /upload/health → Check service health

WHY SEPARATE UPLOAD FROM ANALYSIS:
This follows the separation of concerns principle. Upload handles the file,
analysis handles the AI processing. In production, you'd use a job queue
(Celery/RQ) between them for async processing of large contracts.

Interview talking point: "I separated upload from analysis so we can add
async processing with a job queue later without changing the upload contract."
"""

import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from utils.file_handler import file_handler
from utils.logger import logger
from app.config import settings

router = APIRouter(prefix="/upload", tags=["File Upload"])


@router.post(
    "/",
    summary="Upload a contract PDF",
    description=(
        "Upload a PDF contract file for analysis. "
        "Returns a file_id to use with the /analyze endpoint."
    ),
    response_description="File upload confirmation with file_id",
)
async def upload_contract(
    file: UploadFile = File(..., description="PDF contract file to analyze")
) -> JSONResponse:
    """
    Upload a contract PDF file.

    - **Validates**: Only PDF files accepted (max 10MB by default)
    - **Stores**: File saved with UUID name for security
    - **Returns**: file_id to reference in subsequent analysis calls

    Example response:
    ```json
    {
        "status": "success",
        "file_id": "abc12345-def6-...",
        "original_filename": "service_agreement.pdf",
        "file_size_kb": 245.3,
        "message": "File uploaded successfully. Use file_id to start analysis."
    }
    ```
    """
    try:
        logger.info(f"Upload request: filename='{file.filename}', size={file.size}")

        # Save file securely
        saved_filename, file_path = await file_handler.save_upload(file)

        # Get file size for response
        file_size_kb = file_path.stat().st_size / 1024

        logger.info(f"Upload successful: {saved_filename} ({file_size_kb:.1f}KB)")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "file_id": saved_filename.replace(".pdf", ""),
                "saved_filename": saved_filename,
                "original_filename": file.filename,
                "file_size_kb": round(file_size_kb, 2),
                "message": "File uploaded successfully. Use file_id to start analysis.",
            }
        )

    except HTTPException:
        raise  # Re-raise FastAPI HTTP exceptions as-is

    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get(
    "/health",
    summary="Check upload service health",
)
async def upload_health() -> JSONResponse:
    """Check if the upload service and storage directory are operational."""
    upload_dir = Path(settings.upload_dir)
    return JSONResponse(content={
        "status": "healthy",
        "upload_dir": str(upload_dir.absolute()),
        "upload_dir_exists": upload_dir.exists(),
        "max_file_size_mb": settings.max_file_size_mb,
    })
