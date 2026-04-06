"""
CONFIT Backend — Product Service
==================================
In-memory product catalog mirroring the frontend's mockData.ts structure.
"""

import logging
import json
import os
import random
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Data ───────────────────────────────────────────────────────────

PRODUCT_IMAGES = {
    "tops": [
        "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop",
    ],
    "bottoms": [
        "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&h=500&fit=crop",
    ],
    "dresses": [
        "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400&h=500&fit=crop",
    ],
    "outerwear": [
        "https://images.unsplash.com/photo-1544923246-77307dd628b8?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&h=500&fit=crop",
    ],
    "shoes": [
        "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1560343090-f0409e92791a?w=400&h=500&fit=crop",
    ],
    "accessories": [
        "https://images.unsplash.com/photo-1611923134239-b9be5816f80d?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1523779105320-d1cd346ff52b?w=400&h=500&fit=crop",
    ],
    "bags": [
        "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&h=500&fit=crop",
        "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&h=500&fit=crop",
    ],
}

CATEGORIES = list(PRODUCT_IMAGES.keys())

# ── Data Expansion ──────────────────────────────────────────────────

BRANDS = [
    # International / High-End
    "Gucci", "Prada", "Versace", "Balenciaga", "Saint Laurent", "Burberry", 
    "Louis Vuitton", "Dior", "Chanel", "Hermès", "Fendi", "Valentino", 
    "Givenchy", "Bottega Veneta", "Alexander McQueen", "Tom Ford", "Off-White",
    "Ralph Lauren", "Calvin Klein", "Tommy Hilfiger", "Hugo Boss", "Armani Exchange",
    
    # Streetwear / Trendy
    "Supreme", "Stüssy", "Palace", "Fear of God", "A Bathing Ape", "Kith", 
    "Carhartt WIP", "Stone Island", "Nike", "Adidas Originals", "Puma Select",
    "New Balance", "Vans Vault", "Converse Chuck 70", "Obey", "Huf",

    # Sustainable / Ethical
    "Patagonia", "Reformation", "Everlane", "Stella McCartney", "Eileen Fisher",
    "Veja", "Allbirds", "Outerknown", "Pact", "Tentree",

    # Fast Fashion / High Street
    "Zara", "H&M", "Uniqlo", "Massimo Dutti", "Mango", "Cos", "Arket", 
    "Other Stories", "Topshop", "Urban Outfitters", "ASOS Design", "Boohoo",
    
    # Local / Boutique (Fictional)
    "CONFIT Essentials", "Maison Élégance", "UrbanPulse", "Atelier Noir",
    "Vogue Milano", "Nordic Minimal", "Casa Bella", "The Heritage Co.",
    "LuxeLayers", "Velvet & Vine", "EcoThread", "Cairo Cotton Co.", "Nile Threads"
]

COLORS = [
    {"name": "Black", "hex": "#0D0D0D"}, {"name": "White", "hex": "#FAFAFA"},
    {"name": "Navy", "hex": "#1E3A5F"}, {"name": "Charcoal", "hex": "#36454F"},
    {"name": "Beige", "hex": "#F5F5DC"}, {"name": "Camel", "hex": "#C19A6B"},
    {"name": "Olive", "hex": "#556B2F"}, {"name": "Burgundy", "hex": "#800020"},
    {"name": "Red", "hex": "#FF0000"}, {"name": "Royal Blue", "hex": "#4169E1"},
    {"name": "Emerald", "hex": "#50C878"}, {"name": "Pink", "hex": "#FFC0CB"},
    {"name": "Gold", "hex": "#FFD700"}, {"name": "Silver", "hex": "#C0C0C0"},
    {"name": "Teal", "hex": "#008080"}, {"name": "Mustard", "hex": "#FFDB58"},
]

PRODUCT_NAMES = {
    "tops": [
        "Silk Blouse", "Cashmere Sweater", "Linen Shirt", "Knit Turtleneck", 
        "Cotton Tee", "Blazer Top", "Oversized Hoodie", "Graphic T-Shirt",
        "Polo Shirt", "Oxford Button-Down", "Crop Top", "Tank Top", 
        "Cardigan", "V-Neck Sweater", "Crew Neck Sweatshirt"
    ],
    "bottoms": [
        "Tailored Trousers", "Wide-Leg Pants", "Pencil Skirt", "Denim Jeans", 
        "Culottes", "Pleated Skirt", "Cargo Pants", "Chino Shorts", 
        "Joggers", "Leggings", "Midi Skirt", "A-Line Skirt", 
        "Bermuda Shorts", "Track Pants", "Corduroy Pants"
    ],
    "dresses": [
        "Midi Dress", "Evening Gown", "Wrap Dress", "Shirt Dress", 
        "Cocktail Dress", "Maxi Dress", "Mini Dress", "Sundress", 
        "Bodycon Dress", "Slip Dress", "Kaftan", "Tunic Dress"
    ],
    "outerwear": [
        "Wool Coat", "Trench Coat", "Leather Jacket", "Blazer", 
        "Puffer Jacket", "Cardigan", "Denim Jacket", "Bomber Jacket", 
        "Parka", "Raincoat", "Peacoat", "Fleece Jacket", "Windbreaker"
    ],
    "shoes": [
        "Leather Loafers", "Ankle Boots", "Stiletto Heels", "Sneakers", 
        "Ballet Flats", "Oxford Shoes", "Running Shoes", "Sandals", 
        "Chelsea Boots", "Espadrilles", "Mules", "Platform Boots"
    ],
    "accessories": [
        "Silk Scarf", "Leather Belt", "Statement Earrings", "Watch", 
        "Sunglasses", "Hair Clip", "Fedora Hat", "Beanie", 
        "Necklace", "Bracelet", "Tie", "Cufflinks"
    ],
    "bags": [
        "Tote Bag", "Crossbody Bag", "Clutch", "Shoulder Bag", 
        "Backpack", "Satchel", "Messenger Bag", "Duffel Bag", 
        "Wristlet", "Fanny Pack"
    ],
}

# ── Service ────────────────────────────────────────────────────────

class ProductService:
    """Generates and serves an in-memory product catalog with gender and brand isolation."""

    def __init__(self):
        self._products: list[dict] = []
        dataset_path = os.getenv("PRODUCT_DATASET_PATH")
        if dataset_path:
            try:
                with open(dataset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and all(isinstance(x, dict) for x in data):
                    self._products = data
                    logger.info("Loaded product dataset from %s (%d items)", dataset_path, len(self._products))
                else:
                    raise ValueError("Dataset JSON must be a list[dict]")
            except Exception as e:
                logger.warning("Failed to load PRODUCT_DATASET_PATH=%s (%s). Falling back to synthetic catalog.", dataset_path, e)
                self._generate_products()
        else:
            self._generate_products()
        logger.info(f"Product catalog initialized with {len(self._products)} items")

    def _generate_products(self):
        random.seed(42)  # Reproducible
        product_id = 1

        # Generate a massive dataset (5000+ items for comprehensive testing)
        for _ in range(100):  # Generate 5000+ products
            for category in CATEGORIES:
                names = PRODUCT_NAMES.get(category, [])
                images = PRODUCT_IMAGES.get(category, [])

                for index, name in enumerate(names):
                    brand_name = random.choice(BRANDS)
                    brand_id = f"brand-{brand_name.lower().replace(' ', '-').replace('&', 'and')}"
                    
                    # Cost and Pricing logic
                    base_cost = random.randint(20, 200)
                    markup = random.uniform(1.5, 3.5) # 50% to 250% markup
                    if brand_name in ["Gucci", "Prada", "Versace", "Louis Vuitton", "Chanel"]:
                        markup = random.uniform(5.0, 10.0) # Luxury markup
                    
                    price = int(base_cost * markup)
                    has_discount = random.random() > 0.8
                    discount_price = int(price * 0.8) if has_discount else price
                    
                    # Inventory Logic
                    stock_qty = random.randint(0, 150)
                    sold_count = random.randint(0, 500)
                    
                    # Gender Logic
                    # Some items are gendered by name typically, but we'll randomize for now with bias
                    gender_roll = random.random()
                    if "Dress" in name or "Skirt" in name or "Blouse" in name or "Heels" in name:
                        gender = "women"
                    elif "Polo" in name or "Oxford" in name or "Tie" in name:
                        gender = "men" if gender_roll > 0.1 else "women" # small chance of women wearing oxford style
                    else:
                        if gender_roll < 0.45:
                            gender = "women"
                        elif gender_roll < 0.90:
                            gender = "men"
                        else:
                            gender = "unisex"

                    num_colors = random.randint(1, 6)
                    product_colors = random.sample(COLORS, k=min(num_colors, len(COLORS)))
                    color_names = [c["name"] for c in product_colors]

                    sizes = (
                        ["36", "37", "38", "39", "40", "41", "42", "43", "44", "45"]
                        if category == "shoes"
                        else ["XS", "S", "M", "L", "XL", "XXL"]
                    )
                    
                    image_url = images[index % len(images)] if images else "https://placehold.co/400x500?text=No+Image"

                    self._products.append({
                        "id": f"prod-{product_id}",
                        "name": name,
                        "brand": brand_name,
                        "brandId": brand_id,
                        "gender": gender,
                        "price": discount_price,
                        "originalPrice": price if has_discount else None,
                        "costPrice": base_cost, # Private field for analytics
                        "currency": "USD",
                        "category": category,
                        "subcategory": name.lower(),
                        "images": [image_url],
                        "colors": color_names,
                        "sizes": sizes,
                        "description": (
                            f"The {name} from {brand_name} represents the pinnacle of style and comfort. "
                            f"Designed for the modern individual, it features premium materials and a timeless silhouette. "
                            f"Perfect for {'casual outings' if category == 'tops' else 'any occasion'}."
                        ),
                        "styleCompatibility": random.randint(60, 99),
                        "inStock": stock_qty > 0,
                        "stockQuantity": stock_qty,
                        "soldCount": sold_count,
                        "tags": [category, brand_name.lower().replace(" ", "-"), gender] + [c.lower() for c in color_names],
                        "createdAt": datetime.now().isoformat(), # For "New Arrivals"
                    })
                    product_id += 1

    def get_all(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        brand_id: Optional[str] = None,
        gender: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        in_stock_only: bool = False,
    ) -> list[dict]:
        results = list(self._products)

        if query:
            terms = query.lower().split()
            results = [
                p for p in results
                if all(
                    term in f"{p['name']} {p['brand']} {p['description']} {' '.join(p['tags'])}".lower()
                    for term in terms
                )
            ]

        if category:
            results = [p for p in results if p["category"] == category]

        if brand:
            results = [p for p in results if p["brand"] == brand]
            
        if brand_id:
            results = [p for p in results if p.get("brandId") == brand_id]

        if gender:
            # If requesting 'men', show men + unisex
            # If requesting 'women', show women + unisex
            if gender == 'men':
                results = [p for p in results if p.get("gender") in ['men', 'unisex']]
            elif gender == 'women':
                results = [p for p in results if p.get("gender") in ['women', 'unisex']]
            else:
                results = [p for p in results if p.get("gender") == gender]

        if price_min is not None:
            results = [p for p in results if p["price"] >= price_min]

        if price_max is not None:
            results = [p for p in results if p["price"] <= price_max]

        if in_stock_only:
            results = [p for p in results if p["inStock"]]

        return results

    def get_by_id(self, product_id: str) -> Optional[dict]:
        # Direct match
        for p in self._products:
            if p["id"] == product_id:
                return p

        # Handle numeric IDs
        if product_id.isdigit():
            prefixed = f"prod-{product_id}"
            for p in self._products:
                if p["id"] == prefixed:
                    return p

        return None

    def get_featured(self, limit: int = 8, gender: Optional[str] = None) -> list[dict]:
        filtered = self._products
        if gender:
             if gender == 'men':
                filtered = [p for p in filtered if p.get("gender") in ['men', 'unisex']]
             elif gender == 'women':
                filtered = [p for p in filtered if p.get("gender") in ['women', 'unisex']]
        
        return sorted(
            filtered,
            key=lambda p: p["styleCompatibility"],
            reverse=True,
        )[:limit]

    def get_trending(self, limit: int = 6, gender: Optional[str] = None) -> list[dict]:
        filtered = self._products
        if gender:
             if gender == 'men':
                filtered = [p for p in filtered if p.get("gender") in ['men', 'unisex']]
             elif gender == 'women':
                filtered = [p for p in filtered if p.get("gender") in ['women', 'unisex']]

        on_sale = [p for p in filtered if p["originalPrice"] is not None]
        return on_sale[:limit]

    def get_brands(self) -> list[str]:
        return list(set(p["brand"] for p in self._products))

    def get_categories(self) -> list[str]:
        return CATEGORIES

    # ── CRUD Operations ────────────────────────────────────────────────
    
    def create(self, product_data: dict) -> dict:
        new_id = f"prod-{len(self._products) + 1000}" # Simple ID generation
        
        # Ensure defaults
        new_product = {
            "id": new_id,
            "createdAt": datetime.now().isoformat(),
            **product_data
        }
        
        # Basic validation/normalization could go here
        if "styleCompatibility" not in new_product:
             import random
             new_product["styleCompatibility"] = random.randint(60, 99)
             
        self._products.append(new_product)
        return new_product

    def update(self, product_id: str, updates: dict) -> Optional[dict]:
        product = self.get_by_id(product_id)
        if not product:
            return None
            
        # Update fields
        for key, value in updates.items():
            if key != "id": # Prevent ID change
                product[key] = value
        
        product["updatedAt"] = datetime.now().isoformat()
        return product

    def delete(self, product_id: str) -> bool:
        product = self.get_by_id(product_id)
        if not product:
            return False
            
        self._products.remove(product)
        return True
