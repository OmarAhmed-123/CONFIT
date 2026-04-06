"""
CONFIT Backend — Chatbot Router
===============================
API endpoints for fashion recommendation chatbot with multiple-choice questions.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.session import get_db
from database.models import Product
import json
import random

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


class QuestionOption(BaseModel):
    id: str
    text: str
    value: Any


class Question(BaseModel):
    id: str
    text: str
    type: str  # "single_choice", "multiple_choice", "range"
    options: Optional[List[QuestionOption]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class RecommendationRequest(BaseModel):
    answers: Dict[str, Any]


class RecommendationResponse(BaseModel):
    products: List[Dict[str, Any]]
    explanation: str


QUESTIONS = [
    {
        "id": "skin_type",
        "text": "What is your skin tone?",
        "type": "single_choice",
        "options": [
            {"id": "fair", "text": "Fair", "value": "fair"},
            {"id": "light", "text": "Light", "value": "light"},
            {"id": "medium", "text": "Medium", "value": "medium"},
            {"id": "tan", "text": "Tan", "value": "tan"},
            {"id": "deep", "text": "Deep", "value": "deep"},
        ],
    },
    {
        "id": "gender",
        "text": "What is your gender?",
        "type": "single_choice",
        "options": [
            {"id": "male", "text": "Male", "value": "male"},
            {"id": "female", "text": "Female", "value": "female"},
        ],
    },
    {
        "id": "age",
        "text": "What is your age group?",
        "type": "single_choice",
        "options": [
            {"id": "18-24", "text": "18-24", "value": "young"},
            {"id": "25-34", "text": "25-34", "value": "adult"},
            {"id": "35-44", "text": "35-44", "value": "mature"},
            {"id": "45+", "text": "45+", "value": "senior"},
        ],
    },
    {
        "id": "occasion",
        "text": "What occasion are you dressing for?",
        "type": "single_choice",
        "options": [
            {"id": "casual", "text": "Casual everyday", "value": "casual"},
            {"id": "work", "text": "Work/Office", "value": "work"},
            {"id": "party", "text": "Party/Event", "value": "party"},
            {"id": "formal", "text": "Formal occasion", "value": "formal"},
            {"id": "sports", "text": "Sports/Active", "value": "sports"},
        ],
    },
    {
        "id": "style_preference",
        "text": "What style do you prefer?",
        "type": "single_choice",
        "options": [
            {"id": "classic", "text": "Classic", "value": "classic"},
            {"id": "modern", "text": "Modern", "value": "modern"},
            {"id": "streetwear", "text": "Streetwear", "value": "streetwear"},
            {"id": "elegant", "text": "Elegant", "value": "elegant"},
            {"id": "casual", "text": "Casual", "value": "casual"},
        ],
    },
    {
        "id": "budget",
        "text": "What is your budget range?",
        "type": "single_choice",
        "options": [
            {"id": "low", "text": "Under $50", "value": {"min": 0, "max": 50}},
            {"id": "medium", "text": "$50-$150", "value": {"min": 50, "max": 150}},
            {"id": "high", "text": "$150-$300", "value": {"min": 150, "max": 300}},
            {"id": "premium", "text": "Over $300", "value": {"min": 300, "max": 10000}},
        ],
    },
]


def get_mock_products():
    """Generate mock products for recommendations."""
    mock_products = [
        {
            "id": "prod-1",
            "name": "Silk Blouse",
            "description": "Elegant silk blouse perfect for formal occasions",
            "category": "tops",
            "price": 89.99,
            "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop",
            "tags": ["elegant", "formal", "work"],
        },
        {
            "id": "prod-2", 
            "name": "Tailored Trousers",
            "description": "Professional tailored trousers for office wear",
            "category": "bottoms",
            "price": 129.99,
            "image_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop",
            "tags": ["formal", "work", "classic"],
        },
        {
            "id": "prod-3",
            "name": "Midi Dress",
            "description": "Versatile midi dress for any occasion",
            "category": "dresses", 
            "price": 149.99,
            "image_url": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop",
            "tags": ["elegant", "party", "casual"],
        },
        {
            "id": "prod-4",
            "name": "Leather Jacket",
            "description": "Edgy leather jacket for street style",
            "category": "outerwear",
            "price": 299.99,
            "image_url": "https://images.unsplash.com/photo-1544923246-77307dd628b8?w=400&h=500&fit=crop",
            "tags": ["streetwear", "modern", "casual"],
        },
        {
            "id": "prod-5",
            "name": "Ankle Boots",
            "description": "Stylish ankle boots for all seasons",
            "category": "shoes",
            "price": 119.99,
            "image_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop",
            "tags": ["casual", "modern", "elegant"],
        },
        {
            "id": "prod-6",
            "name": "Crossbody Bag",
            "description": "Functional crossbody bag for daily use",
            "category": "bags",
            "price": 79.99,
            "image_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&h=500&fit=crop",
            "tags": ["casual", "modern", "practical"],
        },
        {
            "id": "prod-7",
            "name": "Cashmere Sweater",
            "description": "Luxurious cashmere sweater for comfort",
            "category": "tops",
            "price": 189.99,
            "image_url": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop",
            "tags": ["casual", "comfort", "elegant"],
        },
        {
            "id": "prod-8",
            "name": "Wide-Leg Pants",
            "description": "Trendy wide-leg pants for fashion-forward look",
            "category": "bottoms",
            "price": 99.99,
            "image_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&h=500&fit=crop",
            "tags": ["modern", "streetwear", "casual"],
        },
    ]
    return mock_products


def get_recommendations(answers: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
    """Enhanced recommendation engine using mock data."""
    all_products = get_mock_products()
    
    # Filter by budget
    budget = answers.get("budget", {})
    if isinstance(budget, dict):
        min_price = budget.get("min", 0)
        max_price = budget.get("max", 10000)
        filtered = [p for p in all_products if min_price <= p["price"] <= max_price]
    else:
        filtered = all_products
    
    # Score products based on preferences
    occasion = answers.get("occasion")
    style = answers.get("style_preference")
    gender = answers.get("gender")
    
    scored_products = []
    for product in filtered:
        score = 0
        
        # Occasion matching
        if occasion:
            if occasion == "work" and any(tag in product["tags"] for tag in ["formal", "work", "classic"]):
                score += 3
            elif occasion == "casual" and any(tag in product["tags"] for tag in ["casual", "comfort"]):
                score += 3
            elif occasion == "party" and any(tag in product["tags"] for tag in ["elegant", "party"]):
                score += 3
            elif occasion == "formal" and any(tag in product["tags"] for tag in ["formal", "elegant"]):
                score += 3
            elif occasion == "sports" and any(tag in product["tags"] for tag in ["casual", "comfort"]):
                score += 3
        
        # Style preference matching
        if style:
            if style in product["tags"]:
                score += 2
        
        # Add some randomness for variety
        score += random.random()
        
        scored_products.append((product, score))
    
    # Sort by score and return top recommendations
    scored_products.sort(key=lambda x: x[1], reverse=True)
    return [product for product, score in scored_products[:6]]


@router.get("/questions", response_model=List[Question])
async def get_questions():
    """Get all chatbot questions."""
    return [Question(**q) for q in QUESTIONS]


@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations_endpoint(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """Get product recommendations based on answers."""
    products = get_recommendations(request.answers, db)
    
    # Generate personalized explanation
    occasion = request.answers.get("occasion", "")
    style = request.answers.get("style_preference", "")
    budget = request.answers.get("budget", {})
    
    explanations = []
    if occasion:
        occasion_map = {
            "work": "professional work environment",
            "casual": "everyday casual wear", 
            "party": "special party occasions",
            "formal": "formal events",
            "sports": "active and sporty lifestyle"
        }
        explanations.append(f"perfect for {occasion_map.get(occasion, 'your chosen occasion')}")
    
    if style:
        style_map = {
            "classic": "timeless classic style",
            "modern": "contemporary modern fashion",
            "streetwear": "trendy streetwear looks", 
            "elegant": "elegant sophisticated appearance",
            "casual": "relaxed casual vibe"
        }
        explanations.append(f"matches your {style_map.get(style, 'style preference')}")
    
    if isinstance(budget, dict):
        max_price = budget.get("max", 10000)
        if max_price < 100:
            explanations.append("within your budget-friendly range")
        elif max_price < 200:
            explanations.append("fitting your mid-range budget")
        else:
            explanations.append("matching your premium budget preferences")
    
    explanation = f"Based on your preferences, I've selected items that are {', '.join(explanations)}. These pieces will work perfectly for your wardrobe!"
    
    return RecommendationResponse(
        products=products,
        explanation=explanation,
    )
