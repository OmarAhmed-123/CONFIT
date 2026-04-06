"""
CONFIT Backend — Commerce Intelligence Service
==============================================
AI-powered commerce features:
- Smart cart optimization
- Return prediction
- Delivery recommendation
- Purchase confidence scoring
- BNPL eligibility prediction

Integrates with AI Central Brain for personalized commerce decisions.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from collections import defaultdict
import json

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.session import get_db

from models.profile_models import (
    UserBehaviorSignal,
    UserStyleProfile,
    UserBudgetProfile,
    UserBrandAffinity,
)
from database.models import Order, OrderItem, ReturnRequest, Product

logger = logging.getLogger(__name__)


# ── Commerce Intelligence Constants ─────────────────────────────────────

RETURN_RISK_WEIGHTS = {
    "category_risk": {
        "dresses": 0.15,
        "shoes": 0.20,
        "pants": 0.18,
        "tops": 0.08,
        "accessories": 0.05,
        "outerwear": 0.12,
        "activewear": 0.07,
    },
    "price_risk": {
        "high": 0.25,  # >$200
        "medium": 0.15,  # $50-$200
        "low": 0.05,  # <$50
    },
    "brand_risk": {
        "unknown": 0.10,
        "known": 0.05,
        "preferred": 0.02,
    },
    "history_risk": {
        "high_return_rate": 0.30,
        "medium_return_rate": 0.15,
        "low_return_rate": 0.05,
    },
}

DELIVERY_PREFERENCES = {
    "standard": {
        "days": "5-7",
        "cost_multiplier": 1.0,
        "eco_score": 0.9,
    },
    "express": {
        "days": "2-3",
        "cost_multiplier": 2.17,  # ~$12.99 vs $5.99
        "eco_score": 0.5,
    },
    "overnight": {
        "days": "1",
        "cost_multiplier": 4.17,  # ~$24.99 vs $5.99
        "eco_score": 0.2,
    },
    "pickup": {
        "days": "0-1",
        "cost_multiplier": 0,
        "eco_score": 1.0,
    },
}

BNPL_THRESHOLDS = {
    "eligible": {
        "min_confidence": 50,
        "max_risk_score": 30,
        "min_order_value": 35,
        "max_order_value": 1000,
    },
    "review_required": {
        "min_confidence": 30,
        "max_risk_score": 50,
    },
}

CART_OPTIMIZATION_RULES = {
    "free_shipping_threshold": 100,
    "bundle_discount_threshold": 3,  # items from same brand
    "bundle_discount_rate": 0.10,
    "cross_sell_confidence_threshold": 0.7,
    "abandonment_rescue_discount": 0.15,
}


class CartOptimizationResult:
    """Result of smart cart optimization."""
    
    def __init__(
        self,
        suggestions: List[Dict[str, Any]],
        savings: float,
        free_shipping_gap: float,
        bundle_opportunities: List[Dict[str, Any]],
        cross_sells: List[Dict[str, Any]],
        confidence_boost: float,
    ):
        self.suggestions = suggestions
        self.savings = savings
        self.free_shipping_gap = free_shipping_gap
        self.bundle_opportunities = bundle_opportunities
        self.cross_sells = cross_sells
        self.confidence_boost = confidence_boost
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestions": self.suggestions,
            "savings": round(self.savings, 2),
            "free_shipping_gap": round(self.free_shipping_gap, 2),
            "bundle_opportunities": self.bundle_opportunities,
            "cross_sells": self.cross_sells,
            "confidence_boost": round(self.confidence_boost, 2),
        }


class ReturnPrediction:
    """Return risk prediction for an item or order."""
    
    def __init__(
        self,
        risk_score: float,
        risk_level: str,
        factors: List[Dict[str, Any]],
        recommendations: List[str],
        confidence: float,
    ):
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.factors = factors
        self.recommendations = recommendations
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level,
            "factors": self.factors,
            "recommendations": self.recommendations,
            "confidence": round(self.confidence, 2),
        }


class DeliveryRecommendation:
    """Personalized delivery recommendation."""
    
    def __init__(
        self,
        recommended_method: str,
        alternatives: List[Dict[str, Any]],
        estimated_arrival: str,
        cost: float,
        eco_impact: float,
        reason: str,
    ):
        self.recommended_method = recommended_method
        self.alternatives = alternatives
        self.estimated_arrival = estimated_arrival
        self.cost = cost
        self.eco_impact = eco_impact
        self.reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_method": self.recommended_method,
            "alternatives": self.alternatives,
            "estimated_arrival": self.estimated_arrival,
            "cost": round(self.cost, 2),
            "eco_impact": round(self.eco_impact, 2),
            "reason": self.reason,
        }


class PurchaseConfidence:
    """Purchase confidence score for checkout."""
    
    def __init__(
        self,
        overall_score: float,
        style_alignment: float,
        budget_fit: float,
        size_confidence: float,
        brand_affinity: float,
        occasion_match: float,
        return_risk: float,
        recommendations: List[str],
    ):
        self.overall_score = overall_score
        self.style_alignment = style_alignment
        self.budget_fit = budget_fit
        self.size_confidence = size_confidence
        self.brand_affinity = brand_affinity
        self.occasion_match = occasion_match
        self.return_risk = return_risk
        self.recommendations = recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "dimensions": {
                "style_alignment": round(self.style_alignment, 2),
                "budget_fit": round(self.budget_fit, 2),
                "size_confidence": round(self.size_confidence, 2),
                "brand_affinity": round(self.brand_affinity, 2),
                "occasion_match": round(self.occasion_match, 2),
                "return_risk": round(self.return_risk, 2),
            },
            "recommendations": self.recommendations,
            "confidence_level": self._get_confidence_level(),
        }
    
    def _get_confidence_level(self) -> str:
        if self.overall_score >= 80:
            return "high"
        elif self.overall_score >= 60:
            return "medium"
        elif self.overall_score >= 40:
            return "low"
        return "very_low"


class CommerceIntelligenceService:
    """
    AI-powered commerce intelligence for frictionless purchasing.
    
    Features:
    - Smart cart optimization with bundles and cross-sells
    - Return prediction using historical patterns
    - Personalized delivery recommendations
    - Purchase confidence scoring
    - BNPL eligibility prediction
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    # ── Smart Cart Optimization ─────────────────────────────────────────
    
    def optimize_cart(
        self,
        user_id: str,
        cart_items: List[Dict[str, Any]],
        user_preferences: Dict[str, Any] = None,
    ) -> CartOptimizationResult:
        """
        Analyze cart and provide optimization suggestions.
        
        Features:
        - Free shipping threshold analysis
        - Bundle discount detection
        - Cross-sell recommendations
        - Price optimization
        """
        suggestions = []
        bundle_opportunities = []
        cross_sells = []
        savings = 0.0
        
        subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart_items)
        free_shipping_gap = max(0, CART_OPTIMIZATION_RULES["free_shipping_threshold"] - subtotal)
        
        # Detect bundle opportunities (same brand items)
        brand_items = defaultdict(list)
        for item in cart_items:
            brand = item.get("brand", "unknown")
            brand_items[brand].append(item)
        
        for brand, items in brand_items.items():
            if len(items) >= CART_OPTIMIZATION_RULES["bundle_discount_threshold"]:
                bundle_savings = sum(i.get("price", 0) for i in items) * CART_OPTIMIZATION_RULES["bundle_discount_rate"]
                bundle_opportunities.append({
                    "brand": brand,
                    "item_count": len(items),
                    "potential_savings": round(bundle_savings, 2),
                    "discount_rate": CART_OPTIMIZATION_RULES["bundle_discount_rate"],
                })
                savings += bundle_savings
        
        # Free shipping suggestion
        if free_shipping_gap > 0 and free_shipping_gap <= 30:
            suggestions.append({
                "type": "free_shipping",
                "message": f"Add ${free_shipping_gap:.2f} more for free shipping!",
                "impact": "Save $5.99 on shipping",
                "priority": "high",
            })
        
        # Cross-sell recommendations based on cart contents
        cross_sells = self._generate_cross_sells(user_id, cart_items, user_preferences)
        
        # Calculate confidence boost from optimizations
        confidence_boost = min(20, len(suggestions) * 5 + len(bundle_opportunities) * 10)
        
        return CartOptimizationResult(
            suggestions=suggestions,
            savings=savings,
            free_shipping_gap=free_shipping_gap,
            bundle_opportunities=bundle_opportunities,
            cross_sells=cross_sells,
            confidence_boost=confidence_boost,
        )
    
    def _generate_cross_sells(
        self,
        user_id: str,
        cart_items: List[Dict[str, Any]],
        user_preferences: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """Generate personalized cross-sell recommendations."""
        cross_sells = []
        
        # Get user's style preferences
        style_profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        
        # Analyze cart categories
        cart_categories = set(item.get("category", "") for item in cart_items)
        
        # Suggest complementary categories
        complementary = {
            "tops": ["bottoms", "accessories"],
            "bottoms": ["tops", "shoes"],
            "dresses": ["shoes", "accessories"],
            "shoes": ["accessories", "bags"],
            "outerwear": ["tops", "accessories"],
        }
        
        for category in cart_categories:
            if category in complementary:
                for comp_cat in complementary[category]:
                    if comp_cat not in cart_categories:
                        cross_sells.append({
                            "category": comp_cat,
                            "reason": f"Completes your {category} selection",
                            "confidence": 0.75,
                        })
        
        return cross_sells[:3]  # Limit to top 3
    
    # ── Return Prediction ────────────────────────────────────────────────
    
    def predict_return_risk(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        order_context: Dict[str, Any] = None,
    ) -> ReturnPrediction:
        """
        Predict return probability for order items.
        
        Factors:
        - Category historical return rates
        - Price point risk
        - Brand familiarity
        - User's return history
        - Size confidence
        """
        factors = []
        total_risk = 0.0
        recommendations = []
        
        # Calculate user's historical return rate
        user_return_rate = self._get_user_return_rate(user_id)
        
        if user_return_rate > 0.3:
            factors.append({
                "type": "history",
                "value": f"{user_return_rate:.0%} return rate",
                "impact": "high",
                "weight": RETURN_RISK_WEIGHTS["history_risk"]["high_return_rate"],
            })
            total_risk += RETURN_RISK_WEIGHTS["history_risk"]["high_return_rate"]
        elif user_return_rate > 0.15:
            factors.append({
                "type": "history",
                "value": f"{user_return_rate:.0%} return rate",
                "impact": "medium",
                "weight": RETURN_RISK_WEIGHTS["history_risk"]["medium_return_rate"],
            })
            total_risk += RETURN_RISK_WEIGHTS["history_risk"]["medium_return_rate"]
        else:
            total_risk += RETURN_RISK_WEIGHTS["history_risk"]["low_return_rate"]
        
        # Analyze item-level risks
        for item in items:
            category = item.get("category", "unknown")
            price = item.get("price", 0)
            brand = item.get("brand", "unknown")
            
            # Category risk
            cat_risk = RETURN_RISK_WEIGHTS["category_risk"].get(category, 0.10)
            if cat_risk > 0.10:
                factors.append({
                    "type": "category",
                    "value": category,
                    "impact": "medium" if cat_risk < 0.15 else "high",
                    "weight": cat_risk,
                })
            total_risk += cat_risk
            
            # Price risk
            if price > 200:
                price_risk = RETURN_RISK_WEIGHTS["price_risk"]["high"]
                factors.append({
                    "type": "price",
                    "value": f"${price:.2f}",
                    "impact": "high",
                    "weight": price_risk,
                })
            elif price > 50:
                price_risk = RETURN_RISK_WEIGHTS["price_risk"]["medium"]
            else:
                price_risk = RETURN_RISK_WEIGHTS["price_risk"]["low"]
            total_risk += price_risk
            
            # Brand risk
            brand_affinity = self._get_brand_affinity(user_id, brand)
            if brand_affinity > 0.7:
                brand_risk = RETURN_RISK_WEIGHTS["brand_risk"]["preferred"]
            elif brand_affinity > 0.3:
                brand_risk = RETURN_RISK_WEIGHTS["brand_risk"]["known"]
            else:
                brand_risk = RETURN_RISK_WEIGHTS["brand_risk"]["unknown"]
            total_risk += brand_risk
        
        # Normalize risk score
        risk_score = min(100, (total_risk / len(items)) * 100) if items else 0
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = "high"
            recommendations = [
                "Consider ordering multiple sizes to try at home",
                "Check our size guide for this brand",
                "Virtual try-on available for this item",
            ]
        elif risk_score >= 30:
            risk_level = "medium"
            recommendations = [
                "Review size chart before purchase",
                "Check return policy for this item",
            ]
        else:
            risk_level = "low"
            recommendations = ["Low return risk - confident purchase!"]
        
        confidence = max(0, 100 - risk_score) * 0.8 + 20  # Confidence inversely related to risk
        
        return ReturnPrediction(
            risk_score=risk_score,
            risk_level=risk_level,
            factors=factors,
            recommendations=recommendations,
            confidence=confidence,
        )
    
    def _get_user_return_rate(self, user_id: str) -> float:
        """Calculate user's historical return rate."""
        orders = self._db.query(Order).filter_by(user_id=user_id).all()
        if not orders:
            return 0.0
        
        returns = self._db.query(ReturnRequest).filter_by(user_id=user_id).count()
        total_orders = len(orders)
        
        return returns / total_orders if total_orders > 0 else 0.0
    
    def _get_brand_affinity(self, user_id: str, brand: str) -> float:
        """Get user's affinity score for a brand."""
        affinity = self._db.query(UserBrandAffinity).filter_by(
            user_id=user_id, brand_name=brand
        ).first()
        
        if affinity:
            return float(affinity.affinity_score)
        
        # Check behavior signals for brand interactions
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.entity_type == "brand",
            UserBehaviorSignal.entity_id == brand,
        ).count()
        
        return min(1.0, signals * 0.1)
    
    # ── Delivery Recommendation ─────────────────────────────────────────
    
    def recommend_delivery(
        self,
        user_id: str,
        order_total: float,
        items: List[Dict[str, Any]],
        user_context: Dict[str, Any] = None,
    ) -> DeliveryRecommendation:
        """
        Recommend optimal delivery method based on user patterns.
        
        Factors:
        - Historical delivery preferences
        - Order urgency indicators
        - Eco-consciousness
        - Cost sensitivity
        - Geographic location
        """
        # Get user's delivery history
        delivery_history = self._get_delivery_history(user_id)
        
        # Get user preferences
        budget_profile = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        style_profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        
        # Determine price sensitivity
        price_sensitivity = float(budget_profile.price_sensitivity) if budget_profile and budget_profile.price_sensitivity else 0.5
        
        # Calculate eco-consciousness (from experimentation level)
        eco_conscious = 0.5
        if style_profile:
            eco_conscious = 1 - float(style_profile.style_maximalist or 0.5)
        
        # Score each delivery method
        method_scores = {}
        
        # Standard shipping - good for price-sensitive, eco-conscious
        method_scores["standard"] = {
            "score": 50 + (price_sensitivity * 30) + (eco_conscious * 20),
            "cost": 5.99 if order_total < 100 else 0,
            "days": "5-7",
            "eco_impact": 0.9,
        }
        
        # Express shipping - good for urgent needs
        method_scores["express"] = {
            "score": 40 + ((1 - price_sensitivity) * 20),
            "cost": 12.99,
            "days": "2-3",
            "eco_impact": 0.5,
        }
        
        # Overnight - for urgent occasions
        method_scores["overnight"] = {
            "score": 30 + ((1 - price_sensitivity) * 10),
            "cost": 24.99,
            "days": "1",
            "eco_impact": 0.2,
        }
        
        # Pickup - best for eco-conscious, cost-sensitive
        method_scores["pickup"] = {
            "score": 45 + (price_sensitivity * 25) + (eco_conscious * 30),
            "cost": 0,
            "days": "0-1",
            "eco_impact": 1.0,
        }
        
        # Adjust based on delivery history
        for method, count in delivery_history.items():
            if method in method_scores:
                method_scores[method]["score"] += min(15, count * 3)
        
        # Find best method
        best_method = max(method_scores.items(), key=lambda x: x[1]["score"])
        
        # Build alternatives
        alternatives = []
        for method, data in sorted(method_scores.items(), key=lambda x: x[1]["score"], reverse=True):
            if method != best_method[0]:
                alternatives.append({
                    "method": method,
                    "cost": data["cost"],
                    "days": data["days"],
                    "eco_impact": data["eco_impact"],
                    "score_diff": round(best_method[1]["score"] - data["score"], 1),
                })
        
        # Generate reason
        reason = self._generate_delivery_reason(best_method[0], price_sensitivity, eco_conscious)
        
        return DeliveryRecommendation(
            recommended_method=best_method[0],
            alternatives=alternatives[:2],
            estimated_arrival=self._estimate_arrival(best_method[1]["days"]),
            cost=best_method[1]["cost"],
            eco_impact=best_method[1]["eco_impact"],
            reason=reason,
        )
    
    def _get_delivery_history(self, user_id: str) -> Dict[str, int]:
        """Get user's delivery method history."""
        orders = self._db.query(Order).filter_by(user_id=user_id).limit(20).all()
        
        history = defaultdict(int)
        for order in orders:
            # Infer from shipping cost
            if order.shipping == 0:
                # Could be pickup or free standard
                history["standard"] += 1
            elif order.shipping < 10:
                history["standard"] += 1
            elif order.shipping < 20:
                history["express"] += 1
            else:
                history["overnight"] += 1
        
        return dict(history)
    
    def _estimate_arrival(self, days_range: str) -> str:
        """Calculate estimated arrival date."""
        if "-" in days_range:
            min_days, max_days = map(int, days_range.split("-"))
        else:
            min_days = max_days = int(days_range)
        
        today = datetime.now(timezone.utc)
        min_date = today + timedelta(days=min_days)
        max_date = today + timedelta(days=max_days)
        
        if min_days == max_days:
            return min_date.strftime("%A, %b %d")
        return f"{min_date.strftime('%b %d')} - {max_date.strftime('%b %d')}"
    
    def _generate_delivery_reason(self, method: str, price_sensitivity: float, eco_conscious: float) -> str:
        """Generate personalized reason for delivery recommendation."""
        reasons = {
            "standard": [
                "Best value for your order",
                "Free shipping on orders over $100",
                "Most economical option",
            ],
            "express": [
                "Faster delivery for your needs",
                "Good balance of speed and cost",
            ],
            "overnight": [
                "Fastest delivery available",
                "Get it tomorrow",
            ],
            "pickup": [
                "Free and eco-friendly",
                "Available today at your nearest store",
                "No shipping cost",
            ],
        }
        
        method_reasons = reasons.get(method, ["Recommended for your order"])
        
        if price_sensitivity > 0.7 and method in ["standard", "pickup"]:
            return method_reasons[0]
        if eco_conscious > 0.7 and method in ["pickup", "standard"]:
            return method_reasons[1] if len(method_reasons) > 1 else method_reasons[0]
        
        return method_reasons[0]
    
    # ── Purchase Confidence Score ────────────────────────────────────────
    
    def calculate_purchase_confidence(
        self,
        user_id: str,
        cart_items: List[Dict[str, Any]],
        occasion: str = None,
    ) -> PurchaseConfidence:
        """
        Calculate overall purchase confidence score.
        
        Dimensions:
        - Style alignment: How well items match user's style
        - Budget fit: Price appropriateness
        - Size confidence: Likelihood of correct fit
        - Brand affinity: Familiarity with brands
        - Occasion match: Suitability for intended use
        - Return risk: Inverse of return prediction
        """
        style_profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        budget_profile = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        
        # Calculate individual dimensions
        style_alignment = self._calculate_style_alignment(user_id, cart_items, style_profile)
        budget_fit = self._calculate_budget_fit(cart_items, budget_profile)
        size_confidence = self._calculate_size_confidence(user_id, cart_items)
        brand_affinity = self._calculate_brand_affinity(user_id, cart_items)
        occasion_match = self._calculate_occasion_match(cart_items, occasion, style_profile)
        return_risk = self.predict_return_risk(user_id, cart_items).risk_score
        
        # Calculate overall score (weighted average)
        weights = {
            "style_alignment": 0.20,
            "budget_fit": 0.15,
            "size_confidence": 0.20,
            "brand_affinity": 0.15,
            "occasion_match": 0.15,
            "return_risk_inverse": 0.15,
        }
        
        overall_score = (
            style_alignment * weights["style_alignment"] +
            budget_fit * weights["budget_fit"] +
            size_confidence * weights["size_confidence"] +
            brand_affinity * weights["brand_affinity"] +
            occasion_match * weights["occasion_match"] +
            (100 - return_risk) * weights["return_risk_inverse"]
        )
        
        # Generate recommendations
        recommendations = self._generate_confidence_recommendations(
            style_alignment, budget_fit, size_confidence, brand_affinity, occasion_match, return_risk
        )
        
        return PurchaseConfidence(
            overall_score=overall_score,
            style_alignment=style_alignment,
            budget_fit=budget_fit,
            size_confidence=size_confidence,
            brand_affinity=brand_affinity,
            occasion_match=occasion_match,
            return_risk=return_risk,
            recommendations=recommendations,
        )
    
    def _calculate_style_alignment(self, user_id: str, items: List[Dict], profile: Any) -> float:
        """Calculate how well items align with user's style."""
        if not profile:
            return 50.0
        
        score = 50.0
        
        # Check archetype match
        if profile.primary_archetype:
            # Would compare item styles to archetype
            score += 15
        
        # Check color preferences
        if profile.preferred_colors:
            item_colors = [i.get("color", "") for i in items]
            matching = sum(1 for c in item_colors if c.lower() in [p.lower() for p in profile.preferred_colors])
            score += min(20, matching * 10)
        
        return min(100, score)
    
    def _calculate_budget_fit(self, items: List[Dict], profile: Any) -> float:
        """Calculate how well prices fit user's budget."""
        if not profile or not profile.per_item_max:
            return 70.0
        
        max_price = float(profile.per_item_max)
        prices = [i.get("price", 0) for i in items]
        
        avg_price = sum(prices) / len(prices) if prices else 0
        
        if avg_price <= max_price:
            return 90.0
        elif avg_price <= max_price * 1.2:
            return 70.0
        elif avg_price <= max_price * 1.5:
            return 50.0
        return 30.0
    
    def _calculate_size_confidence(self, user_id: str, items: List[Dict]) -> float:
        """Calculate confidence in size selections."""
        # Would check against user's body profile and brand size history
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.signal_type == "purchase",
        ).count()
        
        # More purchase history = higher size confidence
        base_confidence = 40 + min(40, signals * 4)
        
        return min(100, base_confidence)
    
    def _calculate_brand_affinity(self, user_id: str, items: List[Dict]) -> float:
        """Calculate affinity for brands in cart."""
        if not items:
            return 50.0
        
        affinities = []
        for item in items:
            brand = item.get("brand", "")
            affinity = self._get_brand_affinity(user_id, brand)
            affinities.append(affinity)
        
        avg_affinity = sum(affinities) / len(affinities) if affinities else 0.5
        return avg_affinity * 100
    
    def _calculate_occasion_match(self, items: List[Dict], occasion: str, profile: Any) -> float:
        """Calculate how well items match the intended occasion."""
        if not occasion:
            return 70.0
        
        # Would check against occasion dress codes
        # Simplified scoring
        occasion_scores = {
            "formal": 80,
            "work": 85,
            "casual": 90,
            "date": 75,
            "party": 75,
            "active": 85,
        }
        
        return occasion_scores.get(occasion, 70.0)
    
    def _generate_confidence_recommendations(
        self,
        style: float,
        budget: float,
        size: float,
        brand: float,
        occasion: float,
        return_risk: float,
    ) -> List[str]:
        """Generate actionable recommendations based on confidence dimensions."""
        recommendations = []
        
        if style < 50:
            recommendations.append("Consider items that better match your style profile")
        if budget < 50:
            recommendations.append("Some items exceed your typical budget range")
        if size < 50:
            recommendations.append("Check size guide or try virtual try-on for better fit confidence")
        if brand < 40:
            recommendations.append("Explore items from your preferred brands for higher satisfaction")
        if occasion < 50:
            recommendations.append("These items may not be ideal for your intended occasion")
        if return_risk > 40:
            recommendations.append("Consider ordering multiple sizes to ensure perfect fit")
        
        if not recommendations:
            recommendations.append("High confidence purchase - you're all set!")
        
        return recommendations
    
    # ── BNPL Eligibility ─────────────────────────────────────────────────
    
    def check_bnpl_eligibility(
        self,
        user_id: str,
        order_total: float,
    ) -> Dict[str, Any]:
        """
        Check BNPL (Buy Now, Pay Later) eligibility.
        
        Factors:
        - Purchase confidence score
        - Return risk
        - Order value
        - User history
        """
        confidence = self.calculate_purchase_confidence(user_id, [])
        return_risk = self.predict_return_risk(user_id, [])
        
        thresholds = BNPL_THRESHOLDS
        
        # Check eligibility criteria
        eligible = (
            confidence.overall_score >= thresholds["eligible"]["min_confidence"] and
            return_risk.risk_score <= thresholds["eligible"]["max_risk_score"] and
            thresholds["eligible"]["min_order_value"] <= order_total <= thresholds["eligible"]["max_order_value"]
        )
        
        # Check if review required
        review_required = (
            confidence.overall_score >= thresholds["review_required"]["min_confidence"] and
            return_risk.risk_score <= thresholds["review_required"]["max_risk_score"] and
            not eligible
        )
        
        return {
            "eligible": eligible,
            "review_required": review_required,
            "confidence_score": confidence.overall_score,
            "risk_score": return_risk.risk_score,
            "order_value_ok": thresholds["eligible"]["min_order_value"] <= order_total <= thresholds["eligible"]["max_order_value"],
            "max_installments": 4 if eligible else (2 if review_required else 0),
            "reason": self._get_bnpl_reason(eligible, review_required, confidence.overall_score, return_risk.risk_score),
        }
    
    def _get_bnpl_reason(self, eligible: bool, review: bool, confidence: float, risk: float) -> str:
        """Generate reason for BNPL eligibility decision."""
        if eligible:
            return "Eligible for interest-free installments based on your profile"
        if review:
            return "May qualify - additional verification required"
        if confidence < 50:
            return "Build your style profile for BNPL eligibility"
        if risk > 30:
            return "Lower return risk required for BNPL access"
        return "Order value outside eligible range"
    
    # ── Cart Abandonment Signals ─────────────────────────────────────────
    
    def track_cart_event(
        self,
        user_id: str,
        event_type: str,
        cart_state: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> None:
        """Track cart events for abandonment analysis."""
        signal_map = {
            "cart_view": "cart_view",
            "cart_add": "cart_add",
            "cart_remove": "cart_remove",
            "checkout_start": "checkout_start",
            "checkout_abandon": "checkout_abandon",
            "promo_failed": "promo_failed",
            "shipping_estimate": "shipping_estimate",
        }
        
        signal_type = signal_map.get(event_type, event_type)
        
        signal = UserBehaviorSignal(
            user_id=user_id,
            signal_type=signal_type,
            entity_type="cart",
            entity_id="current",
            context={
                **(context or {}),
                "cart_value": cart_state.get("total", 0),
                "item_count": cart_state.get("count", 0),
            },
        )
        
        self._db.add(signal)
        self._db.commit()
    
    def detect_abandonment_risk(self, user_id: str, cart_state: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if user is at risk of cart abandonment."""
        recent_signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.signal_type.in_(["checkout_start", "checkout_abandon", "promo_failed"]),
            UserBehaviorSignal.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
        ).all()
        
        risk_factors = []
        risk_score = 0
        
        # Check for abandonment signals
        abandons = [s for s in recent_signals if s.signal_type == "checkout_abandon"]
        if abandons:
            risk_factors.append("previous_abandonment")
            risk_score += 30
        
        # Check for promo failures
        promo_fails = [s for s in recent_signals if s.signal_type == "promo_failed"]
        if promo_fails:
            risk_factors.append("promo_code_friction")
            risk_score += 20
        
        # Check cart value vs user budget
        cart_value = cart_state.get("total", 0)
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        if budget and budget.per_item_max:
            if cart_value > float(budget.per_item_max) * 3:
                risk_factors.append("budget_exceeded")
                risk_score += 25
        
        # Generate rescue strategies
        rescue_strategies = []
        if risk_score > 30:
            rescue_strategies.append({
                "type": "discount",
                "value": CART_OPTIMIZATION_RULES["abandonment_rescue_discount"],
                "message": "Special offer: 15% off your order!",
            })
            rescue_strategies.append({
                "type": "free_shipping",
                "message": "Free shipping unlocked for you!",
            })
        
        return {
            "risk_score": min(100, risk_score),
            "risk_factors": risk_factors,
            "rescue_strategies": rescue_strategies,
            "should_intervene": risk_score > 40,
        }


def get_commerce_intelligence_service(db: Session = Depends(get_db)) -> CommerceIntelligenceService:
    return CommerceIntelligenceService(db)
