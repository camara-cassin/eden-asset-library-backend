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


class BasicInformation(BaseModel):
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


class Overview(BaseModel):
    photos: Optional[List[str]] = []
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


class Dimensions(BaseModel):
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


class OperatingRange(BaseModel):
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    min_humidity: Optional[float] = None
    max_humidity: Optional[float] = None
    pressure_notes: Optional[str] = None


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
    unit_variants: Optional[List[UnitVariant]] = []


class PlanConfiguration(BaseModel):
    build_complexity_score: Optional[int] = None
    tool_complexity_score: Optional[int] = None
    required_skill_level: Optional[str] = None
    required_skills: Optional[List[str]] = []
    required_tools: Optional[List[str]] = []
    estimated_build_time_hours: Optional[float] = None
    annual_maintenance_time_hours: Optional[float] = None
    repair_time_hours: Optional[float] = None


class IOItem(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None


class FunctionalIO(BaseModel):
    inputs: Optional[List[IOItem]] = []
    outputs: Optional[List[IOItem]] = []


class Economics(BaseModel):
    retail_price: Optional[float] = None
    currency: Optional[str] = None
    price_notes: Optional[str] = None
    estimated_lifespan_years: Optional[float] = None
    maintenance_cost_annual: Optional[float] = None
    roi_notes: Optional[str] = None


class Deployment(BaseModel):
    climate_zones: Optional[List[str]] = []
    terrain_types: Optional[List[str]] = []
    infrastructure_requirements: Optional[List[str]] = []
    deployment_notes: Optional[str] = None


class EdenImpactSummary(BaseModel):
    eden_positive_impact_points: Optional[float] = None
    eden_recommended_rating: Optional[str] = None
    impact_categories: Optional[List[str]] = []
    impact_notes: Optional[str] = None


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
    functional_io: Optional[FunctionalIO] = None
    economics: Optional[Economics] = None
    deployment: Optional[Deployment] = None
    eden_impact_summary: Optional[EdenImpactSummary] = None

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
    functional_io: Optional[dict] = None
    economics: Optional[dict] = None
    deployment: Optional[dict] = None
    eden_impact_summary: Optional[dict] = None

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


class AIExtractRequest(BaseModel):
    sources: Optional[dict] = None


class AIExtractSources(BaseModel):
    use_uploaded_docs: Optional[bool] = True
    extra_doc_urls: Optional[List[str]] = []
    extra_web_urls: Optional[List[str]] = []
