"""
OpenAI provider for EDEN Asset Library AI extraction.

This module provides the OpenAI integration for extracting structured data
from product documentation and URLs to populate EdenAsset fields.

Architecture is designed to be modular - future providers (Anthropic, etc.)
can implement the same interface.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum characters for each context section to fit within model context
MAX_DOC_TEXT_CHARS = 15000
MAX_URL_TEXT_CHARS = 8000
MAX_ASSET_JSON_CHARS = 5000

SYSTEM_PROMPT = """You are an AI assistant that extracts structured data from product documentation for the EDEN Asset Library.

Your task is to read the provided documentation text, short description, and product URL text, then return a JSON object containing EdenAsset fields you can confidently populate.

=== GLOBAL RULES ===

1. NO HALLUCINATION: Only extract facts explicitly present in the documentation OR that can be unambiguously inferred through standard engineering reasoning (e.g., converting units, interpreting temperature ranges, mapping IP ratings to environmental suitability).

2. IF UNCLEAR, LEAVE EMPTY: If you cannot determine a value with confidence, do not include that field in your output.

3. ALWAYS GENERATE long_description: You MUST always generate a fresh 2-4 paragraph description for basic_information.long_description, regardless of whether one already exists. This is an AI-owned field.

4. NEVER USE DOUBLE HYPHENS: Do not use "--" in any text output.

5. UNIT CONVERSIONS ALLOWED: You may convert between units (kg to lb, mm to m, Celsius to Fahrenheit, etc.) when extracting values.

6. REASONED INFERENCE ALLOWED: You may infer values from context when unambiguous. For example:
   - IP65 rating implies "Outdoor" environmental_rating
   - "Suitable for tropical climates" implies high humidity tolerance
   - "Stackable up to 5 units" implies stackability.is_stackable = true

=== SECTIONS YOU MUST NOT TOUCH ===

Do NOT output any fields for these sections, even if you could guess them:
- contributor (identity fields, submission status)
- Company contact fields (company_phone, company_email - only fill company_name if clearly stated)
- URLs entered manually (company_website_url, product_url_with_eden_attribution, original_source_url, attribution_link)
- License/attribution fields (license_owner, attribution_text)
- overview.images[] (do not touch image data)
- digital_assets.bim_models[] (do not populate 3D/BIM files)
- commissions_and_settlement (all fields)
- eden_impact_summary (all fields - human-reviewed only)
- simulation (all fields - reserved for Phase 3)
- user_feedback (all fields)

=== SECTION-BY-SECTION EXTRACTION RULES ===

**basic_information** - AI SHOULD FILL:
- long_description: ALWAYS generate a fresh 2-4 paragraph description
- function_purpose: If clearly stated in docs
- certifications[]: Array of certification names found
- patent_links[]: Array of patent numbers/links found
- year_introduced_or_updated: If explicitly mentioned
- scaling_potential: ONLY if explicitly described as "pilot", "local", "regional", or "global"

AI MAY INFER (only if existing value is empty):
- categories[]: Infer from product type (e.g., "solar panel" -> Energy and Heat)
  Format: [{"primary": "Energy and Heat", "subcategories": ["Solar"]}]

**overview** - AI SHOULD FILL:
- key_features[]: Array of key product features
- intended_use_cases[]: Array of use case descriptions
- asset_type_description: Brief description of the asset type

**physical_configuration** - AI SHOULD FILL:
- dimensions.length/width/height: Use format {"value": number, "unit": "cm"|"m"|"inches"|"ft"}
- dimensions.volume: Auto-calculated or extracted
- footprint_area: {"value": number, "unit": "m2"|"ft2"|"acres"|"hectares"}
- unit_weight: {"value": number, "unit": "kg"|"lb"}
- package_size.length/width/height: Shipping dimensions
- package_weight: {"value": number, "unit": "kg"|"lb"}
- units_per_package: Number of units per package
- environmental_rating: One of "Indoor", "Outdoor", "Marine/Coastal", "High-Dust/Industrial", "High-Humidity", "Explosion-Proof/Hazardous Area", "Clean Room", "Unknown"
- modular_interfaces[]: Array of {"interface_types": ["Electrical"|"Plumbing"|"Data"|"Mechanical"|"Fluid"|"Hydraulic"|"Pneumatic"|"Other"], "specification": string, "notes": string}

AI MAY INFER:
- stackability: {"is_stackable": boolean, "max_stack_height_units": number, "max_load_per_unit": {"value": number, "unit": "kg"|"lb"}}

**plan_configuration** - AI SHOULD FILL (only if explicitly stated):
- estimated_build_time_hours
- required_tools[]: Array of tool names
- required_skills[]: Array of skill descriptions
- required_skill_level: "beginner", "intermediate", "advanced", "expert"

**functional_io** - AI SHOULD FILL:
- inputs[]: Array of input items with format:
  {"input_type": string, "quantity": number, "unit": string, "time_period": "per_day"|"per_week"|"per_month"|"per_year", "quality_spec": string, "estimated_financial_value_usd": number (ONLY if explicitly stated)}
- outputs[]: Array of output items with same format plus "variability_profile": string

Common units: kW, kWh, W, Wh, MWh, BTU, calories, joules, gallons, liters, cubic_meters, cubic_feet, tons, kg, pounds, grams, lumens, lux, square_feet, square_meters, pieces, units, systems, people_served, households_served

**economics** - AI SHOULD FILL (only if empty):
- retail_price: Number (no currency symbols)
- wholesale_price: Number
- minimum_wholesale_quantity: Number
- production_lead_time_days: Number
- production_capacity_per_month: Number
- availability_type: "for_sale"|"licensed"|"open_source"|"proprietary"|"not_available"

IMPORTANT: If the existing asset already has a retail_price and you find a different price in the docs, DO NOT output a retail_price. The backend will handle price mismatch warnings.

**licensing** - AI SHOULD FILL (ONLY if explicitly stated):
- license_type: e.g., "MIT", "GPL", "Proprietary", "Creative Commons"
- license_version: e.g., "3.0", "4.0"
- attribution_required: boolean
- derivative_works_allowed: boolean
- commercial_use_allowed: boolean

**materials_and_bom[]** - AI SHOULD FILL:
Array of: {"material_name": string, "quantity": number, "unit": string, "estimated_cost": number (ONLY if docs include specific numbers), "environmental_notes": string}

**manufacturing_and_supply_chain** - AI SHOULD FILL:
- manufacturing_locations[]: Array of {"city": string, "state_province": string, "country": string}
- manufacturing_method: Description of manufacturing process
- energy_per_unit_kwh: Number
- water_per_unit_liters: Number
- waste_generated_notes: String
- transport_energy_per_unit_kwh: Number
- supply_chain_risk_notes: String

**environmental_impact** - AI SHOULD FILL:
- embodied_carbon_kg_co2e: Number
- operational_carbon_kg_co2e_per_year: Number
- air_pollution_notes, water_pollution_notes, soil_pollution_notes: Strings
- recyclability_percent: Number (0-100)
- biodegradation_timeline_years: Number
- end_of_life_pathways: String
- regenerative_outputs_notes: String

AI MAY INFER (from SDS or similar):
- material_toxicity: "non_toxic"|"low_toxicity"|"moderate_toxicity"|"high_toxicity"|"unknown"
- manufacturing_toxicity: "clean"|"low_emissions"|"moderate_emissions"|"high_emissions"|"unknown"

DO NOT FILL: ai_environmental_score, ai_environmental_score_breakdown (reserved for future models)

**human_impact** - AI SHOULD FILL:
- safety_rating: String
- emissions_during_use_notes: String
- off_gassing_notes: String
- noise_level_db: Number
- health_benefits_notes: String
- risk_factors_notes: String
- ergonomics_score: Number (1-10)
- labour_demand_notes: String
- social_benefit_notes: String

DO NOT FILL: ai_human_impact_score, ai_human_impact_score_breakdown

**interoperability** - AI SHOULD FILL:
- supported_standards[]: Array of standard names
- integration_notes: String
- required_dependencies[]: Array of dependency names
- optional_complements[]: Array of complement names
- potential_failure_modes: String
- maintenance_requirements: String
- replacement_cycle_years: Number

**deployment** - AI SHOULD FILL:
- climate_zones[]: Array of climate zone names
- min_operating_temperature, max_operating_temperature: Numbers (Celsius)
- min_relative_humidity, max_relative_humidity: Numbers (0-100)
- max_uv_exposure_rating: String
- max_wind_speed_rating: Number (m/s or mph)
- max_rainfall_intensity: Number
- min_altitude, max_altitude: Numbers (meters)
- soil_requirements[]: Array of soil type names
- soil_and_ground_notes: String
- geographic_suitability_notes: String
- warranty_restrictions_by_geography: String

**lifecycle** - AI SHOULD FILL:
- expected_lifespan_normal_years: Number
- expected_lifespan_harsh_years: Number
- degradation_factors: String
- service_interval_months: Number
- end_of_life_instructions: String

**documentation_summary** - AI SHOULD FILL:
- technical_docs_present: Brief summary of what technical docs were found
- media_assets_present: Brief summary of media assets mentioned
- ai_extraction_notes: Brief summary of what was extracted and any limitations

=== OUTPUT FORMAT ===

Return a single JSON object with only the fields you are proposing to fill. Do not include:
- Null values
- Empty arrays []
- Empty strings ""
- Fields from forbidden sections

Example output structure:
{
  "basic_information": {
    "long_description": "2-4 paragraph description...",
    "function_purpose": "...",
    "certifications": ["CE", "UL"]
  },
  "overview": {
    "key_features": ["Feature 1", "Feature 2"],
    "intended_use_cases": ["Use case 1"]
  },
  "physical_configuration": {
    "dimensions": {
      "length": {"value": 100, "unit": "cm"},
      "width": {"value": 50, "unit": "cm"},
      "height": {"value": 30, "unit": "cm"}
    },
    "unit_weight": {"value": 25, "unit": "kg"},
    "environmental_rating": "Outdoor"
  },
  "functional_io": {
    "inputs": [
      {"input_type": "electricity", "quantity": 10, "unit": "kW", "time_period": "per_hour"}
    ],
    "outputs": [
      {"output_type": "hot water", "quantity": 200, "unit": "liters", "time_period": "per_day"}
    ]
  },
  "economics": {
    "retail_price": 1500,
    "availability_type": "for_sale"
  }
}

Return ONLY valid JSON, no markdown code blocks or explanations."""

USER_PROMPT_TEMPLATE = """Here is the current asset JSON (for context - check which fields already have values):
```json
{current_asset_json}
```

Short Description provided by contributor:
{short_description}

Product URL:
{product_url}

Product Page Text (extracted from URL):
{product_page_text}

Documentation Text (extracted from uploaded files):
{documentation_text}

Based on the above information, extract and return a JSON object with the EdenAsset fields you can confidently populate.

REMEMBER:
- ALWAYS generate a fresh long_description (2-4 paragraphs) - this is required
- Only fill empty fields for other sections (don't overwrite existing values)
- Do NOT output forbidden sections (contributor, images, bim_models, commissions, eden_impact_summary, simulation, user_feedback)
- For economics.retail_price: only include if the existing asset has no retail_price set
- Use proper units and formats as specified in the system prompt
- You may use reasoned inference for unit conversions, IP ratings, temperature ranges, etc.

Return ONLY valid JSON, no markdown code blocks or explanations."""


class OpenAIProvider:
    """OpenAI provider for AI extraction."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.client = None
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
    
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        return self.client is not None and self.api_key is not None
    
    async def extract(
        self,
        documentation_text: str,
        short_description: Optional[str],
        product_url: Optional[str],
        product_page_text: Optional[str],
        current_asset: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract EdenAsset data from provided context using OpenAI.
        
        Args:
            documentation_text: Concatenated text from all uploaded documents
            short_description: The contributor's short description
            product_url: The external product URL
            product_page_text: Text extracted from the product URL
            current_asset: The current asset JSON for context
            
        Returns:
            A partial EdenAsset dict with extracted fields
        """
        if not self.is_configured():
            raise ValueError("OpenAI provider is not configured. Set OPENAI_API_KEY.")
        
        # Truncate inputs to fit context window
        doc_text = documentation_text[:MAX_DOC_TEXT_CHARS] if documentation_text else "No documentation provided."
        url_text = product_page_text[:MAX_URL_TEXT_CHARS] if product_page_text else "No product page text available."
        
        # Prepare current asset JSON (truncated)
        asset_json = json.dumps(current_asset, indent=2, default=str)
        if len(asset_json) > MAX_ASSET_JSON_CHARS:
            # Keep only key sections for context
            minimal_asset = {
                "basic_information": current_asset.get("basic_information", {}),
                "technical_specs": current_asset.get("technical_specs", [])[:3],  # First 3 specs
                "physical_configuration": current_asset.get("physical_configuration", {}),
            }
            asset_json = json.dumps(minimal_asset, indent=2, default=str)
        
        # Build the user prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            current_asset_json=asset_json,
            short_description=short_description or "Not provided",
            product_url=product_url or "Not provided",
            product_page_text=url_text,
            documentation_text=doc_text,
        )
        
        logger.info(f"Calling OpenAI {self.model} for asset extraction")
        logger.debug(f"Documentation text length: {len(doc_text)}")
        logger.debug(f"Product page text length: {len(url_text)}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=4000,
            )
            
            result_text = response.choices[0].message.content
            logger.info(f"OpenAI response received, length: {len(result_text)}")
            
            # Parse the JSON response
            try:
                extracted_data = json.loads(result_text)
                logger.info(f"Successfully parsed extraction result with keys: {list(extracted_data.keys())}")
                return extracted_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                logger.debug(f"Raw response: {result_text[:500]}")
                return {}
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise


async def extract_eden_asset_data(
    documentation_text: str,
    short_description: Optional[str] = None,
    product_url: Optional[str] = None,
    product_page_text: Optional[str] = None,
    current_asset: Optional[Dict[str, Any]] = None,
    model: str = "gpt-4o",
) -> Dict[str, Any]:
    """
    Convenience function to extract EdenAsset data using OpenAI.
    
    This is the main entry point for AI extraction. It creates an OpenAI provider
    and calls the extract method.
    
    Args:
        documentation_text: Concatenated text from all uploaded documents
        short_description: The contributor's short description
        product_url: The external product URL
        product_page_text: Text extracted from the product URL
        current_asset: The current asset JSON for context
        model: The OpenAI model to use (default: gpt-4o)
        
    Returns:
        A partial EdenAsset dict with extracted fields
    """
    provider = OpenAIProvider(model=model)
    
    if not provider.is_configured():
        logger.warning("OpenAI provider not configured, returning empty result")
        return {}
    
    return await provider.extract(
        documentation_text=documentation_text,
        short_description=short_description,
        product_url=product_url,
        product_page_text=product_page_text,
        current_asset=current_asset or {},
    )
