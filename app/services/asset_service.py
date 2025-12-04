import uuid
from datetime import datetime
from typing import Optional, List, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.models.asset import EdenAsset
from app.services.validation import validate_relaxed, validate_strict, validate_file_target
from app.core.config import settings


def generate_asset_id() -> str:
    return f"ASSET_{uuid.uuid4().hex[:12].upper()}"


def deep_merge(base: dict, updates: dict) -> dict:
    """
    Deep merge updates into base dictionary.
    Arrays are replaced, not merged.
    """
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def increment_version(version: str) -> str:
    """
    Increment version string, e.g., v1 -> v2, v10 -> v11
    """
    if version and version.startswith("v"):
        try:
            num = int(version[1:])
            return f"v{num + 1}"
        except ValueError:
            pass
    return "v2"


def extract_scalar_columns(data: dict) -> dict:
    """
    Extract scalar columns from the full EdenAsset data for indexed columns.
    """
    basic_info = data.get("basic_information", {}) or {}
    system_meta = data.get("system_meta", {}) or {}
    contributor = data.get("contributor", {}) or {}
    
    return {
        "asset_type": data.get("asset_type"),
        "status": system_meta.get("status", "draft"),
        "submission_status": contributor.get("submission_status"),
        "category": basic_info.get("category"),
        "scaling_potential": basic_info.get("scaling_potential"),
        "company_name": basic_info.get("company_name"),
        "creator_name": basic_info.get("creator_name"),
        "contributor_id": contributor.get("contributor_id"),
    }


def build_initial_asset_data(input_data: dict) -> dict:
    """
    Build a full EdenAsset structure from partial input, filling defaults.
    """
    now = datetime.utcnow().isoformat()
    
    asset_id = input_data.get("asset_id") or generate_asset_id()
    
    data = {
        "asset_id": asset_id,
        "asset_type": input_data.get("asset_type"),
        "system_meta": {
            "status": "draft",
            "version": "v1",
            "created_at": now,
            "updated_at": now,
            **(input_data.get("system_meta") or {})
        },
        "ai_assistance": {
            "prefill_status": "not_run",
            "prefill_message": "Gathering available information and pre-filling fields, please review for accuracy",
            "sources_used": [],
            "fields_prefilled": [],
            **(input_data.get("ai_assistance") or {})
        },
        "basic_information": input_data.get("basic_information") or {},
        "contributor": {
            "submission_status": "draft",
            **(input_data.get("contributor") or {})
        },
        "overview": input_data.get("overview") or {},
        "documentation_uploads": input_data.get("documentation_uploads") or {},
        "physical_configuration": input_data.get("physical_configuration") or {},
        "plan_configuration": input_data.get("plan_configuration") or {},
        "functional_io": input_data.get("functional_io") or {},
        "economics": input_data.get("economics") or {},
        "deployment": input_data.get("deployment") or {},
        "eden_impact_summary": input_data.get("eden_impact_summary") or {},
    }
    
    return data


async def create_asset(db: AsyncSession, input_data: dict) -> Tuple[Optional[EdenAsset], List[str]]:
    """
    Create a new asset in draft status.
    """
    data = build_initial_asset_data(input_data)
    
    is_valid, errors = validate_relaxed(data)
    if not is_valid:
        return None, errors
    
    scalar_cols = extract_scalar_columns(data)
    
    asset = EdenAsset(
        asset_id=data["asset_id"],
        data=data,
        **scalar_cols
    )
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return asset, []


async def get_asset_by_id(db: AsyncSession, asset_uuid: str) -> Optional[EdenAsset]:
    """
    Get asset by UUID.
    """
    try:
        asset_uuid_obj = uuid.UUID(asset_uuid)
    except ValueError:
        return None
    
    result = await db.execute(select(EdenAsset).where(EdenAsset.id == asset_uuid_obj))
    return result.scalar_one_or_none()


async def get_asset_by_asset_id(db: AsyncSession, asset_id: str) -> Optional[EdenAsset]:
    """
    Get asset by asset_id string.
    """
    result = await db.execute(select(EdenAsset).where(EdenAsset.asset_id == asset_id))
    return result.scalar_one_or_none()


async def update_asset(db: AsyncSession, asset: EdenAsset, updates: dict) -> Tuple[Optional[EdenAsset], List[str]]:
    """
    Update asset with partial deep merge.
    """
    existing_data = asset.data.copy()
    merged_data = deep_merge(existing_data, updates)
    
    now = datetime.utcnow().isoformat()
    if "system_meta" not in merged_data:
        merged_data["system_meta"] = {}
    
    old_version = merged_data["system_meta"].get("version", "v1")
    merged_data["system_meta"]["version"] = increment_version(old_version)
    merged_data["system_meta"]["updated_at"] = now
    
    is_valid, errors = validate_relaxed(merged_data)
    if not is_valid:
        return None, errors
    
    scalar_cols = extract_scalar_columns(merged_data)
    
    asset.data = merged_data
    flag_modified(asset, "data")
    asset.asset_type = scalar_cols["asset_type"]
    asset.status = scalar_cols["status"]
    asset.submission_status = scalar_cols["submission_status"]
    asset.category = scalar_cols["category"]
    asset.scaling_potential = scalar_cols["scaling_potential"]
    asset.company_name = scalar_cols["company_name"]
    asset.creator_name = scalar_cols["creator_name"]
    asset.contributor_id = scalar_cols["contributor_id"]
    asset.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(asset)
    
    return asset, []


async def soft_delete_asset(db: AsyncSession, asset: EdenAsset) -> EdenAsset:
    """
    Soft delete asset by setting status to deprecated.
    """
    data = asset.data.copy()
    if "system_meta" not in data:
        data["system_meta"] = {}
    data["system_meta"]["status"] = "deprecated"
    data["system_meta"]["updated_at"] = datetime.utcnow().isoformat()
    
    asset.data = data
    flag_modified(asset, "data")
    asset.status = "deprecated"
    asset.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(asset)
    
    return asset


async def submit_for_review(db: AsyncSession, asset: EdenAsset) -> Tuple[Optional[EdenAsset], List[str]]:
    """
    Submit asset for review with strict validation.
    """
    is_valid, errors = validate_strict(asset.data)
    if not is_valid:
        return None, errors
    
    data = asset.data.copy()
    now = datetime.utcnow().isoformat()
    
    if "contributor" not in data:
        data["contributor"] = {}
    data["contributor"]["submission_status"] = "pending_review"
    
    if "system_meta" not in data:
        data["system_meta"] = {}
    data["system_meta"]["status"] = "under_review"
    data["system_meta"]["updated_at"] = now
    
    asset.data = data
    flag_modified(asset, "data")
    asset.status = "under_review"
    asset.submission_status = "pending_review"
    asset.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(asset)
    
    return asset, []


async def approve_asset(db: AsyncSession, asset: EdenAsset, reviewer_id: Optional[str] = None, review_notes: Optional[str] = None) -> EdenAsset:
    """
    Approve an asset.
    """
    data = asset.data.copy()
    now = datetime.utcnow().isoformat()
    
    if "system_meta" not in data:
        data["system_meta"] = {}
    data["system_meta"]["status"] = "approved"
    data["system_meta"]["updated_at"] = now
    if reviewer_id:
        data["system_meta"]["updated_by"] = reviewer_id
    if review_notes:
        existing_notes = data["system_meta"].get("internal_reviewer_notes", "") or ""
        data["system_meta"]["internal_reviewer_notes"] = f"{existing_notes}\n[{now}] {review_notes}".strip()
    
    if "contributor" not in data:
        data["contributor"] = {}
    data["contributor"]["submission_status"] = "approved"
    
    asset.data = data
    flag_modified(asset, "data")
    asset.status = "approved"
    asset.submission_status = "approved"
    asset.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(asset)
    
    return asset


async def reject_asset(db: AsyncSession, asset: EdenAsset, reviewer_id: Optional[str] = None, reason: str = "") -> EdenAsset:
    """
    Reject an asset.
    """
    data = asset.data.copy()
    now = datetime.utcnow().isoformat()
    
    if "system_meta" not in data:
        data["system_meta"] = {}
    data["system_meta"]["status"] = "draft"
    data["system_meta"]["updated_at"] = now
    if reviewer_id:
        data["system_meta"]["updated_by"] = reviewer_id
    
    existing_notes = data["system_meta"].get("internal_reviewer_notes", "") or ""
    data["system_meta"]["internal_reviewer_notes"] = f"{existing_notes}\n[{now}] REJECTED: {reason}".strip()
    
    if "contributor" not in data:
        data["contributor"] = {}
    data["contributor"]["submission_status"] = "changes_requested"
    
    asset.data = data
    flag_modified(asset, "data")
    asset.status = "draft"
    asset.submission_status = "changes_requested"
    asset.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(asset)
    
    return asset


async def attach_file_url(db: AsyncSession, asset: EdenAsset, target: str, url: str) -> Tuple[Optional[EdenAsset], Optional[str]]:
    """
    Attach a file URL to the asset's documentation_uploads.
    """
    if not validate_file_target(target):
        return None, f"Invalid target: {target}"
    
    data = asset.data.copy()
    if "documentation_uploads" not in data:
        data["documentation_uploads"] = {}
    
    if target not in data["documentation_uploads"]:
        data["documentation_uploads"][target] = []
    
    data["documentation_uploads"][target].append(url)
    
    now = datetime.utcnow().isoformat()
    if "system_meta" not in data:
        data["system_meta"] = {}
    data["system_meta"]["updated_at"] = now
    
    asset.data = data
    flag_modified(asset, "data")
    asset.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(asset)
    
    return asset, None


def _collect_source_urls(data: dict, sources: dict) -> List[str]:
    """Collect all source URLs from documentation_uploads and extra sources."""
    urls = []
    
    # Collect from documentation_uploads if use_uploaded_docs is true
    if sources.get("use_uploaded_docs", False):
        doc_uploads = data.get("documentation_uploads", {})
        url_fields = [
            "cad_file_urls", "bim_file_urls", "engineering_drawings_urls",
            "safety_data_sheets_urls", "certifications_docs_urls", "patent_docs_urls",
            "marketing_pdfs_urls", "instructional_video_urls", "additional_docs_urls"
        ]
        for field in url_fields:
            field_urls = doc_uploads.get(field, [])
            if isinstance(field_urls, list):
                urls.extend(field_urls)
        
        # Also include single URL fields
        single_url_fields = [
            "technical_spec_sheet_url", "product_datasheet_url", "build_manual_url",
            "step_by_step_instructions_url", "bom_url", "tools_required_doc_url",
            "skills_required_doc_url"
        ]
        for field in single_url_fields:
            url = doc_uploads.get(field)
            if url:
                urls.append(url)
    
    # Add extra doc URLs
    extra_doc_urls = sources.get("extra_doc_urls", [])
    if isinstance(extra_doc_urls, list):
        urls.extend(extra_doc_urls)
    
    # Add extra web URLs
    extra_web_urls = sources.get("extra_web_urls", [])
    if isinstance(extra_web_urls, list):
        urls.extend(extra_web_urls)
    
    return urls


def _apply_field_updates(data: dict, field_updates: dict) -> dict:
    """Apply field updates by JSON path to the data dict."""
    for path, value in field_updates.items():
        parts = path.split(".")
        current = data
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return data


async def ai_extract(db: AsyncSession, asset: EdenAsset, sources: dict) -> EdenAsset:
    """
    AI extraction. When AI_ENABLED is false, marks as complete with stub entry.
    When AI_ENABLED is true, calls the AI microservice to extract data.
    """
    import httpx
    
    data = asset.data.copy()
    now = datetime.utcnow().isoformat()
    
    if "ai_assistance" not in data:
        data["ai_assistance"] = {}
    
    data["ai_assistance"]["prefill_status"] = "running"
    data["ai_assistance"]["last_run_at"] = now
    
    if not settings.AI_ENABLED:
        # Stub mode - just mark as complete
        data["ai_assistance"]["prefill_status"] = "complete"
        if "sources_used" not in data["ai_assistance"]:
            data["ai_assistance"]["sources_used"] = []
        data["ai_assistance"]["sources_used"].append({
            "source_type": "other",
            "source_ref": "ai_extract_stub",
            "notes": "AI extraction not yet implemented"
        })
    else:
        # Real AI mode - call the AI microservice
        try:
            source_urls = _collect_source_urls(data, sources)
            
            if not source_urls:
                data["ai_assistance"]["prefill_status"] = "failed"
                data["ai_assistance"]["prefill_message"] = "No source URLs provided for extraction"
            else:
                # Call AI service
                ai_payload = {
                    "asset_id": asset.asset_id,
                    "sources": source_urls,
                    "current_asset": data
                }
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{settings.AI_SERVICE_URL}/eden/assets/extract",
                        json=ai_payload
                    )
                    response.raise_for_status()
                    ai_response = response.json()
                
                # Apply field updates
                field_updates = ai_response.get("field_updates", {})
                if field_updates:
                    data = _apply_field_updates(data, field_updates)
                
                # Update ai_assistance with results
                fields_prefilled = ai_response.get("fields_prefilled", [])
                if "fields_prefilled" not in data["ai_assistance"]:
                    data["ai_assistance"]["fields_prefilled"] = []
                data["ai_assistance"]["fields_prefilled"].extend(fields_prefilled)
                
                sources_used = ai_response.get("sources_used", [])
                if "sources_used" not in data["ai_assistance"]:
                    data["ai_assistance"]["sources_used"] = []
                data["ai_assistance"]["sources_used"].extend(sources_used)
                
                data["ai_assistance"]["prefill_status"] = "complete"
                data["ai_assistance"]["prefill_message"] = "AI extraction completed successfully"
                
        except httpx.HTTPStatusError as e:
            data["ai_assistance"]["prefill_status"] = "failed"
            data["ai_assistance"]["prefill_message"] = f"AI service returned error: {e.response.status_code}"
        except httpx.RequestError as e:
            data["ai_assistance"]["prefill_status"] = "failed"
            data["ai_assistance"]["prefill_message"] = f"Failed to connect to AI service: {str(e)}"
        except Exception as e:
            data["ai_assistance"]["prefill_status"] = "failed"
            data["ai_assistance"]["prefill_message"] = f"AI extraction failed: {str(e)}"
    
    if "system_meta" not in data:
        data["system_meta"] = {}
    data["system_meta"]["updated_at"] = now
    
    asset.data = data
    flag_modified(asset, "data")
    asset.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(asset)
    
    return asset


async def list_assets(
    db: AsyncSession,
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
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    approved_only: bool = False,
) -> Tuple[List[EdenAsset], int]:
    """
    List and filter assets with pagination.
    """
    query = select(EdenAsset)
    count_query = select(func.count(EdenAsset.id))
    
    conditions = []
    
    if approved_only:
        conditions.append(EdenAsset.status == "approved")
    
    if asset_type:
        conditions.append(EdenAsset.asset_type == asset_type)
    
    if category:
        conditions.append(EdenAsset.category == category)
    
    if status and not approved_only:
        conditions.append(EdenAsset.status == status)
    
    if submission_status:
        conditions.append(EdenAsset.submission_status == submission_status)
    
    if scaling_potential:
        conditions.append(EdenAsset.scaling_potential == scaling_potential)
    
    if company_name:
        conditions.append(EdenAsset.company_name.ilike(f"%{company_name}%"))
    
    if creator_name:
        conditions.append(EdenAsset.creator_name.ilike(f"%{creator_name}%"))
    
    if subcategory:
        conditions.append(EdenAsset.data["basic_information"]["subcategory"].astext == subcategory)
    
    if climate_zone:
        conditions.append(EdenAsset.data["deployment"]["climate_zones"].contains([climate_zone]))
    
    if min_positive_impact is not None:
        conditions.append(
            EdenAsset.data["eden_impact_summary"]["eden_positive_impact_points"].astext.cast(float) >= min_positive_impact
        )
    
    if q:
        search_conditions = [
            EdenAsset.data["basic_information"]["asset_name"].astext.ilike(f"%{q}%"),
            EdenAsset.data["basic_information"]["short_summary"].astext.ilike(f"%{q}%"),
            EdenAsset.data["basic_information"]["long_description"].astext.ilike(f"%{q}%"),
            EdenAsset.asset_type.ilike(f"%{q}%"),
            EdenAsset.category.ilike(f"%{q}%"),
        ]
        conditions.append(or_(*search_conditions))
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    sort_column = getattr(EdenAsset, sort_by, EdenAsset.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    assets = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return list(assets), total


async def list_contributor_assets(
    db: AsyncSession,
    contributor_id: str,
    status: Optional[str] = None,
    submission_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[EdenAsset], int]:
    """
    List assets for a specific contributor.
    """
    query = select(EdenAsset).where(EdenAsset.contributor_id == contributor_id)
    count_query = select(func.count(EdenAsset.id)).where(EdenAsset.contributor_id == contributor_id)
    
    if status:
        query = query.where(EdenAsset.status == status)
        count_query = count_query.where(EdenAsset.status == status)
    
    if submission_status:
        query = query.where(EdenAsset.submission_status == submission_status)
        count_query = count_query.where(EdenAsset.submission_status == submission_status)
    
    query = query.order_by(EdenAsset.created_at.desc())
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    assets = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return list(assets), total
