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


def _merge_scalar_field(current_section: Dict, extracted_section: Dict, field: str, 
                        section_path: str, fields_updated: List[str]) -> None:
    """Helper to merge a scalar field only if current is empty."""
    if field in extracted_section:
        current_val = current_section.get(field)
        if is_empty_value(current_val):
            current_section[field] = extracted_section[field]
            fields_updated.append(f"{section_path}.{field}")


def _merge_array_field(current_section: Dict, extracted_section: Dict, field: str,
                       section_path: str, fields_updated: List[str], 
                       dedupe_key: Optional[str] = None) -> None:
    """Helper to merge an array field by appending new items."""
    if field in extracted_section and isinstance(extracted_section[field], list):
        current_arr = current_section.get(field, [])
        if not isinstance(current_arr, list):
            current_arr = []
        
        new_items = extracted_section[field]
        if new_items:
            if dedupe_key:
                # Dedupe by key (for dicts) or by value (for strings)
                if dedupe_key == "__string__":
                    existing = {str(item).lower() for item in current_arr}
                    new_items = [item for item in new_items if str(item).lower() not in existing]
                else:
                    existing = {item.get(dedupe_key, "").lower() for item in current_arr if isinstance(item, dict)}
                    new_items = [item for item in new_items 
                                if isinstance(item, dict) and item.get(dedupe_key, "").lower() not in existing]
            
            if new_items:
                current_section[field] = current_arr + new_items
                fields_updated.append(f"{section_path}.{field}")


def _merge_value_unit_field(current_section: Dict, extracted_section: Dict, field: str,
                            section_path: str, fields_updated: List[str]) -> None:
    """Helper to merge a value+unit field (like weight, area, dimension)."""
    if field in extracted_section:
        current_val = current_section.get(field)
        if is_empty_value(current_val) or (isinstance(current_val, dict) and is_empty_value(current_val.get("value"))):
            current_section[field] = extracted_section[field]
            fields_updated.append(f"{section_path}.{field}")


def merge_extracted_data(
    current_data: Dict[str, Any],
    extracted_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Merge AI-extracted data into current asset data.
    
    Rules:
    - long_description is ALWAYS overwritten (AI-owned field)
    - Other scalar fields: only fill if empty
    - Arrays: append new items (with deduplication where appropriate)
    - Never touch forbidden sections (contributor, images, bim_models, commissions, etc.)
    - Track all updated fields
    
    Args:
        current_data: The current asset data dict
        extracted_data: The AI-extracted data dict
        
    Returns:
        Tuple of (merged data dict, list of field paths that were updated)
    """
    merged = current_data.copy()
    fields_updated = []
    
    # ========== BASIC_INFORMATION ==========
    if "basic_information" in extracted_data:
        bi_extracted = extracted_data["basic_information"]
        if isinstance(bi_extracted, dict):
            if "basic_information" not in merged:
                merged["basic_information"] = {}
            bi_current = merged["basic_information"]
            
            # long_description: ALWAYS overwrite (AI-owned field)
            if "long_description" in bi_extracted and bi_extracted["long_description"]:
                bi_current["long_description"] = bi_extracted["long_description"]
                fields_updated.append("basic_information.long_description")
                logger.info("Updated long_description from AI extraction (AI-owned field)")
            
            # Scalar fields (only fill if empty)
            for field in ["function_purpose", "scaling_potential", "year_introduced_or_updated", "company_name"]:
                _merge_scalar_field(bi_current, bi_extracted, field, "basic_information", fields_updated)
            
            # Array fields
            _merge_array_field(bi_current, bi_extracted, "certifications", "basic_information", fields_updated, "__string__")
            _merge_array_field(bi_current, bi_extracted, "patent_links", "basic_information", fields_updated, "__string__")
            
            # Categories (only if empty)
            if "categories" in bi_extracted and isinstance(bi_extracted["categories"], list):
                current_cats = bi_current.get("categories", [])
                if is_empty_value(current_cats):
                    bi_current["categories"] = bi_extracted["categories"]
                    fields_updated.append("basic_information.categories")
    
    # Also handle long_description at top level (some models return it there)
    if "long_description" in extracted_data and extracted_data["long_description"]:
        if "basic_information" not in merged:
            merged["basic_information"] = {}
        merged["basic_information"]["long_description"] = extracted_data["long_description"]
        if "basic_information.long_description" not in fields_updated:
            fields_updated.append("basic_information.long_description")
            logger.info("Updated long_description from AI extraction (top-level)")
    
    # ========== OVERVIEW ==========
    if "overview" in extracted_data:
        ov_extracted = extracted_data["overview"]
        if isinstance(ov_extracted, dict):
            if "overview" not in merged:
                merged["overview"] = {}
            ov_current = merged["overview"]
            
            # Scalar fields
            _merge_scalar_field(ov_current, ov_extracted, "asset_type_description", "overview", fields_updated)
            
            # Array fields (dedupe by string value)
            _merge_array_field(ov_current, ov_extracted, "key_features", "overview", fields_updated, "__string__")
            _merge_array_field(ov_current, ov_extracted, "intended_use_cases", "overview", fields_updated, "__string__")
            
            # DO NOT touch images[] - forbidden
    
    # ========== PHYSICAL_CONFIGURATION ==========
    if "physical_configuration" in extracted_data:
        pc_extracted = extracted_data["physical_configuration"]
        if isinstance(pc_extracted, dict):
            if "physical_configuration" not in merged:
                merged["physical_configuration"] = {}
            pc_current = merged["physical_configuration"]
            
            # Dimensions (nested value+unit fields)
            if "dimensions" in pc_extracted and isinstance(pc_extracted["dimensions"], dict):
                if "dimensions" not in pc_current:
                    pc_current["dimensions"] = {}
                dims_current = pc_current["dimensions"]
                dims_extracted = pc_extracted["dimensions"]
                
                for dim_key in ["length", "width", "height"]:
                    _merge_value_unit_field(dims_current, dims_extracted, dim_key, 
                                           "physical_configuration.dimensions", fields_updated)
                
                # Volume (scalar)
                if "volume" in dims_extracted:
                    if is_empty_value(dims_current.get("volume")):
                        dims_current["volume"] = dims_extracted["volume"]
                        fields_updated.append("physical_configuration.dimensions.volume")
            
            # Value+unit fields
            _merge_value_unit_field(pc_current, pc_extracted, "unit_weight", "physical_configuration", fields_updated)
            _merge_value_unit_field(pc_current, pc_extracted, "footprint_area", "physical_configuration", fields_updated)
            _merge_value_unit_field(pc_current, pc_extracted, "package_weight", "physical_configuration", fields_updated)
            
            # Package size (nested)
            if "package_size" in pc_extracted and isinstance(pc_extracted["package_size"], dict):
                if "package_size" not in pc_current:
                    pc_current["package_size"] = {}
                pkg_current = pc_current["package_size"]
                pkg_extracted = pc_extracted["package_size"]
                
                for dim_key in ["length", "width", "height"]:
                    _merge_value_unit_field(pkg_current, pkg_extracted, dim_key,
                                           "physical_configuration.package_size", fields_updated)
            
            # Scalar fields
            for field in ["units_per_package", "environmental_rating"]:
                _merge_scalar_field(pc_current, pc_extracted, field, "physical_configuration", fields_updated)
            
            # Stackability (nested object)
            if "stackability" in pc_extracted and isinstance(pc_extracted["stackability"], dict):
                current_stack = pc_current.get("stackability")
                if is_empty_value(current_stack):
                    pc_current["stackability"] = pc_extracted["stackability"]
                    fields_updated.append("physical_configuration.stackability")
            
            # Array fields
            _merge_array_field(pc_current, pc_extracted, "modular_interfaces", "physical_configuration", fields_updated)
    
    # ========== PLAN_CONFIGURATION ==========
    if "plan_configuration" in extracted_data:
        plan_extracted = extracted_data["plan_configuration"]
        if isinstance(plan_extracted, dict):
            if "plan_configuration" not in merged:
                merged["plan_configuration"] = {}
            plan_current = merged["plan_configuration"]
            
            # Scalar fields
            for field in ["estimated_build_time_hours", "required_skill_level", "build_complexity_score", 
                         "tool_complexity_score", "annual_maintenance_time_hours", "repair_time_hours"]:
                _merge_scalar_field(plan_current, plan_extracted, field, "plan_configuration", fields_updated)
            
            # Array fields
            _merge_array_field(plan_current, plan_extracted, "required_tools", "plan_configuration", fields_updated, "__string__")
            _merge_array_field(plan_current, plan_extracted, "required_skills", "plan_configuration", fields_updated, "__string__")
    
    # ========== FUNCTIONAL_IO ==========
    if "functional_io" in extracted_data:
        fio_extracted = extracted_data["functional_io"]
        if isinstance(fio_extracted, dict):
            if "functional_io" not in merged:
                merged["functional_io"] = {}
            fio_current = merged["functional_io"]
            
            # Append to inputs/outputs arrays
            _merge_array_field(fio_current, fio_extracted, "inputs", "functional_io", fields_updated, "input_type")
            _merge_array_field(fio_current, fio_extracted, "outputs", "functional_io", fields_updated, "output_type")
            _merge_array_field(fio_current, fio_extracted, "financial_output_value", "functional_io", fields_updated, "output_type")
    
    # ========== ECONOMICS ==========
    # Note: Price mismatch detection is handled separately in asset_service.py
    if "economics" in extracted_data:
        econ_extracted = extracted_data["economics"]
        if isinstance(econ_extracted, dict):
            if "economics" not in merged:
                merged["economics"] = {}
            econ_current = merged["economics"]
            
            # Scalar fields (only fill if empty)
            for field in ["retail_price", "wholesale_price", "minimum_wholesale_quantity",
                         "production_lead_time_days", "production_capacity_per_month", "availability_type"]:
                _merge_scalar_field(econ_current, econ_extracted, field, "economics", fields_updated)
    
    # ========== LICENSING ==========
    if "licensing" in extracted_data:
        lic_extracted = extracted_data["licensing"]
        if isinstance(lic_extracted, dict):
            if "licensing" not in merged:
                merged["licensing"] = {}
            lic_current = merged["licensing"]
            
            for field in ["license_type", "license_version", "allowed_uses", "restrictions",
                         "attribution_required", "derivative_works_allowed", "commercial_use_allowed"]:
                _merge_scalar_field(lic_current, lic_extracted, field, "licensing", fields_updated)
    
    # ========== MATERIALS_AND_BOM ==========
    if "materials_and_bom" in extracted_data:
        _merge_array_field(merged, extracted_data, "materials_and_bom", "", fields_updated, "material_name")
        # Fix the path (remove leading dot)
        if ".materials_and_bom" in fields_updated:
            fields_updated.remove(".materials_and_bom")
            fields_updated.append("materials_and_bom")
    
    # ========== MANUFACTURING_AND_SUPPLY_CHAIN ==========
    if "manufacturing_and_supply_chain" in extracted_data:
        mfg_extracted = extracted_data["manufacturing_and_supply_chain"]
        if isinstance(mfg_extracted, dict):
            if "manufacturing_and_supply_chain" not in merged:
                merged["manufacturing_and_supply_chain"] = {}
            mfg_current = merged["manufacturing_and_supply_chain"]
            
            # Scalar fields
            for field in ["manufacturing_method", "fabrication_complexity_score", "energy_per_unit_kwh",
                         "water_per_unit_liters", "waste_generated_notes", "transport_energy_per_unit_kwh",
                         "supply_chain_risk_notes"]:
                _merge_scalar_field(mfg_current, mfg_extracted, field, "manufacturing_and_supply_chain", fields_updated)
            
            # Array field
            _merge_array_field(mfg_current, mfg_extracted, "manufacturing_locations", 
                              "manufacturing_and_supply_chain", fields_updated, "country")
    
    # ========== ENVIRONMENTAL_IMPACT ==========
    if "environmental_impact" in extracted_data:
        env_extracted = extracted_data["environmental_impact"]
        if isinstance(env_extracted, dict):
            if "environmental_impact" not in merged:
                merged["environmental_impact"] = {}
            env_current = merged["environmental_impact"]
            
            # Scalar fields (excluding AI scores which are reserved)
            for field in ["embodied_carbon_kg_co2e", "operational_carbon_kg_co2e_per_year",
                         "air_pollution_notes", "water_pollution_notes", "soil_pollution_notes",
                         "material_toxicity", "manufacturing_toxicity", "recyclability_percent",
                         "biodegradation_timeline_years", "end_of_life_pathways",
                         "circular_recovery_value", "regenerative_outputs_notes"]:
                _merge_scalar_field(env_current, env_extracted, field, "environmental_impact", fields_updated)
            
            # DO NOT fill ai_environmental_score or ai_environmental_score_breakdown
    
    # ========== HUMAN_IMPACT ==========
    if "human_impact" in extracted_data:
        hi_extracted = extracted_data["human_impact"]
        if isinstance(hi_extracted, dict):
            if "human_impact" not in merged:
                merged["human_impact"] = {}
            hi_current = merged["human_impact"]
            
            # Scalar fields (excluding AI scores which are reserved)
            for field in ["safety_rating", "emissions_during_use_notes", "off_gassing_notes",
                         "noise_level_db", "health_benefits_notes", "risk_factors_notes",
                         "ergonomics_score", "labour_demand_notes", "social_benefit_notes"]:
                _merge_scalar_field(hi_current, hi_extracted, field, "human_impact", fields_updated)
            
            # DO NOT fill ai_human_impact_score or ai_human_impact_score_breakdown
    
    # ========== INTEROPERABILITY ==========
    if "interoperability" in extracted_data:
        inter_extracted = extracted_data["interoperability"]
        if isinstance(inter_extracted, dict):
            if "interoperability" not in merged:
                merged["interoperability"] = {}
            inter_current = merged["interoperability"]
            
            # Scalar fields
            for field in ["integration_notes", "potential_failure_modes", "maintenance_requirements",
                         "replacement_cycle_years"]:
                _merge_scalar_field(inter_current, inter_extracted, field, "interoperability", fields_updated)
            
            # Array fields
            for arr_field in ["compatible_assets", "required_dependencies", "optional_complements", "supported_standards"]:
                _merge_array_field(inter_current, inter_extracted, arr_field, "interoperability", fields_updated, "__string__")
    
    # ========== DEPLOYMENT ==========
    if "deployment" in extracted_data:
        dep_extracted = extracted_data["deployment"]
        if isinstance(dep_extracted, dict):
            if "deployment" not in merged:
                merged["deployment"] = {}
            dep_current = merged["deployment"]
            
            # Scalar fields
            for field in ["min_operating_temperature", "max_operating_temperature",
                         "min_relative_humidity", "max_relative_humidity",
                         "max_uv_exposure_rating", "max_wind_speed_rating", "max_rainfall_intensity",
                         "min_altitude", "max_altitude", "soil_and_ground_notes",
                         "geographic_suitability_notes", "warranty_restrictions_by_geography"]:
                _merge_scalar_field(dep_current, dep_extracted, field, "deployment", fields_updated)
            
            # Array fields
            _merge_array_field(dep_current, dep_extracted, "climate_zones", "deployment", fields_updated, "__string__")
            _merge_array_field(dep_current, dep_extracted, "soil_requirements", "deployment", fields_updated, "__string__")
    
    # ========== LIFECYCLE ==========
    if "lifecycle" in extracted_data:
        lc_extracted = extracted_data["lifecycle"]
        if isinstance(lc_extracted, dict):
            if "lifecycle" not in merged:
                merged["lifecycle"] = {}
            lc_current = merged["lifecycle"]
            
            for field in ["expected_lifespan_normal_years", "expected_lifespan_harsh_years",
                         "degradation_factors", "service_interval_months", "end_of_life_instructions"]:
                _merge_scalar_field(lc_current, lc_extracted, field, "lifecycle", fields_updated)
    
    # ========== DOCUMENTATION_SUMMARY ==========
    if "documentation_summary" in extracted_data:
        ds_extracted = extracted_data["documentation_summary"]
        if isinstance(ds_extracted, dict):
            if "documentation_summary" not in merged:
                merged["documentation_summary"] = {}
            ds_current = merged["documentation_summary"]
            
            for field in ["technical_docs_present", "media_assets_present", "ai_extraction_notes"]:
                _merge_scalar_field(ds_current, ds_extracted, field, "documentation_summary", fields_updated)
    
    # ========== FORBIDDEN SECTIONS - DO NOT MERGE ==========
    # These are explicitly NOT processed even if the model outputs them:
    # - contributor
    # - overview.images
    # - digital_assets.bim_models
    # - commissions_and_settlement
    # - eden_impact_summary
    # - simulation
    # - user_feedback
    
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
