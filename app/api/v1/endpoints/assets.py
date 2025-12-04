from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.db.database import get_db
from app.schemas.asset import (
    AssetCreate, AssetUpdate, AssetResponse, PaginatedResponse,
    ErrorResponse, ReviewRequest, RejectRequest, FileAttachRequest, AIExtractRequest,
    FileUploadResponse, AIExtractionRequest, AIExtractionResponse, AIFieldUpdate
)
from app.services import asset_service
from app.services.file_storage import save_upload, get_documentation_field, is_array_field
from app.core.security import get_current_user, get_current_user_optional, require_admin
from app.models.user import User, UserRole

router = APIRouter()


def format_asset_response(asset) -> dict:
    response = asset.data.copy()
    response["id"] = str(asset.id)
    return response


def format_asset_list_item(asset) -> dict:
    data = asset.data
    return {
        "id": str(asset.id),
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "status": asset.status,
        "basic_information": data.get("basic_information"),
        "overview": data.get("overview"),
        "eden_impact_summary": data.get("eden_impact_summary"),
        "deployment": data.get("deployment"),
    }


@router.post("", status_code=201)
async def create_asset(
    asset_data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new EdenAsset in draft status.
    Requires authentication. Auto-sets contributor info from current user.
    Minimum required fields: asset_type, basic_information.asset_name, basic_information.category
    """
    input_dict = asset_data.model_dump(exclude_none=True)
    
    # Auto-set contributor info from current user
    if "contributor" not in input_dict:
        input_dict["contributor"] = {}
    input_dict["contributor"]["name"] = current_user.name
    input_dict["contributor"]["email"] = current_user.email
    input_dict["contributor"]["contributor_id"] = str(current_user.id)
    
    basic_info = input_dict.get("basic_information", {})
    if not basic_info.get("asset_name"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "basic_information.asset_name is required",
                    "details": {}
                }
            }
        )
    if not basic_info.get("category"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "basic_information.category is required",
                    "details": {}
                }
            }
        )
    
    asset, errors = await asset_service.create_asset(db, input_dict)
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "Validation failed",
                    "details": {"errors": errors}
                }
            }
        )
    
    return format_asset_response(asset)


@router.get("")
async def list_assets(
    q: Optional[str] = None,
    asset_type: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    status: Optional[str] = None,
    submission_status: Optional[str] = None,
    scaling_potential: Optional[str] = None,
    company_name: Optional[str] = None,
    creator_name: Optional[str] = None,
    climate_zone: Optional[str] = None,
    min_positive_impact: Optional[float] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|updated_at|eden_positive_impact_points)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search and filter assets with pagination.
    Requires authentication. Admin sees all assets, contributors see only their own.
    """
    # Filter by contributor_id for non-admin users
    contributor_id = None if current_user.role == UserRole.admin else str(current_user.id)
    
    assets, total = await asset_service.list_assets(
        db=db,
        q=q,
        asset_type=asset_type,
        category=category,
        subcategory=subcategory,
        status=status,
        submission_status=submission_status,
        scaling_potential=scaling_potential,
        company_name=company_name,
        creator_name=creator_name,
        climate_zone=climate_zone,
        min_positive_impact=min_positive_impact,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        contributor_id=contributor_id,
    )
    
    return {
        "items": [format_asset_list_item(a) for a in assets],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single asset by UUID.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    return format_asset_response(asset)


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: str,
    updates: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update asset with partial deep merge.
    Requires authentication. Admin can edit any asset, contributors can only edit their own.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    # Check authorization: admin can edit any, contributor can only edit their own
    if current_user.role != UserRole.admin:
        if asset.contributor_id != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "forbidden",
                        "message": "You can only edit your own assets",
                        "details": {}
                    }
                }
            )
    
    update_dict = updates.model_dump(exclude_none=True)
    
    # Ignore any contributor updates from client - contributor info is managed by EDEN
    if "contributor" in update_dict:
        del update_dict["contributor"]
    
    updated_asset, errors = await asset_service.update_asset(db, asset, update_dict)
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "Validation failed",
                    "details": {"errors": errors}
                }
            }
        )
    
    return format_asset_response(updated_asset)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete asset by setting status to deprecated.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    await asset_service.soft_delete_asset(db, asset)
    return None


@router.post("/{asset_id}/submit")
async def submit_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit asset for review with strict validation.
    Requires authentication. Contributor can submit their own, admin can submit any.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    # Check authorization: contributor can submit their own, admin can submit any
    if current_user.role != UserRole.admin:
        if asset.contributor_id != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "forbidden",
                        "message": "You can only submit your own assets",
                        "details": {}
                    }
                }
            )
    
    updated_asset, errors = await asset_service.submit_for_review(db, asset)
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "Asset does not meet submission requirements",
                    "details": {"errors": errors}
                }
            }
        )
    
    return format_asset_response(updated_asset)


@router.post("/{asset_id}/approve")
async def approve_asset(
    asset_id: str,
    request: Optional[ReviewRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Approve an asset. Admin only.
    Sets status="approved" and submission_status="approved".
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    reviewer_id = str(current_user.id)
    review_notes = request.review_notes if request else None
    
    updated_asset = await asset_service.approve_asset(db, asset, reviewer_id, review_notes)
    return format_asset_response(updated_asset)


@router.post("/{asset_id}/reject")
async def reject_asset(
    asset_id: str,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Reject an asset. Admin only.
    Sets submission_status="changes_requested". Accepts reject reason.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    reviewer_id = str(current_user.id)
    updated_asset = await asset_service.reject_asset(db, asset, reviewer_id, request.reason)
    return format_asset_response(updated_asset)


@router.post("/{asset_id}/files")
async def attach_file(
    asset_id: str,
    request: FileAttachRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Attach a file URL to the asset's documentation_uploads.
    Requires authentication.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    updated_asset, error = await asset_service.attach_file_url(db, asset, request.target, request.url)
    
    if error:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "invalid_target",
                    "message": error,
                    "details": {}
                }
            }
        )
    
    return format_asset_response(updated_asset)


@router.post("/{asset_id}/ai-extract", response_model=AIExtractionResponse)
async def ai_extract(
    asset_id: str,
    request: Optional[AIExtractRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger AI extraction (stub mode when USE_REAL_AI is false).
    Requires authentication.
    
    Accepts optional website_url for scraping in addition to uploaded documents.
    Returns AIExtractionResponse with field_updates, fields_prefilled, sources_used, and notes_for_reviewer.
    
    The asset's ai_assistance section is also updated with:
    - prefill_status: "complete" or "failed"
    - fields_prefilled: list of JSON paths that were updated
    - sources_used: list of sources that were processed
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    # Check authorization: admin can extract any, contributor can only extract their own
    if current_user.role != UserRole.admin:
        if asset.contributor_id != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "forbidden",
                        "message": "You can only run AI extraction on your own assets",
                        "details": {}
                    }
                }
            )
    
    sources = request.sources if request and request.sources else {}
    website_url = request.website_url if request else None
    use_uploaded_docs = request.use_uploaded_docs if request else True
    
    # Get uploaded file IDs from documentation_uploads if available
    uploaded_file_ids = []
    doc_uploads = asset.data.get("documentation_uploads", {})
    for field_name, field_value in doc_uploads.items():
        if isinstance(field_value, list):
            uploaded_file_ids.extend(field_value)
        elif field_value:
            uploaded_file_ids.append(field_value)
    
    updated_asset, extraction_response = await asset_service.ai_extract(
        db, asset, sources, 
        website_url=website_url, 
        use_uploaded_docs=use_uploaded_docs,
        uploaded_file_ids=uploaded_file_ids
    )
    
    # Convert field_updates to AIFieldUpdate objects
    field_updates = [
        AIFieldUpdate(
            path=update.get("path", ""),
            value=update.get("value"),
            confidence=update.get("confidence", 0.0),
            source=update.get("source", "")
        )
        for update in extraction_response.get("field_updates", [])
    ]
    
    return AIExtractionResponse(
        field_updates=field_updates,
        fields_prefilled=extraction_response.get("fields_prefilled", []),
        sources_used=extraction_response.get("sources_used", []),
        notes_for_reviewer=extraction_response.get("notes_for_reviewer", [])
    )


@router.post("/{asset_id}/uploads")
async def upload_files(
    asset_id: str,
    files: List[UploadFile] = File(...),
    doc_type: str = Form(default="general"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload multiple files to an asset's documentation_uploads.
    Requires authentication.
    
    doc_type options:
    - technical_spec: Technical specification sheets (PDF)
    - cad_files: CAD files (DWG, DXF, STEP, etc.)
    - engineering_drawings: Engineering drawings (PDF, images)
    - manuals: Build manuals and instructions (PDF)
    - images: Product images (JPG, PNG, etc.)
    - general: Other documents
    
    Note: On Fly.io, local storage is ephemeral. For production, use S3/R2.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    # Check authorization: admin can upload to any, contributor can only upload to their own
    if current_user.role != UserRole.admin:
        if asset.contributor_id != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "forbidden",
                        "message": "You can only upload files to your own assets",
                        "details": {}
                    }
                }
            )
    
    uploaded_files: List[FileUploadResponse] = []
    errors: List[str] = []
    
    for file in files:
        file_url, error = await save_upload(asset_id, file, doc_type)
        
        if error:
            errors.append(f"{file.filename}: {error}")
        elif file_url:
            field = get_documentation_field(doc_type)
            uploaded_files.append(FileUploadResponse(
                url=file_url,
                filename=file.filename or "unknown",
                doc_type=doc_type,
                field=field
            ))
    
    if not uploaded_files and errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "upload_failed",
                    "message": "All file uploads failed",
                    "details": {"errors": errors}
                }
            }
        )
    
    # Update asset's documentation_uploads with the new file URLs
    data = asset.data.copy()
    if "documentation_uploads" not in data:
        data["documentation_uploads"] = {}
    
    for uploaded in uploaded_files:
        field = uploaded.field
        if is_array_field(field):
            if field not in data["documentation_uploads"]:
                data["documentation_uploads"][field] = []
            data["documentation_uploads"][field].append(uploaded.url)
        else:
            data["documentation_uploads"][field] = uploaded.url
    
    # Save the updated asset
    asset.data = data
    await db.commit()
    await db.refresh(asset)
    
    return {
        "uploaded": [f.model_dump() for f in uploaded_files],
        "errors": errors if errors else None,
        "asset": format_asset_response(asset)
    }
