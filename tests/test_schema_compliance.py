import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, ValidationError, validate


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "eden_asset.schema.json"
FIXTURES_PATH = Path(__file__).parent / "fixtures" / "example_valid_asset.json"


@pytest.fixture
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def validator(schema):
    return Draft7Validator(schema)


@pytest.fixture
def example_assets():
    with open(FIXTURES_PATH) as f:
        return json.load(f)


class TestSchemaStructure:
    def test_schema_file_exists(self):
        assert SCHEMA_PATH.exists(), f"Schema file not found at {SCHEMA_PATH}"

    def test_schema_is_valid_json(self, schema):
        assert isinstance(schema, dict)
        assert "type" in schema
        assert schema["type"] == "object"

    def test_schema_has_required_properties(self, schema):
        assert "properties" in schema
        props = schema["properties"]
        assert "asset_id" in props
        assert "asset_type" in props
        assert "system_meta" in props
        assert "ai_assistance" in props
        assert "basic_information" in props

    def test_asset_type_enum_values(self, schema):
        asset_type = schema["properties"]["asset_type"]
        assert "enum" in asset_type
        assert set(asset_type["enum"]) == {"physical", "plan", "hybrid"}

    def test_system_meta_status_enum(self, schema):
        system_meta = schema["properties"]["system_meta"]
        status = system_meta["properties"]["status"]
        assert "enum" in status
        assert set(status["enum"]) == {"draft", "under_review", "approved", "deprecated"}


class TestValidAssets:
    def test_physical_asset_validates(self, validator, example_assets):
        asset = example_assets["physical_asset"]
        errors = list(validator.iter_errors(asset))
        assert len(errors) == 0, f"Physical asset validation errors: {[e.message for e in errors]}"

    def test_plan_asset_validates(self, validator, example_assets):
        asset = example_assets["plan_asset"]
        errors = list(validator.iter_errors(asset))
        assert len(errors) == 0, f"Plan asset validation errors: {[e.message for e in errors]}"

    def test_hybrid_asset_validates(self, validator, example_assets):
        asset = example_assets["hybrid_asset"]
        errors = list(validator.iter_errors(asset))
        assert len(errors) == 0, f"Hybrid asset validation errors: {[e.message for e in errors]}"

    def test_minimal_valid_asset_validates(self, validator, example_assets):
        asset = example_assets["minimal_valid_asset"]
        errors = list(validator.iter_errors(asset))
        assert len(errors) == 0, f"Minimal asset validation errors: {[e.message for e in errors]}"

    def test_empty_object_validates(self, validator):
        errors = list(validator.iter_errors({}))
        assert len(errors) == 0, "Empty object should be valid (no required fields)"


class TestInvalidAssets:
    def test_invalid_asset_type_rejected(self, validator):
        invalid_asset = {"asset_type": "invalid_type"}
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid asset_type should be rejected"
        assert any("invalid_type" in str(e.message) for e in errors)

    def test_invalid_status_rejected(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "system_meta": {"status": "invalid_status"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid status should be rejected"

    def test_invalid_scaling_potential_rejected(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "basic_information": {"scaling_potential": "invalid_scale"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid scaling_potential should be rejected"

    def test_invalid_prefill_status_rejected(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "ai_assistance": {"prefill_status": "invalid_prefill"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid prefill_status should be rejected"

    def test_invalid_submission_status_rejected(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "contributor": {"submission_status": "invalid_submission"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid submission_status should be rejected"

    def test_invalid_availability_type_rejected(self, validator):
        invalid_asset = {
            "asset_type": "plan",
            "economics": {"availability_type": "invalid_access"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid availability_type should be rejected"

    def test_invalid_settlement_method_rejected(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "commissions_and_settlement": {"primary_settlement_method": "invalid_method"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid primary_settlement_method should be rejected"

    def test_invalid_revenue_model_rejected(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "functional_io": {
                "financial_output_value": [{"revenue_model": "invalid_model"}]
            }
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid revenue_model should be rejected"


class TestTypeEnforcement:
    def test_string_field_rejects_number(self, validator):
        invalid_asset = {"asset_id": 12345}
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "String field should reject number"
        assert any("type" in str(e.schema_path) or "12345" in str(e.message) for e in errors)

    def test_number_field_rejects_string(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "economics": {"retail_price": "not_a_number"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Number field should reject string"

    def test_boolean_field_rejects_string(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "contributor": {"agreement_signed": "yes"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Boolean field should reject string"

    def test_array_field_rejects_string(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "overview": {"photos": "not_an_array"}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Array field should reject string"

    def test_object_field_rejects_string(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "system_meta": "not_an_object"
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Object field should reject string"

    def test_integer_field_rejects_float(self, validator):
        invalid_asset = {
            "asset_type": "plan",
            "plan_configuration": {"build_complexity_score": 3.5}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Integer field should reject float"

    def test_datetime_field_accepts_string(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "system_meta": {"created_at": "2024-01-15T10:30:00Z"}
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, "Valid datetime string should pass"

    def test_datetime_field_rejects_non_string(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "system_meta": {"created_at": 12345}
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Datetime field should reject non-string types"


class TestNestedStructures:
    def test_unit_variants_array_structure(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "physical_configuration": {
                "unit_variants": [
                    {
                        "unit_name": "Standard",
                        "dimensions": {"length": 10, "width": 5, "height": 3}
                    }
                ]
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid nested structure should pass: {[e.message for e in errors]}"

    def test_invalid_dimensions_type(self, validator):
        invalid_asset = {
            "asset_type": "physical",
            "physical_configuration": {
                "unit_variants": [
                    {
                        "dimensions": {"length": "ten"}
                    }
                ]
            }
        }
        errors = list(validator.iter_errors(invalid_asset))
        assert len(errors) > 0, "Invalid dimension type should be rejected"

    def test_materials_and_bom_array(self, validator):
        valid_asset = {
            "asset_type": "plan",
            "materials_and_bom": [
                {
                    "material_name": "Steel",
                    "quantity": 10,
                    "unit": "kg",
                    "estimated_cost": 50.00
                }
            ]
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid materials_and_bom should pass: {[e.message for e in errors]}"

    def test_manufacturing_locations_array(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "manufacturing_and_supply_chain": {
                "manufacturing_locations": [
                    {"city": "Portland", "state_province": "OR", "country": "USA"}
                ]
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid manufacturing locations should pass: {[e.message for e in errors]}"

    def test_functional_io_inputs_outputs(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "functional_io": {
                "inputs": [
                    {"input_type": "water", "quantity": 100, "time_profile": "daily"}
                ],
                "outputs": [
                    {"output_type": "purified_water", "quantity": 95}
                ]
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid functional_io should pass: {[e.message for e in errors]}"

    def test_payout_split_nested_object(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "commissions_and_settlement": {
                "payout_split": {
                    "supplier_or_creator_percent": 70,
                    "eden_platform_percent": 10,
                    "referrer_percent": 15,
                    "local_community_percent": 5
                }
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid payout_split should pass: {[e.message for e in errors]}"


class TestAllSchemaSections:
    def test_licensing_section(self, validator):
        valid_asset = {
            "asset_type": "plan",
            "licensing": {
                "license_type": "MIT",
                "license_version": "1.0",
                "attribution_required": True,
                "derivative_works_allowed": True,
                "commercial_use_allowed": False
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid licensing should pass: {[e.message for e in errors]}"

    def test_environmental_impact_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "environmental_impact": {
                "embodied_carbon_kg_co2e": 150.5,
                "recyclability_percent": 85,
                "ai_environmental_score": 92.5
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid environmental_impact should pass: {[e.message for e in errors]}"

    def test_human_impact_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "human_impact": {
                "safety_rating": "A",
                "noise_level_db": 45,
                "ergonomics_score": 8.5,
                "ai_human_impact_score": 90
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid human_impact should pass: {[e.message for e in errors]}"

    def test_interoperability_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "interoperability": {
                "compatible_assets": ["EDEN-001", "EDEN-002"],
                "required_dependencies": ["Power source"],
                "supported_standards": ["ISO 9001"]
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid interoperability should pass: {[e.message for e in errors]}"

    def test_deployment_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "deployment": {
                "climate_zones": ["tropical", "temperate"],
                "min_operating_temperature": -10,
                "max_operating_temperature": 50,
                "soil_requirements": ["stable", "level"]
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid deployment should pass: {[e.message for e in errors]}"

    def test_lifecycle_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "lifecycle": {
                "expected_lifespan_normal_years": 15,
                "expected_lifespan_harsh_years": 10,
                "service_interval_months": 6
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid lifecycle should pass: {[e.message for e in errors]}"

    def test_simulation_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "simulation": {
                "performance_curve": "linear",
                "energy_model": "solar_dependent",
                "yield_model": "500L/day"
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid simulation should pass: {[e.message for e in errors]}"

    def test_documentation_summary_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "documentation_summary": {
                "technical_docs_present": "Complete",
                "media_assets_present": "Photos available"
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid documentation_summary should pass: {[e.message for e in errors]}"

    def test_user_feedback_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "user_feedback": {
                "user_ratings": [4.5, 4.8, 5.0],
                "field_performance_notes": "Excellent in field trials",
                "suggested_improvements": "Add remote monitoring"
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid user_feedback should pass: {[e.message for e in errors]}"

    def test_eden_impact_summary_section(self, validator):
        valid_asset = {
            "asset_type": "physical",
            "eden_impact_summary": {
                "eden_positive_impact_points": 850,
                "best_use_cases": ["Rural water access", "Disaster relief"],
                "eden_recommended_rating": "Highly Recommended"
            }
        }
        errors = list(validator.iter_errors(valid_asset))
        assert len(errors) == 0, f"Valid eden_impact_summary should pass: {[e.message for e in errors]}"
