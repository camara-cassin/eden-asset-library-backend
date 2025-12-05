"""
Merge logic for AI extraction results.

This module implements the merge strategy for AI-extracted data:
- Only fill empty fields (don't overwrite user-entered data)
- Append to arrays rather than replacing them
- Track all updated fields for the ai_assistance.fields_prefilled list
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def is_empty_value(value: Any) -> bool:
    """
    Check if a value is considered "empty" and should be filled by AI.
    
    Empty values include:
    - None
    - Empty string ""
    - Empty list []
    - Empty dict {}
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    return False


def get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Get a value from a nested dict using dot notation path.
    
    Args:
        data: The data dict to search
        path: Dot-separated path like "basic_information.long_description"
        
    Returns:
        The value at the path, or None if not found
    """
    parts = path.split(".")
    current = data
    
    for part in parts:
        if not isinstance(current, dict):
            return None
        if part not in current:
            return None
        current = current[part]
    
    return current


def set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set a value in a nested dict using dot notation path.
    Creates intermediate dicts as needed.
    
    Args:
        data: The data dict to modify
        path: Dot-separated path like "basic_information.long_description"
        value: The value to set
    """
    parts = path.split(".")
    current = data
    
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    
    current[parts[-1]] = value


def merge_extracted_data(
    current_data: Dict[str, Any],
    extracted_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Merge AI-extracted data into current asset data.
    
    Rules:
    - Only fill empty fields (don't overwrite user-entered data)
    - Append to arrays rather than replacing them
    - Track all updated fields
    
    Args:
        current_data: The current asset data dict
        extracted_data: The AI-extracted data dict
        
    Returns:
        Tuple of (merged data dict, list of field paths that were updated)
    """
    merged = current_data.copy()
    fields_updated = []
    
    # Process long_description (only if empty)
    if "long_description" in extracted_data:
        current_long_desc = get_nested_value(merged, "basic_information.long_description")
        if is_empty_value(current_long_desc):
            set_nested_value(merged, "basic_information.long_description", extracted_data["long_description"])
            fields_updated.append("basic_information.long_description")
            logger.info("Filled long_description from AI extraction")
    
    # Process technical_specs (append to existing array)
    if "technical_specs" in extracted_data and isinstance(extracted_data["technical_specs"], list):
        current_specs = get_nested_value(merged, "technical_specs") or []
        if not isinstance(current_specs, list):
            current_specs = []
        
        # Get existing spec names to avoid duplicates
        existing_names = {spec.get("name", "").lower() for spec in current_specs if isinstance(spec, dict)}
        
        new_specs = []
        for spec in extracted_data["technical_specs"]:
            if isinstance(spec, dict):
                spec_name = spec.get("name", "").lower()
                if spec_name and spec_name not in existing_names:
                    new_specs.append(spec)
                    existing_names.add(spec_name)
        
        if new_specs:
            merged["technical_specs"] = current_specs + new_specs
            fields_updated.append("technical_specs")
            logger.info(f"Appended {len(new_specs)} new technical specs from AI extraction")
    
    # Process physical_configuration
    if "physical_configuration" in extracted_data:
        pc_extracted = extracted_data["physical_configuration"]
        if isinstance(pc_extracted, dict):
            if "physical_configuration" not in merged:
                merged["physical_configuration"] = {}
            
            pc_current = merged["physical_configuration"]
            
            # Process dimensions
            if "dimensions" in pc_extracted:
                dims_extracted = pc_extracted["dimensions"]
                if isinstance(dims_extracted, dict):
                    if "dimensions" not in pc_current:
                        pc_current["dimensions"] = {}
                    
                    for dim_key in ["length", "width", "height"]:
                        if dim_key in dims_extracted:
                            current_dim = pc_current["dimensions"].get(dim_key)
                            if is_empty_value(current_dim) or (isinstance(current_dim, dict) and is_empty_value(current_dim.get("value"))):
                                pc_current["dimensions"][dim_key] = dims_extracted[dim_key]
                                fields_updated.append(f"physical_configuration.dimensions.{dim_key}")
            
            # Process unit_weight
            if "unit_weight" in pc_extracted:
                current_weight = pc_current.get("unit_weight")
                if is_empty_value(current_weight) or (isinstance(current_weight, dict) and is_empty_value(current_weight.get("value"))):
                    pc_current["unit_weight"] = pc_extracted["unit_weight"]
                    fields_updated.append("physical_configuration.unit_weight")
            
            # Process package_size
            if "package_size" in pc_extracted:
                pkg_extracted = pc_extracted["package_size"]
                if isinstance(pkg_extracted, dict):
                    if "package_size" not in pc_current:
                        pc_current["package_size"] = {}
                    
                    for dim_key in ["length", "width", "height"]:
                        if dim_key in pkg_extracted:
                            current_dim = pc_current["package_size"].get(dim_key)
                            if is_empty_value(current_dim) or (isinstance(current_dim, dict) and is_empty_value(current_dim.get("value"))):
                                pc_current["package_size"][dim_key] = pkg_extracted[dim_key]
                                fields_updated.append(f"physical_configuration.package_size.{dim_key}")
            
            # Process package_weight
            if "package_weight" in pc_extracted:
                current_pkg_weight = pc_current.get("package_weight")
                if is_empty_value(current_pkg_weight) or (isinstance(current_pkg_weight, dict) and is_empty_value(current_pkg_weight.get("value"))):
                    pc_current["package_weight"] = pc_extracted["package_weight"]
                    fields_updated.append("physical_configuration.package_weight")
            
            # Process footprint_area
            if "footprint_area" in pc_extracted:
                current_footprint = pc_current.get("footprint_area")
                if is_empty_value(current_footprint) or (isinstance(current_footprint, dict) and is_empty_value(current_footprint.get("value"))):
                    pc_current["footprint_area"] = pc_extracted["footprint_area"]
                    fields_updated.append("physical_configuration.footprint_area")
            
            # Process modular_interfaces (append to existing array)
            if "modular_interfaces" in pc_extracted and isinstance(pc_extracted["modular_interfaces"], list):
                current_interfaces = pc_current.get("modular_interfaces", [])
                if not isinstance(current_interfaces, list):
                    current_interfaces = []
                
                if pc_extracted["modular_interfaces"]:
                    pc_current["modular_interfaces"] = current_interfaces + pc_extracted["modular_interfaces"]
                    fields_updated.append("physical_configuration.modular_interfaces")
            
            # Process environmental_rating
            if "environmental_rating" in pc_extracted:
                current_rating = pc_current.get("environmental_rating")
                if is_empty_value(current_rating):
                    pc_current["environmental_rating"] = pc_extracted["environmental_rating"]
                    fields_updated.append("physical_configuration.environmental_rating")
    
    # Process operational_specs
    if "operational_specs" in extracted_data:
        ops_extracted = extracted_data["operational_specs"]
        if isinstance(ops_extracted, dict):
            if "operational_specs" not in merged:
                merged["operational_specs"] = {}
            
            ops_current = merged["operational_specs"]
            
            # Process each operational spec field
            ops_fields = [
                "operating_temperature_min",
                "operating_temperature_max",
                "wind_rating",
                "snow_rating",
                "rain_rating",
            ]
            
            for field in ops_fields:
                if field in ops_extracted:
                    current_val = ops_current.get(field)
                    if is_empty_value(current_val):
                        ops_current[field] = ops_extracted[field]
                        fields_updated.append(f"operational_specs.{field}")
    
    return merged, fields_updated


def build_field_updates(
    extracted_data: Dict[str, Any],
    fields_updated: List[str],
    source: str = "openai"
) -> List[Dict[str, Any]]:
    """
    Build the field_updates list for the extraction response.
    
    Args:
        extracted_data: The AI-extracted data dict
        fields_updated: List of field paths that were updated
        source: The source identifier (e.g., "openai")
        
    Returns:
        List of field update dicts with path, value, confidence, source
    """
    field_updates = []
    
    for path in fields_updated:
        # Get the value from extracted data
        value = get_nested_value(extracted_data, path)
        if value is None:
            # Try without the top-level prefix
            parts = path.split(".")
            if len(parts) > 1:
                alt_path = ".".join(parts[1:])
                value = get_nested_value(extracted_data, alt_path)
        
        field_updates.append({
            "path": path,
            "value": value,
            "confidence": 0.8,  # Default confidence for OpenAI extraction
            "source": source
        })
    
    return field_updates
