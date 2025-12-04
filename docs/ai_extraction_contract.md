# AI Extraction Contract

This document describes the contract for AI-powered data extraction in the EDEN Asset Library. The system is designed to accept documents and URLs, analyze them, and pre-fill asset fields with extracted information.

## Overview

The AI extraction system processes uploaded documents (PDFs, CAD files, images) and website URLs to automatically populate asset fields. When `USE_REAL_AI=false` (default), the system operates in stub mode with placeholder data. When `USE_REAL_AI=true`, it calls an external AI service.

## Request Model: AIExtractionRequest

```python
class AIExtractionSource(BaseModel):
    website_url: Optional[str] = None
    uploaded_file_ids: List[str] = []

class AIExtractionRequest(BaseModel):
    asset_id: str
    sources: AIExtractionSource
    target_sections: List[str] = [
        "basic_information",
        "functional_io",
        "economics",
        "physical_configuration",
        "environmental_impact",
        "human_impact",
        "deployment",
    ]
```

### Example Request

```json
{
  "asset_id": "ASSET_ABC123DEF456",
  "sources": {
    "website_url": "https://example.com/products/solar-panel-x100",
    "uploaded_file_ids": [
      "/uploads/ASSET_ABC123DEF456/technical_spec.pdf",
      "/uploads/ASSET_ABC123DEF456/datasheet.pdf"
    ]
  },
  "target_sections": [
    "basic_information",
    "functional_io",
    "economics"
  ]
}
```

## Response Model: AIExtractionResponse

```python
class AIFieldUpdate(BaseModel):
    path: str         # JSON path, e.g. "functional_io.outputs[0].quantity"
    value: Any        # The extracted value
    confidence: float # 0-1 confidence score
    source: str       # Which doc/URL this came from

class AIExtractionResponse(BaseModel):
    field_updates: List[AIFieldUpdate]
    fields_prefilled: List[str]      # List of JSON paths that were prefilled
    sources_used: List[str]          # URLs or file IDs that were processed
    notes_for_reviewer: List[str]    # Human-readable suggestions/notes
```

### Example Response

```json
{
  "field_updates": [
    {
      "path": "basic_information.short_summary",
      "value": "High-efficiency monocrystalline solar panel with 400W output capacity, designed for residential and commercial rooftop installations.",
      "confidence": 0.92,
      "source": "https://example.com/products/solar-panel-x100"
    },
    {
      "path": "functional_io.outputs[0]",
      "value": {
        "output_type": "Electricity",
        "quantity": 400,
        "unit": "W",
        "time_period": "per_hour",
        "estimated_financial_value_usd": 0.048,
        "quality_spec": "DC output, 48V nominal",
        "variability_profile": "Peak output under standard test conditions (STC)"
      },
      "confidence": 0.88,
      "source": "/uploads/ASSET_ABC123DEF456/technical_spec.pdf"
    },
    {
      "path": "economics.retail_price",
      "value": 299.99,
      "confidence": 0.95,
      "source": "https://example.com/products/solar-panel-x100"
    }
  ],
  "fields_prefilled": [
    "basic_information.short_summary",
    "functional_io.outputs[0].output_type",
    "functional_io.outputs[0].quantity",
    "functional_io.outputs[0].unit",
    "functional_io.outputs[0].time_period",
    "functional_io.outputs[0].estimated_financial_value_usd",
    "economics.retail_price"
  ],
  "sources_used": [
    "https://example.com/products/solar-panel-x100",
    "/uploads/ASSET_ABC123DEF456/technical_spec.pdf",
    "/uploads/ASSET_ABC123DEF456/datasheet.pdf"
  ],
  "notes_for_reviewer": [
    "Extracted product specifications from manufacturer website",
    "Technical datasheet provided detailed electrical specifications",
    "Retail price found on product page - verify if this is current pricing",
    "Environmental impact data not found in provided sources - consider adding lifecycle assessment documents"
  ]
}
```

## Endpoint

```
POST /api/v1/assets/{asset_id}/ai-extract
```

### Authentication

Requires a valid JWT token in the `Authorization: Bearer <token>` header.

### Authorization

- Contributors can only run AI extraction on their own assets
- Admins can run AI extraction on any asset

## How to Implement a Real AI Service

When `USE_REAL_AI=true`, the backend calls an external AI service. To implement a compatible AI service:

1. **Accept the request payload** containing:
   - `asset_id`: The asset being processed
   - `sources`: List of URLs and file paths to analyze
   - `current_asset`: The current asset data (for context)

2. **Process all sources**:
   - For URLs: Scrape and analyze the webpage content
   - For documents: Extract text from PDFs, parse CAD files, analyze images
   - Use OCR for scanned documents
   - Extract structured data from tables and specifications

3. **Map extracted data to asset fields**:
   - Use the EdenAsset schema to understand field structure
   - Generate JSON paths for each extracted value
   - Assign confidence scores based on extraction certainty
   - Track which source each value came from

4. **Return the response** in AIExtractionResponse format:
   - Include all field updates with paths, values, confidence, and sources
   - List all fields that were prefilled
   - List all sources that were successfully processed
   - Add human-readable notes for the reviewer

5. **Handle errors gracefully**:
   - If a source cannot be processed, note it but continue with others
   - Return partial results rather than failing completely
   - Include error notes in `notes_for_reviewer`

## Configuration

Set the following environment variables:

```bash
# Enable real AI extraction (default: false)
USE_REAL_AI=true

# URL of the AI extraction service
AI_SERVICE_URL=https://your-ai-service.example.com
```

The AI service endpoint should be:
```
POST {AI_SERVICE_URL}/eden/assets/extract
```

## Asset ai_assistance Section

After extraction, the asset's `ai_assistance` section is updated:

```json
{
  "ai_assistance": {
    "prefill_status": "complete",
    "prefill_message": "AI extraction completed successfully",
    "last_run_at": "2025-12-04T22:30:00.000Z",
    "sources_used": [
      {
        "source_type": "web_search",
        "source_ref": "https://example.com/products/solar-panel-x100",
        "notes": "Processed by AI service"
      },
      {
        "source_type": "document",
        "source_ref": "/uploads/ASSET_ABC123DEF456/technical_spec.pdf",
        "notes": "Processed by AI service"
      }
    ],
    "fields_prefilled": [
      "basic_information.short_summary",
      "functional_io.outputs[0].output_type",
      "functional_io.outputs[0].quantity",
      "economics.retail_price"
    ]
  }
}
```

## Supported Units and Time Periods

### Units
kW, kWh, W, Wh, MWh, BTU, calories, joules, gallons, liters, cubic_meters, cubic_feet, cubic_yards, tons, kg, pounds, grams, lumens, lux, square_feet, square_meters, acres, hectares, pieces, units, systems, people_served, households_served

### Time Periods
instant, per_minute, per_hour, per_day, per_week, per_month, per_year, one_time
