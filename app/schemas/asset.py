from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class SourceUsed(BaseModel):
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    notes: Optional[str] = None


class AIAssistance(BaseModel):
    prefill_status: Optional[str] = "not_run"
    prefill_message: Optional[str] = "Gathering available information and pre-filling fields, please review for accuracy"
    last_run_at: Optional[datetime] = None
    sources_used: Optional[List[SourceUsed]] = []
    fields_prefilled: Optional[List[str]] = []
    issues: Optional[List[str]] = []  # Warnings/issues detected during extraction (e.g., price mismatches)


class SystemMeta(BaseModel):
    status: Optional[str] = "draft"
    version: Optional[str] = "v1"
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    raw_source_text: Optional[str] = None
    provenance_notes: Optional[str] = None
    internal_reviewer_notes: Optional[str] = None


class CategorySelection(BaseModel):
    """A single category selection with primary category and optional subcategories."""
    primary: str
    subcategories: Optional[List[str]] = []


class BasicInformation(BaseModel):
    # New multi-category structure (1-4 primary categories with optional subcategories)
    categories: Optional[List[CategorySelection]] = []
    # Legacy single category fields (kept for backwards compatibility, derived from first category)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    asset_name: Optional[str] = None
    short_summary: Optional[str] = None
    function_purpose: Optional[str] = None
    scaling_potential: Optional[str] = None
    long_description: Optional[str] = None
    associated_physical_asset_id: Optional[str] = None
    associated_plan_asset_id: Optional[str] = None
    company_name: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_website_url: Optional[str] = None
    product_url_with_eden_attribution: Optional[str] = None
    creator_name: Optional[str] = None
    creator_organization: Optional[str] = None
    creator_email: Optional[str] = None
    original_source_url: Optional[str] = None
    attribution_text: Optional[str] = None
    attribution_link: Optional[str] = None
    license_owner: Optional[str] = None
    certifications: Optional[List[str]] = []
    patent_links: Optional[List[str]] = []
    year_introduced_or_updated: Optional[str] = None


class Contributor(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    eden_username: Optional[str] = None
    wallet_address: Optional[str] = None
    contributor_id: Optional[str] = None
    submission_date: Optional[datetime] = None
    notes: Optional[str] = None
    submission_status: Optional[str] = "draft"
    automated_outreach_status: Optional[str] = "not_sent"
    agreement_signed: Optional[bool] = False
    agreement_document_url: Optional[str] = None


class AssetImage(BaseModel):
    url: str
    caption: Optional[str] = None
    is_primary: Optional[bool] = False


class BimModel(BaseModel):
    url: str
    format: Optional[str] = None  # IFC, RVT, OBJ, STL, glTF, USDZ, Other
    source_software: Optional[str] = None


class DigitalAssets(BaseModel):
    bim_models: Optional[List["BimModel"]] = []


class Overview(BaseModel):
    photos: Optional[List[str]] = []
    images: Optional[List[AssetImage]] = []
    key_features: Optional[List[str]] = []
    intended_use_cases: Optional[List[str]] = []
    asset_type_description: Optional[str] = None


class DocumentationUploads(BaseModel):
    technical_spec_sheet_url: Optional[str] = None
    product_datasheet_url: Optional[str] = None
    cad_file_urls: Optional[List[str]] = []
    bim_file_urls: Optional[List[str]] = []
    engineering_drawings_urls: Optional[List[str]] = []
    build_manual_url: Optional[str] = None
    step_by_step_instructions_url: Optional[str] = None
    bom_url: Optional[str] = None
    tools_required_doc_url: Optional[str] = None
    skills_required_doc_url: Optional[str] = None
    safety_data_sheets_urls: Optional[List[str]] = []
    certifications_docs_urls: Optional[List[str]] = []
    patent_docs_urls: Optional[List[str]] = []
    marketing_pdfs_urls: Optional[List[str]] = []
    instructional_video_urls: Optional[List[str]] = []
    additional_docs_urls: Optional[List[str]] = []


class DimensionValue(BaseModel):
    """A dimension value with unit."""
    value: Optional[float] = None
    unit: Optional[str] = None  # cm, m, inches, ft


class WeightValue(BaseModel):
    """A weight value with unit."""
    value: Optional[float] = None
    unit: Optional[str] = None  # kg, lb


class AreaValue(BaseModel):
    """An area value with unit."""
    value: Optional[float] = None
    unit: Optional[str] = None  # m², ft², acres, hectares


class Dimensions(BaseModel):
    """Dimensions with length, width, height and auto-calculated volume."""
    length: Optional[DimensionValue] = None
    width: Optional[DimensionValue] = None
    height: Optional[DimensionValue] = None
    volume: Optional[float] = None  # Auto-calculated: L x W x H


class PackageSize(BaseModel):
    """Package dimensions for shipping."""
    length: Optional[DimensionValue] = None
    width: Optional[DimensionValue] = None
    height: Optional[DimensionValue] = None


class Stackability(BaseModel):
    """Stackability information."""
    is_stackable: Optional[bool] = None
    max_stack_height_units: Optional[int] = None
    max_load_per_unit: Optional[WeightValue] = None


class ModularInterface(BaseModel):
    """A modular interface entry with types and specification."""
    interface_types: Optional[List[str]] = []  # Electrical, Plumbing, Data, Mechanical, Fluid, Hydraulic, Pneumatic, Other
    specification: Optional[str] = None
    notes: Optional[str] = None


class UnitVariantNew(BaseModel):
    """A unit variant with name, model number, and notes."""
    variant_name: Optional[str] = None
    model_number: Optional[str] = None
    notes: Optional[str] = None


class OperatingRange(BaseModel):
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    min_humidity: Optional[float] = None
    max_humidity: Optional[float] = None
    pressure_notes: Optional[str] = None


# Legacy UnitVariant for backwards compatibility
class UnitVariant(BaseModel):
    unit_name: Optional[str] = None
    unit_of_analysis: Optional[str] = None
    dimensions: Optional[Dimensions] = None
    footprint_area: Optional[float] = None
    volume: Optional[float] = None
    unit_weight: Optional[float] = None
    package_size: Optional[str] = None
    package_weight: Optional[float] = None
    stackability_notes: Optional[str] = None
    modular_interfaces: Optional[List[str]] = []
    operating_range: Optional[OperatingRange] = None
    scalability_notes: Optional[str] = None


class PhysicalConfiguration(BaseModel):
    """Physical configuration with detailed specs for EDEN.OS integration."""
    # Legacy field for backwards compatibility
    unit_variants: Optional[List[UnitVariant]] = []
    
    # New detailed fields
    unit_variants_new: Optional[List[UnitVariantNew]] = []
    dimensions: Optional[Dimensions] = None
    footprint_area: Optional[AreaValue] = None
    unit_weight: Optional[WeightValue] = None
    package_size: Optional[PackageSize] = None
    package_weight: Optional[WeightValue] = None
    units_per_package: Optional[int] = None
    stackability: Optional[Stackability] = None
    modular_interfaces: Optional[List[ModularInterface]] = []
    environmental_rating: Optional[str] = None  # Indoor, Outdoor, Marine/Coastal, High-Dust/Industrial, High-Humidity, Explosion-Proof/Hazardous Area, Clean Room, Unknown


class PlanConfiguration(BaseModel):
    build_complexity_score: Optional[int] = None
    tool_complexity_score: Optional[int] = None
    required_skill_level: Optional[str] = None
    required_skills: Optional[List[str]] = []
    required_tools: Optional[List[str]] = []
    estimated_build_time_hours: Optional[float] = None
    annual_maintenance_time_hours: Optional[float] = None
    repair_time_hours: Optional[float] = None


class InputItem(BaseModel):
    input_type: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None  # kW, gallons, tons, lumens, liters, cubic_meters, etc.
    time_period: Optional[str] = None  # instant, hour, day, month, year
    time_profile: Optional[str] = None
    quality_spec: Optional[str] = None
    estimated_financial_value_usd: Optional[float] = None


class OutputItem(BaseModel):
    output_type: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None  # kW, gallons, tons, lumens, liters, cubic_meters, etc.
    time_period: Optional[str] = None  # instant, hour, day, month, year
    quality_spec: Optional[str] = None
    variability_profile: Optional[str] = None
    estimated_financial_value_usd: Optional[float] = None


class FinancialOutputValue(BaseModel):
    output_type: Optional[str] = None
    output_quantity_per_unit: Optional[float] = None
    unit_of_measure: Optional[str] = None
    market_price_per_unit: Optional[float] = None
    currency: Optional[str] = "USD"
    price_region: Optional[str] = None
    price_source_reference: Optional[str] = None
    cycles_per_year: Optional[float] = None
    annual_output_value: Optional[float] = None
    lifetime_output_value: Optional[float] = None
    payback_period_years: Optional[float] = None
    net_financial_yield: Optional[float] = None
    revenue_model: Optional[str] = None
    eden_token_equivalent_value: Optional[float] = None


class FunctionalIO(BaseModel):
    inputs: Optional[List[InputItem]] = []
    outputs: Optional[List[OutputItem]] = []
    financial_output_value: Optional[List[FinancialOutputValue]] = []


class Economics(BaseModel):
    retail_price: Optional[float] = None
    wholesale_price: Optional[float] = None
    minimum_wholesale_quantity: Optional[float] = None
    production_lead_time_days: Optional[float] = None
    production_capacity_per_month: Optional[float] = None
    availability_type: Optional[str] = None  # for_sale, licensed, open_source, proprietary, not_available
    generates_revenue: Optional[str] = None  # yes, no, maybe
    estimated_annual_net_profit_usd: Optional[float] = None


class Licensing(BaseModel):
    license_type: Optional[str] = None
    license_version: Optional[str] = None
    allowed_uses: Optional[str] = None
    restrictions: Optional[str] = None
    attribution_required: Optional[bool] = None
    derivative_works_allowed: Optional[bool] = None
    commercial_use_allowed: Optional[bool] = None


class PayoutSplit(BaseModel):
    supplier_or_creator_percent: Optional[float] = None
    eden_platform_percent: Optional[float] = None
    referrer_percent: Optional[float] = None
    local_community_percent: Optional[float] = None
    vesting_or_lockup_rules: Optional[str] = None


class CommissionsAndSettlement(BaseModel):
    eden_commission_percent: Optional[float] = None
    high_value_commission_rules: Optional[str] = None
    billing_contact_email: Optional[str] = None
    billing_contact_phone: Optional[str] = None
    invoicing_address: Optional[str] = None
    payment_terms: Optional[str] = None
    agreement_document_url: Optional[str] = None
    accepts_fiat: Optional[bool] = None
    accepts_credit_card: Optional[bool] = None
    accepts_eden_tokens: Optional[bool] = None
    accepts_other_crypto: Optional[bool] = None
    primary_settlement_method: Optional[str] = None
    smart_contract_settlement_enabled: Optional[bool] = None
    blockchain_network: Optional[str] = None
    smart_contract_type: Optional[str] = None
    smart_contract_address: Optional[str] = None
    smart_contract_abi_link: Optional[str] = None
    on_chain_asset_id: Optional[str] = None
    eden_token_price: Optional[float] = None
    eden_reward_multiplier: Optional[float] = None
    payout_split: Optional[PayoutSplit] = None
    token_to_fiat_path: Optional[str] = None
    fiat_invoicing_required: Optional[bool] = None
    scout_commission_percent: Optional[float] = None
    scout_payment_method: Optional[str] = None
    scout_payment_conditions: Optional[str] = None
    scout_referral_link: Optional[str] = None


class MaterialItem(BaseModel):
    material_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    source: Optional[str] = None
    estimated_cost: Optional[float] = None
    local_alternatives: Optional[str] = None
    environmental_notes: Optional[str] = None


class ManufacturingLocation(BaseModel):
    city: Optional[str] = None
    state_province: Optional[str] = None
    country: Optional[str] = None


class ManufacturingAndSupplyChain(BaseModel):
    manufacturing_locations: Optional[List[ManufacturingLocation]] = []
    manufacturing_method: Optional[str] = None
    fabrication_complexity_score: Optional[int] = None
    energy_per_unit_kwh: Optional[float] = None
    water_per_unit_liters: Optional[float] = None
    waste_generated_notes: Optional[str] = None
    transport_energy_per_unit_kwh: Optional[float] = None
    supply_chain_risk_notes: Optional[str] = None


class EnvironmentalImpact(BaseModel):
    embodied_carbon_kg_co2e: Optional[float] = None
    operational_carbon_kg_co2e_per_year: Optional[float] = None
    air_pollution_notes: Optional[str] = None
    water_pollution_notes: Optional[str] = None
    soil_pollution_notes: Optional[str] = None
    material_toxicity: Optional[str] = None  # non_toxic, low_toxicity, moderate_toxicity, high_toxicity, unknown
    manufacturing_toxicity: Optional[str] = None  # clean, low_emissions, moderate_emissions, high_emissions, unknown
    recyclability_percent: Optional[float] = None
    biodegradation_timeline_years: Optional[float] = None
    end_of_life_pathways: Optional[str] = None
    circular_recovery_value: Optional[str] = None
    regenerative_outputs_notes: Optional[str] = None
    ai_environmental_score: Optional[float] = None
    ai_environmental_score_breakdown: Optional[str] = None


class HumanImpact(BaseModel):
    safety_rating: Optional[str] = None
    emissions_during_use_notes: Optional[str] = None
    off_gassing_notes: Optional[str] = None
    noise_level_db: Optional[float] = None
    health_benefits_notes: Optional[str] = None
    risk_factors_notes: Optional[str] = None
    ergonomics_score: Optional[float] = None
    labour_demand_notes: Optional[str] = None
    social_benefit_notes: Optional[str] = None
    ai_human_impact_score: Optional[float] = None
    ai_human_impact_score_breakdown: Optional[str] = None


class Interoperability(BaseModel):
    compatible_assets: Optional[List[str]] = []
    required_dependencies: Optional[List[str]] = []
    optional_complements: Optional[List[str]] = []
    supported_standards: Optional[List[str]] = []
    integration_notes: Optional[str] = None
    potential_failure_modes: Optional[str] = None
    maintenance_requirements: Optional[str] = None
    replacement_cycle_years: Optional[float] = None


class Deployment(BaseModel):
    climate_zones: Optional[List[str]] = []
    min_operating_temperature: Optional[float] = None
    max_operating_temperature: Optional[float] = None
    min_relative_humidity: Optional[float] = None
    max_relative_humidity: Optional[float] = None
    max_uv_exposure_rating: Optional[str] = None
    max_wind_speed_rating: Optional[float] = None
    max_rainfall_intensity: Optional[float] = None
    min_altitude: Optional[float] = None
    max_altitude: Optional[float] = None
    soil_requirements: Optional[List[str]] = []
    soil_and_ground_notes: Optional[str] = None
    geographic_suitability_notes: Optional[str] = None
    warranty_restrictions_by_geography: Optional[str] = None


class Lifecycle(BaseModel):
    expected_lifespan_normal_years: Optional[float] = None
    expected_lifespan_harsh_years: Optional[float] = None
    degradation_factors: Optional[str] = None
    service_interval_months: Optional[float] = None
    end_of_life_instructions: Optional[str] = None


class Simulation(BaseModel):
    resource_consumption_curve: Optional[str] = None
    performance_curve: Optional[str] = None
    degradation_curve: Optional[str] = None
    failure_probability_model: Optional[str] = None
    thermal_impact_model: Optional[str] = None
    energy_model: Optional[str] = None
    yield_model: Optional[str] = None
    additional_simulation_parameters: Optional[str] = None


class DocumentationSummary(BaseModel):
    technical_docs_present: Optional[str] = None
    media_assets_present: Optional[str] = None
    ai_extraction_notes: Optional[str] = None


class UserFeedback(BaseModel):
    user_ratings: Optional[List[float]] = []
    field_performance_notes: Optional[str] = None
    reported_issues: Optional[str] = None
    lessons_learned: Optional[str] = None
    suggested_improvements: Optional[str] = None


class EdenImpactSummary(BaseModel):
    eden_positive_impact_points: Optional[float] = None
    best_use_cases: Optional[List[str]] = []
    eden_recommended_rating: Optional[str] = None


class AssetCreate(BaseModel):
    asset_id: Optional[str] = None
    asset_type: str = Field(..., pattern="^(physical|plan|hybrid)$")
    system_meta: Optional[SystemMeta] = None
    ai_assistance: Optional[AIAssistance] = None
    basic_information: Optional[BasicInformation] = None
    contributor: Optional[Contributor] = None
    overview: Optional[Overview] = None
    documentation_uploads: Optional[DocumentationUploads] = None
    physical_configuration: Optional[PhysicalConfiguration] = None
    plan_configuration: Optional[PlanConfiguration] = None
    economics: Optional[Economics] = None
    licensing: Optional[Licensing] = None
    commissions_and_settlement: Optional[CommissionsAndSettlement] = None
    materials_and_bom: Optional[List[MaterialItem]] = []
    manufacturing_and_supply_chain: Optional[ManufacturingAndSupplyChain] = None
    environmental_impact: Optional[EnvironmentalImpact] = None
    human_impact: Optional[HumanImpact] = None
    eden_impact_summary: Optional[EdenImpactSummary] = None
    functional_io: Optional[FunctionalIO] = None
    interoperability: Optional[Interoperability] = None
    deployment: Optional[Deployment] = None
    lifecycle: Optional[Lifecycle] = None
    simulation: Optional[Simulation] = None
    documentation_summary: Optional[DocumentationSummary] = None
    user_feedback: Optional[UserFeedback] = None
    digital_assets: Optional[DigitalAssets] = None

    class Config:
        extra = "allow"


class AssetUpdate(BaseModel):
    asset_type: Optional[str] = None
    system_meta: Optional[dict] = None
    ai_assistance: Optional[dict] = None
    basic_information: Optional[dict] = None
    contributor: Optional[dict] = None
    overview: Optional[dict] = None
    documentation_uploads: Optional[dict] = None
    physical_configuration: Optional[dict] = None
    plan_configuration: Optional[dict] = None
    economics: Optional[dict] = None
    licensing: Optional[dict] = None
    commissions_and_settlement: Optional[dict] = None
    materials_and_bom: Optional[List[dict]] = None
    manufacturing_and_supply_chain: Optional[dict] = None
    environmental_impact: Optional[dict] = None
    human_impact: Optional[dict] = None
    eden_impact_summary: Optional[dict] = None
    functional_io: Optional[dict] = None
    interoperability: Optional[dict] = None
    deployment: Optional[dict] = None
    lifecycle: Optional[dict] = None
    simulation: Optional[dict] = None
    documentation_summary: Optional[dict] = None
    user_feedback: Optional[dict] = None
    digital_assets: Optional[dict] = None

    class Config:
        extra = "allow"


class AssetResponse(BaseModel):
    id: UUID
    asset_id: str
    asset_type: str
    status: str
    submission_status: Optional[str] = None
    category: Optional[str] = None
    scaling_potential: Optional[str] = None
    company_name: Optional[str] = None
    creator_name: Optional[str] = None
    contributor_id: Optional[str] = None
    data: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetListItem(BaseModel):
    id: UUID
    asset_id: str
    asset_type: str
    status: str
    basic_information: Optional[dict] = None
    overview: Optional[dict] = None
    eden_impact_summary: Optional[dict] = None
    deployment: Optional[dict] = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    items: List[Any]
    page: int
    page_size: int
    total: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ReviewRequest(BaseModel):
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None


class RejectRequest(BaseModel):
    reviewer_id: Optional[str] = None
    reason: str


class FileAttachRequest(BaseModel):
    target: str
    url: str
    label: Optional[str] = None


class AIExtractionSource(BaseModel):
    """Sources for AI extraction - website URL and/or uploaded file references."""
    website_url: Optional[str] = None
    uploaded_file_ids: List[str] = []


class AIExtractionRequest(BaseModel):
    """Request model for AI extraction endpoint."""
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


class AIFieldUpdate(BaseModel):
    """A single field update suggested by AI extraction."""
    path: str  # JSON path, e.g. "functional_io.outputs[0].quantity"
    value: Any
    confidence: float  # 0-1 confidence score
    source: str  # which doc/url this came from


class AIExtractionResponse(BaseModel):
    """Response model for AI extraction endpoint."""
    field_updates: List[AIFieldUpdate]
    fields_prefilled: List[str]  # list of JSON paths that were prefilled
    sources_used: List[str]  # URLs or file IDs that were processed
    notes_for_reviewer: List[str]  # human-readable suggestions/notes


# Legacy models for backward compatibility
class AIExtractRequest(BaseModel):
    """Legacy request model - use AIExtractionRequest for new implementations."""
    sources: Optional[dict] = None
    website_url: Optional[str] = None
    use_uploaded_docs: Optional[bool] = True


class AIExtractSources(BaseModel):
    use_uploaded_docs: Optional[bool] = True
    extra_doc_urls: Optional[List[str]] = []
    extra_web_urls: Optional[List[str]] = []
    website_url: Optional[str] = None


class FileUploadResponse(BaseModel):
    url: str
    filename: str
    doc_type: str
    field: Optional[str] = None
