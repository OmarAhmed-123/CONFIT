"""
CONFIT Backend — Database Seed
===============================
Creates default brands, stores, and quests when the database is empty.
Run after init_db() so that list and create operations have data to work with.
"""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from database.models import Brand, Store, Quest, Product

logger = logging.getLogger(__name__)

DEFAULT_BRANDS = [
    {"name": "LuxeLayers", "description": "Contemporary fashion for the modern minimalist."},
    {"name": "UrbanPulse", "description": "Streetwear essentials for the bold."},
    {"name": "EcoThread", "description": "Sustainable clothing made with care."},
    {"name": "Velvet & Vine", "description": "Elegant evening wear and formal attire."},
]

DEFAULT_STORES = [
    {
        "name": "CONFIT Flagship - NY",
        "brand_slug": "luxelayers",
        "store_slug": "confit-flagship-ny",
        "address": "123 Fashion Ave",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "postal_code": "10012",
        "location": {"lat": 40.7128, "lng": -74.0060},
        "services": ["BOPIS", "Stylist", "Alterations"],
        "hours": {"Mon-Fri": "10am-9pm", "Sat-Sun": "11am-7pm"},
    },
    {
        "name": "CONFIT Downtown - LA",
        "brand_slug": "luxelayers",
        "store_slug": "confit-downtown-la",
        "address": "456 Style Blvd",
        "city": "Los Angeles",
        "state": "CA",
        "country": "USA",
        "postal_code": "90015",
        "location": {"lat": 34.0522, "lng": -118.2437},
        "services": ["BOPIS", "Returns"],
        "hours": {"Mon-Fri": "10am-9pm", "Sat-Sun": "11am-7pm"},
    },
]

DEFAULT_PRODUCTS = [
    {
        "name": "Classic White Shirt",
        "description": "Timeless white button-up shirt",
        "category": "shirt",
        "subcategory": "button-up",
        "color": "white",
        "size": "M",
        "price": 89.99,
        "brand_slug": "luxelayers",
        "store_slug": "confit-flagship-ny",
        "image_url": "/images/products/white-shirt.jpg",
        "tags": ["casual", "formal", "neutral"],
    },
    {
        "name": "Slim Fit Jeans",
        "description": "Comfortable slim fit denim jeans",
        "category": "pants",
        "subcategory": "jeans",
        "color": "blue",
        "size": "32",
        "price": 129.99,
        "brand_slug": "urbanpulse",
        "store_slug": "confit-downtown-la",
        "image_url": "/images/products/slim-jeans.jpg",
        "tags": ["casual", "streetwear"],
    },
    {
        "name": "Evening Gown",
        "description": "Elegant black evening gown",
        "category": "dress",
        "subcategory": "evening",
        "color": "black",
        "size": "S",
        "price": 299.99,
        "brand_slug": "velvet-vine",
        "store_slug": "confit-flagship-ny",
        "image_url": "/images/products/evening-gown.jpg",
        "tags": ["formal", "evening", "elegant"],
    },
    {
        "name": "Eco Hoodie",
        "description": "Sustainable organic cotton hoodie",
        "category": "jacket",
        "subcategory": "hoodie",
        "color": "gray",
        "size": "L",
        "price": 79.99,
        "brand_slug": "ecothread",
        "store_slug": "confit-downtown-la",
        "image_url": "/images/products/eco-hoodie.jpg",
        "tags": ["casual", "sustainable", "comfort"],
    },
]

DEFAULT_QUESTS = [
    {
        "title": "First Look",
        "description": "Create your first outfit in the Outfit Builder.",
        "type": "milestone",
        "reward_points": 150,
        "reward_badge": "creator",
        "icon": "✨",
        "constraint_json": {},
    },
    {
        "title": "Mindful Monday",
        "description": "Style a complete look using only items already in your wardrobe.",
        "type": "weekly",
        "reward_points": 200,
        "reward_badge": "sustainista",
        "icon": "♻️",
        "constraint_json": {"wardrobe_only": True},
    },
    {
        "title": "Budget Stylist",
        "description": "Build a full outfit under $100.",
        "type": "daily",
        "reward_points": 100,
        "reward_badge": None,
        "icon": "💸",
        "constraint_json": {"max_budget": 100},
    },
    {
        "title": "AI Explorer",
        "description": "Use the Virtual Try-On feature for the first time.",
        "type": "milestone",
        "reward_points": 250,
        "reward_badge": "early_adopter",
        "icon": "🤖",
        "constraint_json": {},
    },
    {
        "title": "Rainy Day Edit",
        "description": "Style a look for a rainy day under $150.",
        "type": "daily",
        "reward_points": 120,
        "reward_badge": None,
        "icon": "🌧️",
        "constraint_json": {"max_budget": 150, "occasion": "casual"},
    },
    {
        "title": "Digital Twin Debut",
        "description": "Generate your first Digital Twin.",
        "type": "milestone",
        "reward_points": 300,
        "reward_badge": "trendsetter",
        "icon": "🪞",
        "constraint_json": {},
    },
    {
        "title": "Store Scout",
        "description": "Scan a QR code in a physical store.",
        "type": "milestone",
        "reward_points": 200,
        "reward_badge": "explorer",
        "icon": "📱",
        "constraint_json": {},
    },
    {
        "title": "Style Streak",
        "description": "Log an outfit 7 days in a row.",
        "type": "weekly",
        "reward_points": 500,
        "reward_badge": "streak_master",
        "icon": "🔥",
        "constraint_json": {"days": 7},
    },
]


def seed_brands_and_stores(db: Session) -> None:
    """Insert default brands, stores, and quests if none exist. Idempotent."""
    if db.query(Brand).count() > 0:
        return

    now = datetime.utcnow()
    brand_ids: dict[str, str] = {}
    store_ids: dict[str, str] = {}

    for b in DEFAULT_BRANDS:
        b_id = f"brand-{b['name'].lower().replace(' ', '-')}"
        brand_ids[b["name"].lower().replace(" ", "-")] = b_id
        db.add(
            Brand(
                id=b_id,
                name=b["name"],
                description=b["description"],
                created_at=now,
                updated_at=now,
            )
        )

    db.commit()

    for s in DEFAULT_STORES:
        brand_id = brand_ids.get(s["brand_slug"], list(brand_ids.values())[0] if brand_ids else None)
        if not brand_id:
            continue
        s_id = str(uuid.uuid4())
        store_ids[s["store_slug"]] = s_id
        db.add(
            Store(
                id=s_id,
                brand_id=brand_id,
                name=s["name"],
                address=s["address"],
                city=s["city"],
                state=s["state"],
                country=s["country"],
                postal_code=s["postal_code"],
                location=s["location"],
                services=s["services"],
                hours=s["hours"],
            )
        )

    db.commit()

    # Seed quests
    for q in DEFAULT_QUESTS:
        q_id = str(uuid.uuid4())
        db.add(
            Quest(
                id=q_id,
                title=q["title"],
                description=q["description"],
                type=q["type"],
                reward_points=q["reward_points"],
                reward_badge=q["reward_badge"],
                icon=q["icon"],
                constraint_json=q["constraint_json"],
                is_active=True,
                expires_at=now + timedelta(days=30) if q["type"] == "weekly" else None,
                created_at=now,
            )
        )

    db.commit()

    # Seed products
    for p in DEFAULT_PRODUCTS:
        brand_id = brand_ids.get(p["brand_slug"])
        store_id = store_ids.get(p["store_slug"])
        if not brand_id or not store_id:
            continue
        p_id = str(uuid.uuid4())
        db.add(
            Product(
                id=p_id,
                name=p["name"],
                description=p["description"],
                category=p["category"],
                subcategory=p["subcategory"],
                color=p["color"],
                size=p["size"],
                price=p["price"],
                brand_id=brand_id,
                store_id=store_id,
                image_url=p["image_url"],
                tags=p["tags"],
                is_active=True,
                created_at=now,
            )
        )

    db.commit()
    logger.info("Seeded %s brands, %s stores, %s quests, and %s products", len(DEFAULT_BRANDS), len(DEFAULT_STORES), len(DEFAULT_QUESTS), len(DEFAULT_PRODUCTS))
