#!/usr/bin/env python3
"""
Seed script for EDEN Asset Library.
Creates three example assets: one physical, one plan, and one hybrid.
Also creates an initial admin user if INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD are set.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.database import Base
from app.services.asset_service import create_asset
from app.models.user import User, UserRole


PHYSICAL_ASSET = {
    "asset_type": "physical",
    "basic_information": {
        "category": "Energy",
        "subcategory": "Solar",
        "asset_name": "Solar Roof Tile X100",
        "short_summary": "Modular solar roof tile system for residential and commercial buildings",
        "function_purpose": "Generate clean electricity from sunlight while serving as roofing material",
        "scaling_potential": "global",
        "long_description": "The Solar Roof Tile X100 is an innovative building-integrated photovoltaic (BIPV) solution that combines the functionality of traditional roofing materials with solar energy generation. Each tile is designed to seamlessly integrate with standard roofing systems while providing maximum energy output.",
        "company_name": "SolarTech Industries",
        "company_email": "info@solartech.example.com",
        "company_website_url": "https://solartech.example.com",
        "creator_name": "Dr. Sarah Chen",
        "creator_organization": "SolarTech R&D",
        "certifications": ["IEC 61215", "UL 1703", "ISO 9001"],
        "year_introduced_or_updated": "2024"
    },
    "contributor": {
        "name": "Jane Scout",
        "email": "jane@example.org",
        "contributor_id": "user_001",
        "submission_status": "draft"
    },
    "overview": {
        "photos": ["https://example.com/photos/solar-tile-1.jpg", "https://example.com/photos/solar-tile-2.jpg"],
        "key_features": [
            "High efficiency monocrystalline cells",
            "Weather resistant tempered glass",
            "Easy snap-lock installation",
            "25-year warranty",
            "Integrated micro-inverter option"
        ],
        "intended_use_cases": [
            "Residential rooftop solar",
            "Commercial building integration",
            "New construction projects",
            "Roof replacement with solar upgrade"
        ],
        "asset_type_description": "Building-integrated photovoltaic roofing tile"
    },
    "physical_configuration": {
        "unit_variants": [
            {
                "unit_name": "Standard Tile",
                "unit_of_analysis": "single tile",
                "dimensions": {
                    "length": 1140,
                    "width": 420,
                    "height": 25
                },
                "footprint_area": 0.48,
                "unit_weight": 5.2,
                "package_size": "6 tiles per box",
                "package_weight": 32,
                "stackability_notes": "Stack up to 4 boxes high",
                "modular_interfaces": ["Snap-lock edge connector", "MC4 electrical connector"],
                "operating_range": {
                    "min_temperature": -40,
                    "max_temperature": 85,
                    "min_humidity": 0,
                    "max_humidity": 100
                },
                "scalability_notes": "Tiles can be combined in any quantity to match roof size"
            }
        ]
    },
    "functional_io": {
        "inputs": [
            {"name": "Solar Irradiance", "type": "energy", "unit": "W/m2", "description": "Sunlight energy input"},
            {"name": "Roof Area", "type": "space", "unit": "m2", "description": "Available installation area"}
        ],
        "outputs": [
            {"name": "Electrical Power", "type": "energy", "unit": "W", "description": "DC electrical output per tile (peak)"},
            {"name": "Annual Energy", "type": "energy", "unit": "kWh/year", "description": "Expected annual energy production per tile"}
        ]
    },
    "economics": {
        "retail_price": 350,
        "currency": "USD",
        "price_notes": "Price per tile, bulk discounts available",
        "estimated_lifespan_years": 30,
        "maintenance_cost_annual": 5,
        "roi_notes": "Typical payback period of 7-10 years depending on local electricity rates and incentives"
    },
    "deployment": {
        "climate_zones": ["3", "4", "5", "6"],
        "terrain_types": ["Urban", "Suburban", "Rural"],
        "infrastructure_requirements": ["Grid connection", "Inverter system", "Mounting hardware"],
        "deployment_notes": "Professional installation recommended. Compatible with most roof pitches between 15-45 degrees."
    },
    "eden_impact_summary": {
        "eden_positive_impact_points": 87,
        "eden_recommended_rating": "A",
        "impact_categories": ["Clean Energy", "Carbon Reduction", "Building Efficiency"],
        "impact_notes": "High positive impact due to clean energy generation and building integration"
    }
}


PLAN_ASSET = {
    "asset_type": "plan",
    "basic_information": {
        "category": "Water",
        "subcategory": "Purification",
        "asset_name": "DIY Biosand Water Filter",
        "short_summary": "Open-source plans for building a household biosand water filter",
        "function_purpose": "Purify contaminated water for safe drinking using biological and physical filtration",
        "scaling_potential": "local",
        "long_description": "The DIY Biosand Water Filter is a proven, low-cost water treatment technology that can be built using locally available materials. It uses layers of sand and gravel to filter water through biological and physical processes, removing pathogens and turbidity.",
        "creator_name": "Clean Water Initiative",
        "creator_organization": "Global Water Foundation",
        "creator_email": "plans@cleanwater.example.org",
        "original_source_url": "https://cleanwater.example.org/biosand-filter",
        "attribution_text": "Based on CAWST Biosand Filter design",
        "certifications": ["WHO Approved Technology"],
        "year_introduced_or_updated": "2023"
    },
    "contributor": {
        "name": "Mark Builder",
        "email": "mark@example.org",
        "contributor_id": "user_002",
        "submission_status": "draft"
    },
    "overview": {
        "photos": ["https://example.com/photos/biosand-1.jpg"],
        "key_features": [
            "No electricity required",
            "Uses locally available materials",
            "Low maintenance",
            "Removes 90-99% of pathogens",
            "Long operational lifespan"
        ],
        "intended_use_cases": [
            "Household water treatment",
            "Community water points",
            "Emergency water supply",
            "Off-grid living"
        ],
        "asset_type_description": "Construction plans for biological sand water filter"
    },
    "plan_configuration": {
        "build_complexity_score": 3,
        "tool_complexity_score": 2,
        "required_skill_level": "Intermediate",
        "required_skills": [
            "Basic construction",
            "Concrete mixing",
            "Plumbing basics"
        ],
        "required_tools": [
            "Shovel",
            "Bucket",
            "Trowel",
            "Level",
            "Measuring tape",
            "PVC pipe cutter"
        ],
        "estimated_build_time_hours": 8,
        "annual_maintenance_time_hours": 4,
        "repair_time_hours": 2
    },
    "documentation_uploads": {
        "build_manual_url": "https://example.com/docs/biosand-manual.pdf",
        "step_by_step_instructions_url": "https://example.com/docs/biosand-steps.pdf",
        "bom_url": "https://example.com/docs/biosand-bom.pdf"
    },
    "economics": {
        "retail_price": 50,
        "currency": "USD",
        "price_notes": "Estimated material cost, varies by location",
        "estimated_lifespan_years": 20,
        "maintenance_cost_annual": 5,
        "roi_notes": "Saves approximately $200/year compared to bottled water"
    },
    "deployment": {
        "climate_zones": ["Tropical", "Temperate", "Dry"],
        "terrain_types": ["Urban", "Rural", "Remote"],
        "infrastructure_requirements": ["Water source", "Level ground"],
        "deployment_notes": "Filter must be used daily to maintain biological layer. Not suitable for freezing conditions."
    },
    "eden_impact_summary": {
        "eden_positive_impact_points": 92,
        "eden_recommended_rating": "A+",
        "impact_categories": ["Clean Water", "Health", "Poverty Reduction"],
        "impact_notes": "Extremely high impact for communities without access to clean water"
    }
}


HYBRID_ASSET = {
    "asset_type": "hybrid",
    "basic_information": {
        "category": "Food & Agriculture",
        "subcategory": "Farming",
        "asset_name": "Modular Aquaponics System Kit",
        "short_summary": "Complete kit and plans for building a backyard aquaponics system",
        "function_purpose": "Produce fish and vegetables in a closed-loop sustainable system",
        "scaling_potential": "regional",
        "long_description": "The Modular Aquaponics System Kit combines physical components with detailed construction plans to enable anyone to build a productive aquaponics system. The system uses fish waste to fertilize plants, which in turn filter the water for the fish, creating a sustainable food production cycle.",
        "company_name": "AquaGrow Systems",
        "company_email": "support@aquagrow.example.com",
        "company_website_url": "https://aquagrow.example.com",
        "creator_name": "Dr. Michael Waters",
        "creator_organization": "AquaGrow R&D",
        "certifications": ["Organic Compatible", "Food Safe Materials"],
        "year_introduced_or_updated": "2024"
    },
    "contributor": {
        "name": "Lisa Farmer",
        "email": "lisa@example.org",
        "contributor_id": "user_003",
        "submission_status": "draft"
    },
    "overview": {
        "photos": ["https://example.com/photos/aquaponics-1.jpg", "https://example.com/photos/aquaponics-2.jpg"],
        "key_features": [
            "Modular expandable design",
            "Food-grade materials included",
            "Detailed assembly instructions",
            "Water quality monitoring guide",
            "Starter fish and plant recommendations"
        ],
        "intended_use_cases": [
            "Backyard food production",
            "Educational demonstrations",
            "Urban farming",
            "Restaurant fresh produce"
        ],
        "asset_type_description": "Physical kit with construction plans for aquaponics system"
    },
    "physical_configuration": {
        "unit_variants": [
            {
                "unit_name": "Starter Kit",
                "unit_of_analysis": "complete system",
                "dimensions": {
                    "length": 2400,
                    "width": 1200,
                    "height": 1800
                },
                "footprint_area": 2.88,
                "volume": 5.18,
                "unit_weight": 45,
                "package_size": "2 boxes",
                "package_weight": 52,
                "stackability_notes": "Do not stack, fragile components",
                "modular_interfaces": ["Standard garden hose", "12V DC power"],
                "operating_range": {
                    "min_temperature": 15,
                    "max_temperature": 35,
                    "min_humidity": 30,
                    "max_humidity": 80
                },
                "scalability_notes": "Additional grow bed modules available for expansion"
            }
        ]
    },
    "plan_configuration": {
        "build_complexity_score": 4,
        "tool_complexity_score": 3,
        "required_skill_level": "Intermediate",
        "required_skills": [
            "Basic plumbing",
            "Electrical connections",
            "Assembly from instructions"
        ],
        "required_tools": [
            "Screwdriver set",
            "Adjustable wrench",
            "Level",
            "Drill",
            "Silicone sealant gun"
        ],
        "estimated_build_time_hours": 6,
        "annual_maintenance_time_hours": 24,
        "repair_time_hours": 2
    },
    "functional_io": {
        "inputs": [
            {"name": "Fish Feed", "type": "material", "unit": "kg/month", "description": "Fish food input"},
            {"name": "Electricity", "type": "energy", "unit": "kWh/month", "description": "Power for pump and aeration"},
            {"name": "Water", "type": "material", "unit": "L/month", "description": "Top-up water for evaporation"}
        ],
        "outputs": [
            {"name": "Fish", "type": "food", "unit": "kg/year", "description": "Harvestable fish production"},
            {"name": "Vegetables", "type": "food", "unit": "kg/year", "description": "Vegetable production"}
        ]
    },
    "economics": {
        "retail_price": 899,
        "currency": "USD",
        "price_notes": "Complete starter kit including all components",
        "estimated_lifespan_years": 15,
        "maintenance_cost_annual": 150,
        "roi_notes": "Produces approximately $500-800 worth of food annually after first year"
    },
    "deployment": {
        "climate_zones": ["3", "4", "5", "Temperate"],
        "terrain_types": ["Urban", "Suburban"],
        "infrastructure_requirements": ["Outdoor space or greenhouse", "Water supply", "Electrical outlet"],
        "deployment_notes": "Best results in greenhouse or climate-controlled environment. Can be used outdoors in temperate climates."
    },
    "eden_impact_summary": {
        "eden_positive_impact_points": 78,
        "eden_recommended_rating": "A",
        "impact_categories": ["Food Security", "Water Conservation", "Sustainable Agriculture"],
        "impact_notes": "Uses 90% less water than traditional farming while producing both protein and vegetables"
    }
}


async def seed_admin_user(session: AsyncSession):
    """Create initial admin user if env vars are set and no admin exists."""
    if not settings.INITIAL_ADMIN_EMAIL or not settings.INITIAL_ADMIN_PASSWORD:
        print("INITIAL_ADMIN_EMAIL or INITIAL_ADMIN_PASSWORD not set, skipping admin user creation")
        return
    
    # Check if admin already exists
    result = await session.execute(
        select(User).where(User.role == UserRole.admin)
    )
    existing_admin = result.scalar_one_or_none()
    
    if existing_admin:
        print(f"Admin user already exists: {existing_admin.email}")
        return
    
    # Create admin user
    admin_user = User(
        name="Admin",
        email=settings.INITIAL_ADMIN_EMAIL,
        password_hash=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
        role=UserRole.admin
    )
    session.add(admin_user)
    await session.commit()
    await session.refresh(admin_user)
    print(f"Created admin user: {admin_user.email} (ID: {admin_user.id})")


async def seed_database():
    """Create example assets and admin user in the database."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Seed admin user first
        print("=== Seeding Admin User ===")
        await seed_admin_user(session)
        
        print("\n=== Seeding Assets ===")
        print("Creating Physical Asset: Solar Roof Tile X100...")
        physical_asset, errors = await create_asset(session, PHYSICAL_ASSET)
        if errors:
            print(f"  Errors: {errors}")
        else:
            print(f"  Created with ID: {physical_asset.id}, Asset ID: {physical_asset.asset_id}")
        
        print("\nCreating Plan Asset: DIY Biosand Water Filter...")
        plan_asset, errors = await create_asset(session, PLAN_ASSET)
        if errors:
            print(f"  Errors: {errors}")
        else:
            print(f"  Created with ID: {plan_asset.id}, Asset ID: {plan_asset.asset_id}")
        
        print("\nCreating Hybrid Asset: Modular Aquaponics System Kit...")
        hybrid_asset, errors = await create_asset(session, HYBRID_ASSET)
        if errors:
            print(f"  Errors: {errors}")
        else:
            print(f"  Created with ID: {hybrid_asset.id}, Asset ID: {hybrid_asset.asset_id}")
    
    await engine.dispose()
    print("\nSeed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
