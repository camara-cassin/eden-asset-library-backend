from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

router = APIRouter()

ASSET_TYPES = ["physical", "plan", "hybrid"]

# New hierarchical category structure with 9 primary categories
CATEGORY_HIERARCHY: Dict[str, List[str]] = {
    "Shelter and Buildings": [
        "Modular Housing Units",
        "Building Components (walls, roofs, foundations)",
        "Structural Systems",
        "Insulation and Weatherproofing",
        "Doors, Windows and Openings",
        "Interior Finishes",
        "Building Plans and Blueprints",
    ],
    "Energy and Heat": [
        "Solar (PV panels, thermal collectors)",
        "Wind Turbines",
        "Hydroelectric Systems",
        "Biogas and Biomass",
        "Batteries and Energy Storage",
        "Heating and Cooling Systems",
        "Energy Distribution and Wiring",
        "Micro-grids and Controllers",
    ],
    "Water, Air and Climate": [
        "Water Collection (rainwater, fog nets, wells)",
        "Water Storage (tanks, ponds, cisterns)",
        "Water Filtration and Purification",
        "Greywater and Blackwater Systems",
        "Irrigation Systems",
        "Water Pump",
        "Air Quality and Ventilation",
        "Climate Control Systems",
        "Humidity Management",
    ],
    "Food Systems and Agriculture": [
        "Growing Systems (raised beds, greenhouses, indoor)",
        "Aquaponics and Hydroponics",
        "Composting Systems",
        "Seeds and Planting Materials",
        "Livestock and Animal Husbandry",
        "Food Processing and Preservation",
        "Agricultural Tools and Equipment",
        "Permaculture Elements",
    ],
    "Waste, Recycling and Bioprocessing": [
        "Composting Toilets",
        "Biogas Digesters",
        "Recycling Equipment",
        "Waste Sorting Systems",
        "Biochar Production",
        "Mushroom Cultivation",
        "Vermicomposting",
        "Waste-to-Energy Systems",
    ],
    "Tools, Fabrication and Manufacturing": [
        "Hand Tools",
        "Power Tools",
        "CNC and Digital Fabrication",
        "3D Printers",
        "Welding and Metalworking",
        "Woodworking Equipment",
        "Electronics and Prototyping",
        "Workshop Infrastructure",
    ],
    "Mobility and Transport": [
        "Bicycles and E-bikes",
        "Electric Vehicles",
        "Cargo and Utility Vehicles",
        "Boats and Watercraft",
        "Paths and Infrastructure",
        "Charging Stations",
    ],
    "Household and Personal Items": [
        "Cookware and Kitchen Equipment",
        "Furniture",
        "Lighting",
        "Textiles and Clothing",
        "Storage Solutions",
        "Personal Care Items",
        "Communication Devices",
    ],
    "Health, Sanitation and Care": [
        "Medical Equipment and Supplies",
        "Hygiene Products",
        "Sanitation Systems",
        "First Aid and Emergency",
        "Wellness and Fitness",
        "Childcare Equipment",
        "Elderly Care Equipment",
    ],
}

# Category badge colors for frontend reference
CATEGORY_COLORS: Dict[str, str] = {
    "Shelter and Buildings": "amber",
    "Energy and Heat": "yellow",
    "Water, Air and Climate": "blue",
    "Food Systems and Agriculture": "green",
    "Waste, Recycling and Bioprocessing": "purple",
    "Tools, Fabrication and Manufacturing": "gray",
    "Mobility and Transport": "red",
    "Household and Personal Items": "pink",
    "Health, Sanitation and Care": "teal",
}

# Legacy flat lists for backwards compatibility
CATEGORIES = list(CATEGORY_HIERARCHY.keys())

SUBCATEGORIES = CATEGORY_HIERARCHY  # Alias for backwards compat

# Migration mapping from old categories to new
CATEGORY_MIGRATION_MAP: Dict[str, str] = {
    "Energy": "Energy and Heat",
    "Water": "Water, Air and Climate",
    "Food & Agriculture": "Food Systems and Agriculture",
    "Shelter & Construction": "Shelter and Buildings",
    "Waste Management": "Waste, Recycling and Bioprocessing",
    "Transportation": "Mobility and Transport",
    "Health & Sanitation": "Health, Sanitation and Care",
    "Communication": "Household and Personal Items",
    "Education": "Tools, Fabrication and Manufacturing",
    "Manufacturing": "Tools, Fabrication and Manufacturing",
}


class CategoryItem(BaseModel):
    """A single category with its subcategories."""
    primary: str
    subcategories: List[str]
    color: str


class CategoriesResponse(BaseModel):
    """Response model for hierarchical categories endpoint."""
    categories: List[CategoryItem]

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
async def get_categories() -> CategoriesResponse:
    """
    Returns available categories with their subcategories and colors.
    Returns hierarchical structure for multi-category selection.
    """
    categories = [
        CategoryItem(
            primary=primary,
            subcategories=subcategories,
            color=CATEGORY_COLORS.get(primary, "gray")
        )
        for primary, subcategories in CATEGORY_HIERARCHY.items()
    ]
    return CategoriesResponse(categories=categories)


@router.get("/categories/flat")
async def get_categories_flat() -> List[str]:
    """
    Returns flat list of primary category names (legacy endpoint).
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
