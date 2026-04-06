"""
CONFIT Backend — Products Router
===============================
API endpoints for product catalog, search, and recommendations.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.session import get_db
from database.models import Product
from services.fashion_catalog import fetch_dummyjson_fashion_sync, fetch_dummyjson_product_by_id_sync

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["products"])

# When DB rows have no image or only broken relative paths, serve stable HTTPS thumbnails
_CATEGORY_FALLBACK_IMAGE: dict[str, str] = {
    "tops": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop",
    "bottoms": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop",
    "dresses": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop",
    "outerwear": "https://images.unsplash.com/photo-1544923246-77307dd628b8?w=400&h=500&fit=crop",
    "shoes": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop",
    "accessories": "https://images.unsplash.com/photo-1611923134239-b9be5816f80d?w=400&h=500&fit=crop",
    "bags": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&h=500&fit=crop",
}


def _ensure_image_list(category: str, images: list, image_url: Optional[str]) -> list[str]:
    """Prefer absolute https URLs; otherwise use a category placeholder (avoids empty / broken relative URLs)."""
    out: list[str] = []
    for u in images or []:
        s = str(u).strip() if u else ""
        if s.startswith(("http://", "https://")):
            out.append(s)
    if not out and image_url:
        s = str(image_url).strip()
        if s.startswith(("http://", "https://")):
            out.append(s)
    if not out:
        cat = (category or "tops").lower()
        out = [_CATEGORY_FALLBACK_IMAGE.get(cat, _CATEGORY_FALLBACK_IMAGE["tops"])]
    return out


class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    gender: Optional[str] = "unisex"
    color: Optional[str]
    size: Optional[str]
    price: float
    brand: Optional[str] = None
    brandId: Optional[str] = None
    store_id: Optional[str]
    images: List[str] = []
    image_url: Optional[str]
    tags: Optional[List[str]]
    inStock: bool = True
    is_active: bool = True
    styleCompatibility: int = 85
    created_at: str


@router.get("/featured", response_model=List[ProductResponse])
async def get_featured_products(
    limit: int = Query(default=12, le=50),
    gender: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Get featured products with optional gender filter."""
    logger.info(f"Fetching featured products: limit={limit}, gender={gender}")
    
    try:
        # Try to get from database first
        query = db.query(Product).filter(Product.is_active == True)
        
        # Apply gender filter if provided
        if gender and gender in ['men', 'women']:
            query = query.filter(Product.tags.contains([gender]))
        
        # Order by style compatibility and limit
        products = query.order_by(Product.style_compatibility.desc()).limit(limit).all()
        
        if products:
            logger.info(f"Found {len(products)} products in database")
            return [
                ProductResponse(
                    id=str(p.id),
                    name=p.name,
                    description=p.description,
                    category=p.category,
                    gender=p.tags[0] if p.tags and len(p.tags) > 0 else "unisex",
                    color=p.color,
                    size=p.size,
                    price=p.price,
                    brand=None,
                    brandId=str(p.brand_id) if p.brand_id else None,
                    store_id=str(p.store_id) if p.store_id else None,
                    images=_ensure_image_list(
                        p.category,
                        [p.image_url] if p.image_url else [],
                        p.image_url,
                    ),
                    image_url=_ensure_image_list(
                        p.category,
                        [p.image_url] if p.image_url else [],
                        p.image_url,
                    )[0],
                    tags=p.tags,
                    inStock=p.is_active,
                    is_active=p.is_active,
                    styleCompatibility=p.style_compatibility or 85,
                    created_at=p.created_at.isoformat(),
                )
                for p in products
            ]
    except Exception as e:
        logger.warning(f"Database query failed, using mock data: {e}")
    
    # Fallback to mock data + DummyJSON fashion (same as list fallback)
    mock_products = fetch_dummyjson_fashion_sync(limit_total=min(50, limit * 3)) + _get_mock_products()
    
    # Filter by gender if provided
    if gender and gender in ['men', 'women']:
        mock_products = [p for p in mock_products if p.get('gender') == gender or p.get('gender') == 'unisex']
    
    # Return limited number of products
    featured = mock_products[:limit]
    logger.info(f"Returning {len(featured)} mock products")
    
    return [
        ProductResponse(
            id=str(p['id']),
            name=p['name'],
            description=p.get('description', ''),
            category=p.get('category', 'tops'),
            gender=p.get('gender', 'unisex'),
            color=p.get('color'),
            size=p.get('size'),
            price=p.get('price', 50.0),
            brand=None,
            brandId=p.get('brandId'),
            store_id=None,
            images=p.get('images', []),
            image_url=(p.get('image_url') or (p['images'][0] if p.get('images') else None)),
            tags=p.get('tags', []),
            inStock=p.get('inStock', True),
            is_active=p.get('inStock', True),
            styleCompatibility=85,
            created_at=p.get('created_at', "2024-01-01T00:00:00Z"),
        )
        for p in featured
    ]


def _get_mock_products():
    """Generate mock products for fallback."""
    return [
        {
            'id': '1', 'name': 'Classic White T-Shirt', 'description': 'Premium cotton t-shirt',
            'category': 'tops', 'price': 45.0, 'gender': 'unisex',
            'images': ['https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop&q=80'],
            'tags': ['basics', 'cotton'], 'inStock': True, 'brandId': 'brand-1'
        },
        {
            'id': '2', 'name': 'Slim Fit Jeans', 'description': 'Comfortable stretch jeans',
            'category': 'bottoms', 'price': 89.0, 'gender': 'unisex',
            'images': ['https://images.unsplash.com/photo-1542272604-787c4734df0b?w=400'],
            'tags': ['denim', 'casual'], 'inStock': True, 'brandId': 'brand-2'
        },
        {
            'id': '3', 'name': 'Summer Floral Dress', 'description': 'Light and breezy summer dress',
            'category': 'dresses', 'price': 75.0, 'gender': 'women',
            'images': ['https://images.unsplash.com/photo-1572804013309-106a932f4cb5?w=400'],
            'tags': ['summer', 'floral'], 'inStock': True, 'brandId': 'brand-1'
        },
        {
            'id': '4', 'name': 'Leather Bomber Jacket', 'description': 'Classic leather jacket',
            'category': 'outerwear', 'price': 199.0, 'gender': 'men',
            'images': ['https://images.unsplash.com/photo-1551028719-0f8e62890308?w=400'],
            'tags': ['leather', 'winter'], 'inStock': True, 'brandId': 'brand-3'
        },
        {
            'id': '5', 'name': 'Athletic Running Shorts', 'description': 'Breathable running shorts',
            'category': 'bottoms', 'price': 35.0, 'gender': 'unisex',
            'images': ['https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop&q=80'],
            'tags': ['sports', 'athletic'], 'inStock': True, 'brandId': 'brand-4'
        },
        {
            'id': '6', 'name': 'Wool Blend Sweater', 'description': 'Cozy winter sweater',
            'category': 'tops', 'price': 85.0, 'gender': 'unisex',
            'images': ['https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop&q=80'],
            'tags': ['wool', 'winter'], 'inStock': True, 'brandId': 'brand-2'
        },
        {
            'id': '7', 'name': 'Pleated Midi Skirt', 'description': 'Elegant pleated skirt',
            'category': 'bottoms', 'price': 65.0, 'gender': 'women',
            'images': ['https://images.unsplash.com/photo-1583496661160-fb5883a2a3b3?w=400'],
            'tags': ['elegant', 'formal'], 'inStock': True, 'brandId': 'brand-1'
        },
        {
            'id': '8', 'name': 'Casual Linen Shirt', 'description': 'Lightweight linen shirt',
            'category': 'tops', 'price': 55.0, 'gender': 'men',
            'images': ['https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400'],
            'tags': ['linen', 'summer'], 'inStock': True, 'brandId': 'brand-3'
        },
        {
            'id': '9', 'name': 'Yoga Leggings', 'description': 'High-waist yoga leggings',
            'category': 'bottoms', 'price': 68.0, 'gender': 'women',
            'images': ['https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400'],
            'tags': ['yoga', 'fitness'], 'inStock': True, 'brandId': 'brand-4'
        },
        {
            'id': '10', 'name': 'Denim Jacket', 'description': 'Classic denim jacket',
            'category': 'outerwear', 'price': 95.0, 'gender': 'unisex',
            'images': ['https://images.unsplash.com/photo-1576995824980-14e0871cbfa2?w=400'],
            'tags': ['denim', 'casual'], 'inStock': True, 'brandId': 'brand-2'
        },
        {
            'id': '11', 'name': 'Silk Evening Dress', 'description': 'Luxurious silk dress',
            'category': 'dresses', 'price': 180.0, 'gender': 'women',
            'images': ['https://images.unsplash.com/photo-1566174043889-054b8e4f1a59?w=400'],
            'tags': ['silk', 'evening'], 'inStock': True, 'brandId': 'brand-1'
        },
        {
            'id': '12', 'name': 'Chino Pants', 'description': 'Classic chino pants',
            'category': 'bottoms', 'price': 72.0, 'gender': 'men',
            'images': ['https://images.unsplash.com/photo-1473966968600-fa801c20469a?w=400'],
            'tags': ['chino', 'formal'], 'inStock': True, 'brandId': 'brand-3'
        },
    ]


def _synthetic_product_for_id(product_id: str) -> Optional[ProductResponse]:
    """
    Build a deterministic fallback product for IDs like `prod-304` used by seeded UIs.
    This keeps PDP/cart flows functional when DB rows are not present locally.
    """
    if not product_id:
        return None
    pid = product_id.strip()
    num = None
    if pid.startswith("prod-"):
        raw = pid.replace("prod-", "", 1)
        if raw.isdigit():
            num = int(raw)
    if num is None:
        # Also support UUID-like/string IDs so PDP does not break when upstream catalog IDs
        # come from recommendation/sustainability feeds.
        num = sum(ord(ch) for ch in pid) % 1000

    mock_pool = _get_mock_products()
    base = mock_pool[num % len(mock_pool)]
    price = round(float(base.get("price", 49.0)) + (num % 7) * 2.5, 2)
    return ProductResponse(
        id=pid,
        name=f"{base.get('name', 'CONFIT Product')} #{num}",
        description=base.get("description", "Fashion item"),
        category=base.get("category", "tops"),
        gender=base.get("gender", "unisex"),
        color=base.get("color"),
        size=base.get("size"),
        price=price,
        brand=None,
        brandId=base.get("brandId"),
        store_id=None,
        images=base.get("images", []),
        image_url=(base.get("images", [None])[0] if base.get("images") else None),
        tags=base.get("tags", []),
        inStock=True,
        is_active=True,
        styleCompatibility=85,
        created_at="2024-01-01T00:00:00Z",
    )


@router.get("", response_model=List[ProductResponse])
async def list_products(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List products with optional filters."""
    logger.info(f"Listing products: category={category}, min_price={min_price}, max_price={max_price}, search={search}")
    
    try:
        query = db.query(Product).filter(Product.is_active == True)

        if category:
            query = query.filter(Product.category == category)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))

        products = query.offset(offset).limit(limit).all()
        
        if products:
            logger.info(f"Found {len(products)} products in database")
            return [
                ProductResponse(
                    id=str(p.id),
                    name=p.name,
                    description=p.description,
                    category=p.category,
                    gender=p.tags[0] if p.tags and len(p.tags) > 0 else "unisex",
                    color=p.color,
                    size=p.size,
                    price=p.price,
                    brand=None,
                    brandId=str(p.brand_id) if p.brand_id else None,
                    store_id=str(p.store_id) if p.store_id else None,
                    images=_ensure_image_list(
                        p.category,
                        [p.image_url] if p.image_url else [],
                        p.image_url,
                    ),
                    image_url=_ensure_image_list(
                        p.category,
                        [p.image_url] if p.image_url else [],
                        p.image_url,
                    )[0],
                    tags=p.tags,
                    inStock=p.is_active,
                    is_active=p.is_active,
                    styleCompatibility=p.style_compatibility or 85,
                    created_at=p.created_at.isoformat(),
                )
                for p in products
            ]
    except Exception as e:
        logger.warning(f"Database query failed: {e}")
    
    # Fallback to mock data + optional DummyJSON fashion (real images/prices)
    logger.info("Returning mock products (+ external fashion when enabled)")
    external_fashion = fetch_dummyjson_fashion_sync(limit_total=min(80, limit + offset + 40))
    mock_products = external_fashion + _get_mock_products()
    
    # Apply filters to mock data
    if category:
        mock_products = [p for p in mock_products if p.get('category') == category]
    if min_price is not None:
        mock_products = [p for p in mock_products if p.get('price', 0) >= min_price]
    if max_price is not None:
        mock_products = [p for p in mock_products if p.get('price', 0) <= max_price]
    if search:
        mock_products = [p for p in mock_products if search.lower() in p.get('name', '').lower()]
    
    # Apply pagination
    paginated = mock_products[offset:offset + limit]
    
    return [
        ProductResponse(
            id=str(p['id']),
            name=p['name'],
            description=p.get('description', ''),
            category=p.get('category', 'tops'),
            gender=p.get('gender', 'unisex'),
            color=p.get('color'),
            size=p.get('size'),
            price=p.get('price', 50.0),
            brand=None,
            brandId=p.get('brandId'),
            store_id=None,
            images=p.get('images', []),
            image_url=(p.get('image_url') or (p['images'][0] if p.get('images') else None)),
            tags=p.get('tags', []),
            inStock=p.get('inStock', True),
            is_active=p.get('inStock', True),
            styleCompatibility=85,
            created_at=p.get('created_at', "2024-01-01T00:00:00Z"),
        )
        for p in paginated
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    product = None
    
    try:
        # Convert string ID to UUID for database query
        from uuid import UUID
        try:
            product_uuid = UUID(product_id)
            product = db.query(Product).filter(Product.id == product_uuid, Product.is_active == True).first()
        except ValueError:
            # If not a valid UUID, try as string (for mock data compatibility)
            product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    except Exception as e:
        logger.warning(f"Database query failed for product {product_id}: {e}")
    
    # If not in database, check mock products
    if not product:
        mock_products = _get_mock_products()
        ext = fetch_dummyjson_product_by_id_sync(product_id)
        if ext:
            return ProductResponse(
                id=str(ext['id']),
                name=ext['name'],
                description=ext.get('description', ''),
                category=ext.get('category', 'tops'),
                gender=ext.get('gender', 'unisex'),
                color=ext.get('color'),
                size=ext.get('size'),
                price=ext.get('price', 50.0),
                brand=ext.get('brand'),
                brandId=ext.get('brandId'),
                store_id=ext.get('store_id'),
                images=ext.get('images', []),
                image_url=ext.get('image_url') or (ext['images'][0] if ext.get('images') else None),
                tags=ext.get('tags', []),
                inStock=ext.get('inStock', True),
                is_active=ext.get('is_active', True),
                styleCompatibility=ext.get('styleCompatibility', 85),
                created_at=ext.get('created_at', "2024-01-01T00:00:00Z"),
            )
        for p in mock_products:
            if str(p['id']) == product_id or p['id'] == product_id:
                return ProductResponse(
                    id=str(p['id']),
                    name=p['name'],
                    description=p.get('description', ''),
                    category=p.get('category', 'tops'),
                    gender=p.get('gender', 'unisex'),
                    color=p.get('color'),
                    size=p.get('size'),
                    price=p.get('price', 50.0),
                    brand=None,
                    brandId=p.get('brandId'),
                    store_id=None,
                    images=p.get('images', []),
                    image_url=p['images'][0] if p.get('images') else None,
                    tags=p.get('tags', []),
                    inStock=p.get('inStock', True),
                    is_active=p.get('inStock', True),
                    styleCompatibility=85,
                    created_at="2024-01-01T00:00:00Z",
                )
        
        # Fallback for synthetic IDs like prod-132 used by sustainability/recommendation feeds
        synthetic = _synthetic_product_for_id(product_id)
        if synthetic:
            return synthetic
        
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    imgs = _ensure_image_list(
        product.category,
        [product.image_url] if product.image_url else [],
        product.image_url,
    )
    return ProductResponse(
        id=str(product.id),
        name=product.name,
        description=product.description,
        category=product.category,
        gender=product.tags[0] if product.tags and len(product.tags) > 0 else "unisex",
        color=product.color,
        size=product.size,
        price=product.price,
        brand=None,
        brandId=str(product.brand_id) if product.brand_id else None,
        store_id=str(product.store_id) if product.store_id else None,
        images=imgs,
        image_url=imgs[0],
        tags=product.tags,
        inStock=product.is_active,
        is_active=product.is_active,
        styleCompatibility=product.style_compatibility or 85,
        created_at=product.created_at.isoformat(),
    )

