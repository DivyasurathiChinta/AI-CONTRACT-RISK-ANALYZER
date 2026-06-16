"""
utils/file_handler.py
---------------------
Secure file upload handling and management.

SECURITY CONSIDERATIONS (important for interviews):
1. Validate MIME type, not just extension (attackers can rename files)
2. Generate UUID filenames (prevents path traversal attacks)
3. Enforce file size limits (prevents DoS attacks)
4. Store uploads in isolated directory (not web-accessible root)
"""

import os
import uuid
import shutil
import aiofiles
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException
from utils.logger import logger
from app.config import settings


class FileHandler:
    """Handles secure file upload, storage, and cleanup."""

    # Only accept PDF files
    ALLOWED_MIME_TYPES = {"application/pdf"}
    ALLOWED_EXTENSIONS = {".pdf"}

    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        """Create upload directory if it doesn't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory ready: {self.upload_dir.absolute()}")

    def _validate_file(self, file: UploadFile) -> None:
        """
        Validate file before saving.
        
        SECURITY: We check content_type (set by browser) AND file extension.
        Neither alone is sufficient — always validate both.
        """
        # Check extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Only PDF files are accepted. Got: {file_ext}"
            )

        # Check MIME type
        if file.content_type and file.content_type not in self.ALLOWED_MIME_TYPES:
            # Some browsers send application/octet-stream for PDFs — allow it
            if file.content_type != "application/octet-stream":
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid MIME type: {file.content_type}. Expected: application/pdf"
                )

        logger.debug(f"File validation passed: {file.filename}, type={file.content_type}")

    async def save_upload(self, file: UploadFile) -> Tuple[str, Path]:
        """
        Securely save an uploaded file to disk.
        
        Returns:
            Tuple of (unique_filename, file_path)
        """
        # Validate before saving
        self._validate_file(file)

        # Generate UUID filename to prevent:
        # 1. Path traversal attacks (../../etc/passwd)
        # 2. Filename collisions
        # 3. Information disclosure (don't expose internal paths)
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}.pdf"
        file_path = self.upload_dir / safe_filename

        # Read and validate file size
        content = await file.read()
        file_size = len(content)

        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File too large: {file_size / 1024 / 1024:.1f}MB. "
                    f"Maximum allowed: {settings.max_file_size_mb}MB"
                )
            )

        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Write to disk asynchronously
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        logger.info(
            f"File saved: original='{file.filename}', "
            f"saved_as='{safe_filename}', "
            f"size={file_size / 1024:.1f}KB"
        )

        return safe_filename, file_path

    def delete_file(self, filename: str) -> bool:
        """
        Delete a saved upload file.
        
        DESIGN DECISION: We delete files after analysis to avoid
        storing sensitive legal documents longer than needed (data minimization).
        """
        file_path = self.upload_dir / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"File deleted: {filename}")
            return True
        return False

    def get_file_path(self, filename: str) -> Path:
        """Get full path for a saved file."""
        file_path = self.upload_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        return file_path

    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Remove uploads older than max_age_hours.
        
        In production, this would be called by a scheduled job (Celery beat, cron).
        Interview talking point: "I implemented automatic file cleanup 
        for GDPR compliance and storage management."
        """
        import time
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        for file_path in self.upload_dir.glob("*.pdf"):
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                file_path.unlink()
                deleted_count += 1
                logger.info(f"Cleaned up old file: {file_path.name}")

        if deleted_count > 0:
            logger.info(f"Cleanup complete: {deleted_count} files removed")

        return deleted_count


# Singleton instance
file_handler = FileHandler()
