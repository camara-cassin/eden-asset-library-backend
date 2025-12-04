"""migrate_categories_to_array_structure

Revision ID: 682f67f0d218
Revises: e4beac9e1745
Create Date: 2025-12-04 23:34:53.088201

This migration converts existing assets from the legacy single-category structure
to the new multi-category array structure.

Old structure:
  basic_information.category: "Energy"
  basic_information.subcategory: "Solar"

New structure:
  basic_information.categories: [
    {"primary": "Energy and Heat", "subcategories": ["Solar (PV panels, thermal collectors)"]}
  ]
  basic_information.category: "Energy and Heat"  # Kept for backwards compat
"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision: str = '682f67f0d218'
down_revision: Union[str, Sequence[str], None] = 'e4beac9e1745'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Migration mapping from old categories to new primary categories
CATEGORY_MIGRATION_MAP = {
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

# Subcategory migration mapping (old subcategory -> new subcategory within new primary)
SUBCATEGORY_MIGRATION_MAP = {
    # Energy -> Energy and Heat
    "Solar": "Solar (PV panels, thermal collectors)",
    "Wind": "Wind Turbines",
    "Hydro": "Hydroelectric Systems",
    "Biomass": "Biogas and Biomass",
    "Geothermal": "Heating and Cooling Systems",
    "Storage": "Batteries and Energy Storage",
    "Grid": "Micro-grids and Controllers",
    "Efficiency": "Energy Distribution and Wiring",
    # Water -> Water, Air and Climate
    "Purification": "Water Filtration and Purification",
    "Collection": "Water Collection (rainwater, fog nets, wells)",
    "Distribution": "Irrigation Systems",
    "Irrigation": "Irrigation Systems",
    "Desalination": "Water Filtration and Purification",
    # Food & Agriculture -> Food Systems and Agriculture
    "Farming": "Growing Systems (raised beds, greenhouses, indoor)",
    "Aquaculture": "Aquaponics and Hydroponics",
    "Livestock": "Livestock and Animal Husbandry",
    "Processing": "Food Processing and Preservation",
}


def upgrade() -> None:
    """Migrate existing assets to new category structure."""
    bind = op.get_bind()
    session = Session(bind=bind)
    
    # Get all assets
    result = session.execute(sa.text("SELECT id, data, category FROM eden_assets"))
    assets = result.fetchall()
    
    for asset_id, data, old_category in assets:
        if data is None:
            continue
        
        # Parse JSON data
        if isinstance(data, str):
            asset_data = json.loads(data)
        else:
            asset_data = data
        
        basic_info = asset_data.get("basic_information", {})
        
        # Skip if already has new categories structure
        if basic_info.get("categories") and len(basic_info.get("categories", [])) > 0:
            continue
        
        # Get old category and subcategory
        legacy_category = basic_info.get("category") or old_category
        legacy_subcategory = basic_info.get("subcategory")
        
        if not legacy_category:
            continue
        
        # Map to new category
        new_primary = CATEGORY_MIGRATION_MAP.get(legacy_category, legacy_category)
        
        # Map subcategory if exists
        new_subcategories = []
        if legacy_subcategory:
            new_sub = SUBCATEGORY_MIGRATION_MAP.get(legacy_subcategory)
            if new_sub:
                new_subcategories.append(new_sub)
        
        # Create new categories array
        new_categories = [{
            "primary": new_primary,
            "subcategories": new_subcategories
        }]
        
        # Update basic_information
        basic_info["categories"] = new_categories
        basic_info["category"] = new_primary  # Update legacy field too
        asset_data["basic_information"] = basic_info
        
        # Update the asset
        session.execute(
            sa.text("UPDATE eden_assets SET data = :data, category = :category WHERE id = :id"),
            {"data": json.dumps(asset_data), "category": new_primary, "id": asset_id}
        )
    
    session.commit()


def downgrade() -> None:
    """Revert to legacy single-category structure."""
    bind = op.get_bind()
    session = Session(bind=bind)
    
    # Reverse mapping
    REVERSE_CATEGORY_MAP = {v: k for k, v in CATEGORY_MIGRATION_MAP.items()}
    
    # Get all assets
    result = session.execute(sa.text("SELECT id, data FROM eden_assets"))
    assets = result.fetchall()
    
    for asset_id, data in assets:
        if data is None:
            continue
        
        # Parse JSON data
        if isinstance(data, str):
            asset_data = json.loads(data)
        else:
            asset_data = data
        
        basic_info = asset_data.get("basic_information", {})
        categories = basic_info.get("categories", [])
        
        if not categories:
            continue
        
        # Get first category
        first_cat = categories[0] if categories else {}
        new_primary = first_cat.get("primary", "")
        
        # Map back to old category
        old_category = REVERSE_CATEGORY_MAP.get(new_primary, new_primary)
        
        # Update basic_information - remove categories array
        basic_info["category"] = old_category
        if "categories" in basic_info:
            del basic_info["categories"]
        asset_data["basic_information"] = basic_info
        
        # Update the asset
        session.execute(
            sa.text("UPDATE eden_assets SET data = :data, category = :category WHERE id = :id"),
            {"data": json.dumps(asset_data), "category": old_category, "id": asset_id}
        )
    
    session.commit()
