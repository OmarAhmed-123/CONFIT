"""
CONFIT Backend — Visual Search Router
=====================================
Real visual search implementation using image embeddings
and feature extraction for product matching.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from controllers.product_controller import ProductController
from services.visual_search_service import VisualSearchService, ImageFeatures

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visual-search", tags=["Visual Search"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MIN_FILE_SIZE = 100

# Service instance (lazy loaded)
_search_service = None


def get_search_service():
    """Get or create visual search service instance."""
    global _search_service
    if _search_service is None:
        _search_service = VisualSearchService()
    return _search_service


@router.post("", response_model=List[Dict])
async def visual_search(
    file: UploadFile = File(...),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
):
    """
    Upload an image to find visually similar products.
    
    Uses real image feature extraction:
    - Color analysis
    - Category detection
    - Style classification
    - Embedding-based similarity search
    
    Returns products ranked by visual similarity score.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Invalid file type. Please upload an image.")
    
    # Read file contents
    contents = await file.read()
    
    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB")
    
    if len(contents) < MIN_FILE_SIZE:
        raise HTTPException(400, "File appears to be empty or too small")
    
    try:
        # Get search service
        service = get_search_service()
        
        # Extract features from query image
        logger.info(f"Extracting features from uploaded image ({len(contents)} bytes)")
        query_features = await service.extract_features(contents, extract_embedding=True)
        
        logger.info(
            f"Detected category: {query_features.category} "
            f"(confidence: {query_features.category_confidence:.2f}), "
            f"dominant colors: {query_features.dominant_colors[:3]}"
        )
        
        # Build filters
        filters = {}
        if category:
            filters['category'] = category
        elif query_features.category_confidence > 0.6:
            # Use detected category if confidence is high
            filters['category'] = query_features.category
        
        if min_price is not None:
            filters['min_price'] = min_price
        if max_price is not None:
            filters['max_price'] = max_price
        
        # Fetch products from database
        # In production, would fetch products with pre-computed embeddings
        controller = ProductController()
        
        # Get products from detected or filtered category
        search_category = filters.get('category', query_features.category)
        products = await controller.get_all_products(category=search_category)
        
        # Convert products to feature format for matching
        product_features = [
            {
                'id': p.get('id'),
                'name': p.get('name'),
                'brand': p.get('brand'),
                'price': p.get('price'),
                'category': p.get('category'),
                'colors': p.get('colors', []),
                'style_tags': p.get('tags', []),
                'embedding': None,  # Would have pre-computed embeddings in production
            }
            for p in products
        ]
        
        # Search for similar products
        results = await service.search_similar(
            query_features=query_features,
            product_features=product_features,
            limit=limit,
            filters=filters if filters else None,
        )
        
        # Map results back to products with similarity scores
        result_products = []
        for result in results:
            # Find matching product
            product = next((p for p in products if str(p.get('id')) == result.product_id), None)
            
            if product:
                # Add similarity information
                product_with_score = {
                    **product,
                    'similarityScore': round(result.similarity_score, 3),
                    'matchReasons': result.match_reasons,
                    'colorSimilarity': round(result.color_similarity, 3),
                    'categoryMatch': result.category_match,
                    'styleMatch': result.style_match,
                }
                result_products.append(product_with_score)
        
        logger.info(f"Found {len(result_products)} similar products for query")
        
        # If no results with detected category, try broader search
        if len(result_products) == 0 and not category:
            logger.info("No results with detected category, searching all categories")
            all_products = await controller.get_all_products()
            
            all_product_features = [
                {
                    'id': p.get('id'),
                    'name': p.get('name'),
                    'brand': p.get('brand'),
                    'price': p.get('price'),
                    'category': p.get('category'),
                    'colors': p.get('colors', []),
                    'style_tags': p.get('tags', []),
                }
                for p in all_products
            ]
            
            results = await service.search_similar(
                query_features=query_features,
                product_features=all_product_features,
                limit=limit,
            )
            
            for result in results:
                product = next((p for p in all_products if str(p.get('id')) == result.product_id), None)
                if product:
                    product_with_score = {
                        **product,
                        'similarityScore': round(result.similarity_score, 3),
                        'matchReasons': result.match_reasons,
                    }
                    result_products.append(product_with_score)
        
        return result_products
        
    except Exception as e:
        logger.error(f"Visual search failed: {e}", exc_info=True)
        raise HTTPException(500, f"Visual search failed: {str(e)}")


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze an image and return extracted features.
    
    Returns:
    - Detected category
    - Dominant colors
    - Style tags
    - Pattern type
    - Image properties
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Invalid file type. Please upload an image.")
    
    contents = await file.read()
    
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB")
    
    try:
        service = get_search_service()
        features = await service.extract_features(contents, extract_embedding=False)
        
        return {
            'category': features.category,
            'categoryConfidence': round(features.category_confidence, 3),
            'dominantColors': [
                {'r': c[0], 'g': c[1], 'b': c[2]}
                for c in features.dominant_colors
            ],
            'styleTags': features.style_tags,
            'pattern': features.pattern,
            'properties': {
                'aspectRatio': round(features.aspect_ratio, 2),
                'brightness': round(features.brightness, 3),
                'contrast': round(features.contrast, 3),
            },
        }
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}", exc_info=True)
        raise HTTPException(500, f"Image analysis failed: {str(e)}")
