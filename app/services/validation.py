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


def validate_strict_physical(data: dict) -> Tuple[bool, List[str]]:
    """
    Strict validation for physical assets.
    Requires:
    - physical_configuration.unit_variants must have at least one entry
    - functional_io.inputs must not be empty
    - functional_io.outputs must not be empty
    """
    errors = []
    
    physical_config = data.get("physical_configuration", {})
    unit_variants = physical_config.get("unit_variants", [])
    if not unit_variants or len(unit_variants) == 0:
        errors.append("physical_configuration.unit_variants: must have at least one entry for physical assets")
    
    functional_io = data.get("functional_io", {})
    inputs = functional_io.get("inputs", [])
    outputs = functional_io.get("outputs", [])
    
    if not inputs or len(inputs) == 0:
        errors.append("functional_io.inputs: must not be empty for physical assets")
    
    if not outputs or len(outputs) == 0:
        errors.append("functional_io.outputs: must not be empty for physical assets")
    
    return len(errors) == 0, errors


def validate_strict_plan(data: dict) -> Tuple[bool, List[str]]:
    """
    Strict validation for plan assets.
    Requires:
    - plan_configuration.required_skill_level present
    - plan_configuration.estimated_build_time_hours present
    """
    errors = []
    
    plan_config = data.get("plan_configuration", {})
    
    if not plan_config.get("required_skill_level"):
        errors.append("plan_configuration.required_skill_level: required for plan assets")
    
    if plan_config.get("estimated_build_time_hours") is None:
        errors.append("plan_configuration.estimated_build_time_hours: required for plan assets")
    
    return len(errors) == 0, errors


def validate_strict(data: dict) -> Tuple[bool, List[str]]:
    """
    Strict validation mode for POST /assets/:id/submit.
    Runs relaxed validation first, then applies asset-type-specific rules.
    """
    is_valid, errors = validate_relaxed(data)
    if not is_valid:
        return False, errors
    
    asset_type = data.get("asset_type")
    
    if asset_type == "physical":
        physical_valid, physical_errors = validate_strict_physical(data)
        if not physical_valid:
            errors.extend(physical_errors)
    
    elif asset_type == "plan":
        plan_valid, plan_errors = validate_strict_plan(data)
        if not plan_valid:
            errors.extend(plan_errors)
    
    elif asset_type == "hybrid":
        physical_valid, physical_errors = validate_strict_physical(data)
        plan_valid, plan_errors = validate_strict_plan(data)
        if not physical_valid:
            errors.extend(physical_errors)
        if not plan_valid:
            errors.extend(plan_errors)
    
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
