import json
import os
from typing import Tuple, List, Optional
from jsonschema import Draft7Validator, ValidationError

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "eden_asset.schema.json")

_schema = None


def get_schema() -> dict:
    global _schema
    if _schema is None:
        with open(SCHEMA_PATH, "r") as f:
            _schema = json.load(f)
    return _schema


def validate_relaxed(data: dict) -> Tuple[bool, List[str]]:
    """
    Relaxed validation mode for POST /assets and PATCH /assets/:id.
    Enforces JSON types for present fields but allows missing sections.
    """
    schema = get_schema()
    validator = Draft7Validator(schema)
    errors = []
    
    for error in validator.iter_errors(data):
        if error.validator == "required":
            continue
        errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}" if error.path else error.message)
    
    return len(errors) == 0, errors


def validate_mvp_common(data: dict) -> List[str]:
    """
    MVP validation: Common required fields for all asset types.
    
    Required for all assets:
    - asset_type
    - basic_information.asset_name
    - basic_information.category
    - basic_information.subcategory
    - basic_information.short_summary
    """
    errors = []
    
    if not data.get("asset_type"):
        errors.append("asset_type: required")
    
    basic_info = data.get("basic_information", {})
    
    if not basic_info.get("asset_name"):
        errors.append("basic_information.asset_name: required")
    
    if not basic_info.get("category"):
        errors.append("basic_information.category: required")
    
    if not basic_info.get("subcategory"):
        errors.append("basic_information.subcategory: required")
    
    if not basic_info.get("short_summary"):
        errors.append("basic_information.short_summary: required")
    
    return errors


def validate_mvp_physical_hybrid(data: dict) -> List[str]:
    """
    MVP validation: Required fields for physical and hybrid assets.
    
    Required:
    - basic_information.company_name
    - basic_information.company_email
    - basic_information.company_website_url
    - basic_information.original_source_url (Product URL)
    """
    errors = []
    basic_info = data.get("basic_information", {})
    
    if not basic_info.get("company_name"):
        errors.append("basic_information.company_name: required for physical/hybrid assets")
    
    if not basic_info.get("company_email"):
        errors.append("basic_information.company_email: required for physical/hybrid assets")
    
    if not basic_info.get("company_website_url"):
        errors.append("basic_information.company_website_url: required for physical/hybrid assets")
    
    if not basic_info.get("original_source_url"):
        errors.append("basic_information.original_source_url: required for physical/hybrid assets (Product URL)")
    
    return errors


def validate_mvp_plan(data: dict) -> List[str]:
    """
    MVP validation: Required fields for plan assets.
    
    Required:
    - basic_information.creator_name
    - basic_information.creator_email
    
    Optional but encouraged:
    - basic_information.original_source_url
    """
    errors = []
    basic_info = data.get("basic_information", {})
    
    if not basic_info.get("creator_name"):
        errors.append("basic_information.creator_name: required for plan assets")
    
    if not basic_info.get("creator_email"):
        errors.append("basic_information.creator_email: required for plan assets")
    
    return errors


def validate_mvp_economics(data: dict) -> List[str]:
    """
    MVP validation: Required economics fields for all asset types.
    
    Required:
    - economics.retail_price
    - economics.availability_type
    - economics.generates_revenue
    
    Optional:
    - economics.wholesale_price
    - economics.minimum_wholesale_quantity
    - economics.estimated_annual_net_profit_usd
    """
    errors = []
    economics = data.get("economics", {})
    
    if economics.get("retail_price") is None:
        errors.append("economics.retail_price: required")
    
    if not economics.get("availability_type"):
        errors.append("economics.availability_type: required")
    
    if not economics.get("generates_revenue"):
        errors.append("economics.generates_revenue: required")
    
    return errors


def validate_mvp_images(data: dict) -> List[str]:
    """
    MVP validation: Image requirements.
    
    Required:
    - At least one overview.images[] item with a valid url
    - Exactly one image should be marked is_primary = true
    """
    errors = []
    overview = data.get("overview", {})
    images = overview.get("images", [])
    
    if not images or len(images) == 0:
        errors.append("overview.images: at least one image with a valid url is required")
        return errors
    
    valid_images = [img for img in images if img.get("url")]
    if len(valid_images) == 0:
        errors.append("overview.images: at least one image with a valid url is required")
        return errors
    
    primary_images = [img for img in images if img.get("is_primary") is True]
    if len(primary_images) == 0:
        errors.append("overview.images: exactly one image must be marked as is_primary = true")
    elif len(primary_images) > 1:
        errors.append("overview.images: only one image can be marked as is_primary = true")
    
    return errors


def validate_mvp_documentation(data: dict) -> List[str]:
    """
    MVP validation: Documentation requirements.
    
    Required: at least one documentation URL from:
    - documentation_uploads.technical_spec_sheet_url OR
    - documentation_uploads.product_datasheet_url OR
    - any entry in documentation_uploads.additional_docs_urls[] OR
    - basic_information.original_source_url
    """
    errors = []
    
    basic_info = data.get("basic_information", {})
    doc_uploads = data.get("documentation_uploads", {})
    
    has_doc = False
    
    if basic_info.get("original_source_url"):
        has_doc = True
    
    if doc_uploads.get("technical_spec_sheet_url"):
        has_doc = True
    
    if doc_uploads.get("product_datasheet_url"):
        has_doc = True
    
    additional_docs = doc_uploads.get("additional_docs_urls", [])
    if additional_docs and len(additional_docs) > 0:
        has_doc = True
    
    if not has_doc:
        errors.append("documentation: at least one documentation URL is required (technical_spec_sheet_url, product_datasheet_url, additional_docs_urls, or original_source_url)")
    
    return errors


def validate_strict(data: dict) -> Tuple[bool, List[str]]:
    """
    MVP strict validation mode for POST /assets/:id/submit.
    
    Validates:
    1. JSON schema types (relaxed)
    2. Common required fields (all asset types)
    3. Asset-type-specific supplier/creator fields
    4. Economics required fields
    5. Image requirements
    6. Documentation requirements
    
    Does NOT require (hidden in MVP UI):
    - physical_configuration.unit_variants
    - functional_io.inputs/outputs
    - plan_configuration.required_skill_level
    - plan_configuration.estimated_build_time_hours
    """
    is_valid, errors = validate_relaxed(data)
    if not is_valid:
        return False, errors
    
    errors = []
    
    common_errors = validate_mvp_common(data)
    errors.extend(common_errors)
    
    asset_type = data.get("asset_type")
    
    if asset_type == "physical":
        type_errors = validate_mvp_physical_hybrid(data)
        errors.extend(type_errors)
    elif asset_type == "plan":
        type_errors = validate_mvp_plan(data)
        errors.extend(type_errors)
    elif asset_type == "hybrid":
        type_errors = validate_mvp_physical_hybrid(data)
        errors.extend(type_errors)
    
    economics_errors = validate_mvp_economics(data)
    errors.extend(economics_errors)
    
    image_errors = validate_mvp_images(data)
    errors.extend(image_errors)
    
    doc_errors = validate_mvp_documentation(data)
    errors.extend(doc_errors)
    
    return len(errors) == 0, errors


def validate_file_target(target: str) -> bool:
    """
    Validate that the target is a valid array field under documentation_uploads.
    """
    valid_targets = [
        "cad_file_urls",
        "bim_file_urls",
        "engineering_drawings_urls",
        "safety_data_sheets_urls",
        "certifications_docs_urls",
        "patent_docs_urls",
        "marketing_pdfs_urls",
        "instructional_video_urls",
        "additional_docs_urls",
    ]
    return target in valid_targets
