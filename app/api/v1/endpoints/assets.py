from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.db.database import get_db
from app.schemas.asset import (
    AssetCreate, AssetUpdate, AssetResponse, PaginatedResponse,
    ErrorResponse, ReviewRequest, RejectRequest, FileAttachRequest, AIExtractRequest
)
from app.services import asset_service

router = APIRouter()


def format_asset_response(asset) -> dict:
    return asset.data


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
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new EdenAsset in draft status.
    Minimum required fields: asset_type, basic_information.asset_name, basic_information.category
    """
    input_dict = asset_data.model_dump(exclude_none=True)
    
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
    db: AsyncSession = Depends(get_db)
):
    """
    Search and filter assets with pagination.
    """
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
    db: AsyncSession = Depends(get_db)
):
    """
    Update asset with partial deep merge.
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
    
    update_dict = updates.model_dump(exclude_none=True)
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
    db: AsyncSession = Depends(get_db)
):
    """
    Submit asset for review with strict validation.
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
    db: AsyncSession = Depends(get_db)
):
    """
    Approve an asset.
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
    
    reviewer_id = request.reviewer_id if request else None
    review_notes = request.review_notes if request else None
    
    updated_asset = await asset_service.approve_asset(db, asset, reviewer_id, review_notes)
    return format_asset_response(updated_asset)


@router.post("/{asset_id}/reject")
async def reject_asset(
    asset_id: str,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reject an asset.
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
    
    updated_asset = await asset_service.reject_asset(db, asset, request.reviewer_id, request.reason)
    return format_asset_response(updated_asset)


@router.post("/{asset_id}/files")
async def attach_file(
    asset_id: str,
    request: FileAttachRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Attach a file URL to the asset's documentation_uploads.
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


@router.post("/{asset_id}/ai-extract")
async def ai_extract(
    asset_id: str,
    request: Optional[AIExtractRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger AI extraction (stub mode when AI_ENABLED is false).
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
    
    sources = request.sources if request and request.sources else {}
    updated_asset = await asset_service.ai_extract(db, asset, sources)
    
    return format_asset_response(updated_asset)
