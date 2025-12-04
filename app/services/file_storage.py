"""
File storage service for handling document uploads.

This implementation uses local disk storage. For production on Fly.io,
this should be replaced with S3/R2 storage as local files are ephemeral.
"""
import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from app.core.config import settings


# Allowed file extensions by category
ALLOWED_EXTENSIONS = {
    "technical_spec": [".pdf", ".doc", ".docx"],
    "cad_files": [".dwg", ".dxf", ".step", ".stp", ".iges", ".igs", ".stl", ".obj"],
    "engineering_drawings": [".pdf", ".dwg", ".dxf", ".png", ".jpg", ".jpeg"],
    "manuals": [".pdf", ".doc", ".docx"],
    "images": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
    "general": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".zip"],
}

# Map document types to documentation_uploads fields
DOC_TYPE_TO_FIELD = {
    "technical_spec": "technical_spec_sheet_url",
    "product_datasheet": "product_datasheet_url",
    "cad_files": "cad_file_urls",
    "bim_files": "bim_file_urls",
    "engineering_drawings": "engineering_drawings_urls",
    "build_manual": "build_manual_url",
    "instructions": "step_by_step_instructions_url",
    "bom": "bom_url",
    "safety_sheets": "safety_data_sheets_urls",
    "certifications": "certifications_docs_urls",
    "marketing": "marketing_pdfs_urls",
    "videos": "instructional_video_urls",
    "additional": "additional_docs_urls",
}


def get_upload_dir() -> Path:
    """Get the upload directory path, creating it if needed."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_asset_upload_dir(asset_id: str) -> Path:
    """Get the upload directory for a specific asset."""
    asset_dir = get_upload_dir() / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    return asset_dir


def get_file_extension(filename: str) -> str:
    """Get the lowercase file extension."""
    return Path(filename).suffix.lower()


def is_allowed_extension(filename: str, doc_type: str = "general") -> bool:
    """Check if the file extension is allowed for the document type."""
    ext = get_file_extension(filename)
    allowed = ALLOWED_EXTENSIONS.get(doc_type, ALLOWED_EXTENSIONS["general"])
    return ext in allowed


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving the extension."""
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    # Sanitize original filename
    safe_name = "".join(c for c in Path(original_filename).stem if c.isalnum() or c in "-_")[:50]
    return f"{safe_name}_{unique_id}{ext}"


async def save_upload(
    asset_id: str,
    upload: UploadFile,
    doc_type: str = "general"
) -> tuple[Optional[str], Optional[str]]:
    """
    Save an uploaded file to local storage.
    
    Args:
        asset_id: The asset ID to associate the file with
        upload: The FastAPI UploadFile object
        doc_type: The document type category
        
    Returns:
        Tuple of (file_url, error_message). One will be None.
    """
    if not upload.filename:
        return None, "No filename provided"
    
    # Check file size
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # Check extension
    if not is_allowed_extension(upload.filename, doc_type):
        allowed = ALLOWED_EXTENSIONS.get(doc_type, ALLOWED_EXTENSIONS["general"])
        return None, f"File type not allowed. Allowed types: {', '.join(allowed)}"
    
    # Generate unique filename
    unique_filename = generate_unique_filename(upload.filename)
    
    # Get asset directory
    asset_dir = get_asset_upload_dir(asset_id)
    file_path = asset_dir / unique_filename
    
    # Save file
    try:
        content = await upload.read()
        if len(content) > max_size:
            return None, f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB"
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        # Return the URL path (relative to static mount)
        file_url = f"/files/{asset_id}/{unique_filename}"
        return file_url, None
        
    except Exception as e:
        return None, f"Failed to save file: {str(e)}"


async def delete_file(asset_id: str, filename: str) -> bool:
    """Delete a file from storage."""
    try:
        file_path = get_asset_upload_dir(asset_id) / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception:
        return False


def get_documentation_field(doc_type: str) -> Optional[str]:
    """Get the documentation_uploads field name for a document type."""
    return DOC_TYPE_TO_FIELD.get(doc_type)


def is_array_field(field_name: str) -> bool:
    """Check if a documentation_uploads field is an array type."""
    array_fields = [
        "cad_file_urls", "bim_file_urls", "engineering_drawings_urls",
        "safety_data_sheets_urls", "certifications_docs_urls", "patent_docs_urls",
        "marketing_pdfs_urls", "instructional_video_urls", "additional_docs_urls"
    ]
    return field_name in array_fields
