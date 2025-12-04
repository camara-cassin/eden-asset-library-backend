from fastapi import APIRouter, Query
from typing import Optional, List

router = APIRouter()

ASSET_TYPES = ["physical", "plan", "hybrid"]

CATEGORIES = [
    "Energy",
    "Water",
    "Food & Agriculture",
    "Shelter & Construction",
    "Waste Management",
    "Transportation",
    "Health & Sanitation",
    "Communication",
    "Education",
    "Manufacturing",
]

SUBCATEGORIES = {
    "Energy": ["Solar", "Wind", "Hydro", "Biomass", "Geothermal", "Storage", "Grid", "Efficiency"],
    "Water": ["Purification", "Collection", "Storage", "Distribution", "Irrigation", "Desalination"],
    "Food & Agriculture": ["Farming", "Aquaculture", "Livestock", "Processing", "Storage", "Distribution"],
    "Shelter & Construction": ["Housing", "Infrastructure", "Materials", "Tools", "Insulation"],
    "Waste Management": ["Recycling", "Composting", "Sanitation", "Hazardous", "E-waste"],
    "Transportation": ["Vehicles", "Infrastructure", "Logistics", "Public Transit"],
    "Health & Sanitation": ["Medical Equipment", "Sanitation", "Diagnostics", "Preventive"],
    "Communication": ["Networks", "Devices", "Software", "Broadcasting"],
    "Education": ["Tools", "Content", "Infrastructure", "Training"],
    "Manufacturing": ["Equipment", "Processes", "Materials", "Quality Control"],
}

SCALING_POTENTIALS = ["pilot", "local", "regional", "global"]

LICENSE_TYPES = [
    "Open Source",
    "Creative Commons",
    "Proprietary",
    "Public Domain",
    "MIT",
    "GPL",
    "Apache 2.0",
    "BSD",
    "Commercial",
    "Custom",
]

CLIMATE_ZONES = [
    "1", "2", "3", "4", "5", "6", "7", "8",
    "Tropical", "Dry", "Temperate", "Continental", "Polar",
    "A", "B", "C", "D", "E",
]

SUBMISSION_STATUSES = [
    "draft",
    "pending_review",
    "pending_supplier_contact",
    "pending_creator_contact",
    "pending_license_confirmation",
    "pending_agreement",
    "complete",
    "approved",
    "changes_requested",
    "rejected",
]

SYSTEM_STATUSES = ["draft", "under_review", "approved", "deprecated"]


@router.get("/asset-types")
async def get_asset_types() -> List[str]:
    """
    Returns available asset types.
    """
    return ASSET_TYPES


@router.get("/categories")
async def get_categories() -> List[str]:
    """
    Returns available categories.
    """
    return CATEGORIES


@router.get("/subcategories")
async def get_subcategories(category: Optional[str] = Query(default=None)) -> List[str]:
    """
    Returns subcategories, optionally filtered by category.
    """
    if category:
        return SUBCATEGORIES.get(category, [])
    
    all_subcategories = []
    for subs in SUBCATEGORIES.values():
        all_subcategories.extend(subs)
    return list(set(all_subcategories))


@router.get("/scaling-potentials")
async def get_scaling_potentials() -> List[str]:
    """
    Returns available scaling potentials.
    """
    return SCALING_POTENTIALS


@router.get("/license-types")
async def get_license_types() -> List[str]:
    """
    Returns available license types.
    """
    return LICENSE_TYPES


@router.get("/climate-zones")
async def get_climate_zones() -> List[str]:
    """
    Returns available climate zones.
    """
    return CLIMATE_ZONES


@router.get("/submission-statuses")
async def get_submission_statuses() -> List[str]:
    """
    Returns available submission statuses.
    """
    return SUBMISSION_STATUSES


@router.get("/system-statuses")
async def get_system_statuses() -> List[str]:
    """
    Returns available system statuses.
    """
    return SYSTEM_STATUSES
