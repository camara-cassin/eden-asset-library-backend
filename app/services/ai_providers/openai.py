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

# Target fields for v1 extraction
V1_TARGET_FIELDS = [
    "basic_information.long_description",
    "technical_specs",
    "physical_configuration.dimensions",
    "physical_configuration.unit_weight",
    "physical_configuration.package_size",
    "physical_configuration.package_weight",
    "physical_configuration.footprint_area",
    "physical_configuration.modular_interfaces",
    "physical_configuration.environmental_rating",
    "operational_specs.operating_temperature_min",
    "operational_specs.operating_temperature_max",
    "operational_specs.wind_rating",
    "operational_specs.snow_rating",
    "operational_specs.rain_rating",
]

SYSTEM_PROMPT = """You are an AI assistant that extracts structured data from product documentation for the EDEN Asset Library.

Your task is to read the provided documentation text, short description, and product URL text, then return a JSON object containing only the EdenAsset fields you can confidently populate.

IMPORTANT RULES:
1. Never hallucinate values. Only extract facts explicitly present in the documentation.
2. Never use double hyphens in any text output.
3. Only return fields you can fill with high confidence. Leave out fields you're uncertain about.
4. Be concise in descriptions and notes.
5. For numerical values, extract the number and unit separately when possible.
6. For dimensions, use the format: {"value": number, "unit": "cm"|"m"|"inches"|"ft"}
7. For weights, use the format: {"value": number, "unit": "kg"|"lb"}
8. For areas, use the format: {"value": number, "unit": "m²"|"ft²"|"acres"|"hectares"}

TARGET FIELDS FOR THIS EXTRACTION:
- long_description: A 2-4 paragraph human-readable description of the product (only if not already present)
- technical_specs: Array of {name, value, unit, notes} objects for technical specifications
- physical_configuration:
  - dimensions: {length, width, height} with value+unit pairs, and auto-calculated volume
  - unit_weight: {value, unit} for single unit weight
  - package_size: {length, width, height} with value+unit pairs for shipping
  - package_weight: {value, unit} for package weight
  - footprint_area: {value, unit} for floor space required
  - modular_interfaces: Array of {interface_types: string[], specification, notes}
  - environmental_rating: One of "Indoor", "Outdoor", "Marine / Coastal", "High-Dust / Industrial", "High-Humidity", "Explosion-Proof / Hazardous Area", "Clean Room", "Unknown"
- operational_specs:
  - operating_temperature_min/max
  - wind_rating, snow_rating, rain_rating (weather tolerance)

Return a JSON object with only the fields you can confidently extract. Do not include fields you cannot determine from the provided context."""

USER_PROMPT_TEMPLATE = """Here is the current asset JSON (for context - do not repeat existing values):
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

Based on the above information, extract and return a JSON object with the EdenAsset fields you can confidently populate. Remember:
- Only include fields you can extract with confidence
- Do not overwrite fields that already have values in the current asset
- For long_description, write 2-4 paragraphs describing the product
- For technical_specs, create an array of specification objects
- Use proper units and formats as specified

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
