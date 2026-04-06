"""
CONFIT Backend — Brand Intelligence Service
===========================================
AI-powered brand analytics and intelligence:
- Demand prediction
- Style trend analytics
- Return-risk scoring for brand products
- AI pricing suggestions
- Inventory intelligence
- Performance signals for AI Brain

Integrates with AI Central Brain for marketplace-wide intelligence.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from collections import defaultdict
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from database.models import Brand, Product, Order, OrderItem, ReturnRequest
from models.brand_models import BrandMetrics

logger = logging.getLogger(__name__)


# ── Industry Intelligence Constants ─────────────────────────────────────

DEMAND_PREDICTION_WEIGHTS = {
    "seasonality": 0.25,
    "trend_alignment": 0.20,
    "historical_velocity": 0.20,
    "social_signals": 0.15,
    "price_elasticity": 0.10,
    "inventory_pressure": 0.10,
}

SEASONAL_DEMAND_PATTERNS = {
    "dresses": {
        "spring": 1.3, "summer": 1.5, "fall": 0.9, "winter": 0.7,
        "peak_months": [4, 5, 6, 7],
    },
    "outerwear": {
        "spring": 0.6, "summer": 0.3, "fall": 1.2, "winter": 1.8,
        "peak_months": [10, 11, 12, 1],
    },
    "activewear": {
        "spring": 1.2, "summer": 1.4, "fall": 1.0, "winter": 0.8,
        "peak_months": [1, 3, 5, 6],
    },
    "tops": {
        "spring": 1.1, "summer": 1.2, "fall": 1.0, "winter": 0.9,
        "peak_months": [3, 4, 5, 6, 7],
    },
    "bottoms": {
        "spring": 1.0, "summer": 1.1, "fall": 1.0, "winter": 0.9,
        "peak_months": [4, 5, 9, 10],
    },
    "shoes": {
        "spring": 1.0, "summer": 1.2, "fall": 1.1, "winter": 0.8,
        "peak_months": [3, 4, 8, 9],
    },
    "accessories": {
        "spring": 1.1, "summer": 1.0, "fall": 1.2, "winter": 1.3,
        "peak_months": [11, 12],
    },
}

STYLE_TREND_INDICATORS = {
    "colors": {
        "rising": ["sage_green", "terracotta", "lavender", "cream", "burgundy"],
        "stable": ["navy", "black", "white", "grey", "beige"],
        "declining": ["neon_pink", "electric_blue", "acid_green"],
    },
    "patterns": {
        "rising": ["subtle_plaid", "micro_floral", "textured_solid", "geometric"],
        "stable": ["stripes", "solid", "classic_plaid"],
        "declining": ["loud_animal", "excessive_distressing", "oversized_logo"],
    },
    "silhouettes": {
        "rising": ["oversized_blazer", "wide_leg_pants", "crop_jacket", "relaxed_fit"],
        "stable": ["slim_fit", "regular_fit", "straight_leg"],
        "declining": ["skinny_jeans", "ultra_tight", "excessive_oversized"],
    },
    "fabrics": {
        "rising": ["linen_blend", "organic_cotton", "recycled_polyester", "tencel"],
        "stable": ["cotton", "wool", "polyester", "silk"],
        "declining": ["conventional_polyester", "non_recycled_nylon"],
    },
}

PRICING_STRATEGY_FACTORS = {
    "premium_positioning": {
        "margin_floor": 0.55,
        "competition_sensitivity": 0.3,
        "brand_elasticity": 0.15,
    },
    "value_positioning": {
        "margin_floor": 0.30,
        "competition_sensitivity": 0.5,
        "brand_elasticity": 0.20,
    },
    "competitive_positioning": {
        "margin_floor": 0.40,
        "competition_sensitivity": 0.4,
        "brand_elasticity": 0.20,
    },
}

RETURN_RISK_BRAND_WEIGHTS = {
    "quality_score_weight": 0.30,
    "fit_consistency_weight": 0.25,
    "material_accuracy_weight": 0.20,
    "description_accuracy_weight": 0.15,
    "historical_return_rate_weight": 0.10,
}


class DemandPrediction:
    """Demand prediction result for a product or category."""
    
    def __init__(
        self,
        product_id: str,
        predicted_demand: float,
        confidence: float,
        factors: Dict[str, float],
        recommendation: str,
        time_horizon: str = "30d",
    ):
        self.product_id = product_id
        self.predicted_demand = predicted_demand
        self.confidence = confidence
        self.factors = factors
        self.recommendation = recommendation
        self.time_horizon = time_horizon
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "predicted_demand": round(self.predicted_demand, 2),
            "confidence": round(self.confidence, 2),
            "factors": {k: round(v, 3) for k, v in self.factors.items()},
            "recommendation": self.recommendation,
            "time_horizon": self.time_horizon,
        }


class StyleTrendAnalysis:
    """Style trend analysis for brand products."""
    
    def __init__(
        self,
        brand_id: str,
        trend_alignment_score: float,
        trending_elements: Dict[str, List[str]],
        declining_elements: Dict[str, List[str]],
        recommendations: List[str],
        category_scores: Dict[str, float],
    ):
        self.brand_id = brand_id
        self.trend_alignment_score = trend_alignment_score
        self.trending_elements = trending_elements
        self.declining_elements = declining_elements
        self.recommendations = recommendations
        self.category_scores = category_scores
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "trend_alignment_score": round(self.trend_alignment_score, 2),
            "trending_elements": self.trending_elements,
            "declining_elements": self.declining_elements,
            "recommendations": self.recommendations,
            "category_scores": {k: round(v, 2) for k, v in self.category_scores.items()},
        }


class BrandReturnRiskScore:
    """Return risk assessment for brand products."""
    
    def __init__(
        self,
        brand_id: str,
        overall_risk_score: float,
        risk_level: str,
        category_risks: Dict[str, float],
        top_risk_factors: List[Dict[str, Any]],
        mitigation_strategies: List[str],
    ):
        self.brand_id = brand_id
        self.overall_risk_score = overall_risk_score
        self.risk_level = risk_level
        self.category_risks = category_risks
        self.top_risk_factors = top_risk_factors
        self.mitigation_strategies = mitigation_strategies
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "overall_risk_score": round(self.overall_risk_score, 2),
            "risk_level": self.risk_level,
            "category_risks": {k: round(v, 2) for k, v in self.category_risks.items()},
            "top_risk_factors": self.top_risk_factors,
            "mitigation_strategies": self.mitigation_strategies,
        }


class PricingSuggestion:
    """AI-powered pricing suggestion."""
    
    def __init__(
        self,
        product_id: str,
        current_price: float,
        suggested_price: float,
        price_change_percent: float,
        strategy: str,
        reasoning: List[str],
        expected_impact: Dict[str, float],
        confidence: float,
    ):
        self.product_id = product_id
        self.current_price = current_price
        self.suggested_price = suggested_price
        self.price_change_percent = price_change_percent
        self.strategy = strategy
        self.reasoning = reasoning
        self.expected_impact = expected_impact
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "current_price": round(self.current_price, 2),
            "suggested_price": round(self.suggested_price, 2),
            "price_change_percent": round(self.price_change_percent, 2),
            "strategy": self.strategy,
            "reasoning": self.reasoning,
            "expected_impact": {k: round(v, 2) for k, v in self.expected_impact.items()},
            "confidence": round(self.confidence, 2),
        }


class InventoryIntelligence:
    """Inventory intelligence report for brand."""
    
    def __init__(
        self,
        brand_id: str,
        stock_health_score: float,
        overstock_items: List[Dict[str, Any]],
        understock_items: List[Dict[str, Any]],
        reorder_recommendations: List[Dict[str, Any]],
        dead_stock_alerts: List[Dict[str, Any]],
    ):
        self.brand_id = brand_id
        self.stock_health_score = stock_health_score
        self.overstock_items = overstock_items
        self.understock_items = understock_items
        self.reorder_recommendations = reorder_recommendations
        self.dead_stock_alerts = dead_stock_alerts
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "stock_health_score": round(self.stock_health_score, 2),
            "overstock_items": self.overstock_items,
            "understock_items": self.understock_items,
            "reorder_recommendations": self.reorder_recommendations,
            "dead_stock_alerts": self.dead_stock_alerts,
        }


class BrandIntelligenceService:
    """
    AI-powered brand intelligence for marketplace optimization.
    
    Features:
    - Demand prediction using ML models
    - Style trend analytics and alignment
    - Return risk scoring for brand products
    - AI pricing suggestions
    - Inventory intelligence
    - Performance signals for AI Brain integration
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    # ── Demand Prediction ────────────────────────────────────────────────
    
    def predict_demand(
        self,
        brand_id: str,
        product_id: str = None,
        category: str = None,
        time_horizon: str = "30d",
    ) -> DemandPrediction:
        """
        Predict demand for a product or category.
        
        Factors:
        - Seasonality patterns
        - Trend alignment
        - Historical sales velocity
        - Social signals (views, wishlist, shares)
        - Price elasticity
        - Inventory pressure
        """
        # Get product data
        product = None
        if product_id:
            product = self._db.query(Product).filter_by(id=product_id).first()
        
        if not product and not category:
            # Default to brand-level prediction
            return self._predict_brand_demand(brand_id, time_horizon)
        
        # Calculate demand factors
        factors = {}
        
        # Seasonality factor
        current_month = datetime.now().month
        category_key = category or (product.category if product else "tops")
        season = self._get_current_season()
        seasonality_factor = SEASONAL_DEMAND_PATTERNS.get(
            category_key, {"spring": 1.0, "summer": 1.0, "fall": 1.0, "winter": 1.0}
        ).get(season, 1.0)
        factors["seasonality"] = seasonality_factor
        
        # Historical velocity (sales per day)
        historical_velocity = self._calculate_sales_velocity(product_id, brand_id)
        factors["historical_velocity"] = min(2.0, historical_velocity / 10)  # Normalize
        
        # Trend alignment
        trend_alignment = self._calculate_product_trend_alignment(product)
        factors["trend_alignment"] = trend_alignment
        
        # Social signals (views, wishlist adds, shares)
        social_signals = self._calculate_social_signals(product_id, brand_id)
        factors["social_signals"] = min(1.0, social_signals / 100)
        
        # Price elasticity estimate
        price_elasticity = self._estimate_price_elasticity(product)
        factors["price_elasticity"] = price_elasticity
        
        # Inventory pressure (low stock = higher demand urgency)
        inventory_pressure = self._calculate_inventory_pressure(product_id)
        factors["inventory_pressure"] = inventory_pressure
        
        # Calculate weighted prediction
        predicted_demand = sum(
            factors.get(factor, 0) * weight
            for factor, weight in DEMAND_PREDICTION_WEIGHTS.items()
        )
        
        # Scale by historical baseline
        baseline = historical_velocity * 30 if historical_velocity > 0 else 50
        predicted_demand = baseline * predicted_demand
        
        # Calculate confidence
        confidence = self._calculate_prediction_confidence(factors)
        
        # Generate recommendation
        recommendation = self._generate_demand_recommendation(predicted_demand, factors, baseline)
        
        return DemandPrediction(
            product_id=product_id or "brand_level",
            predicted_demand=predicted_demand,
            confidence=confidence,
            factors=factors,
            recommendation=recommendation,
            time_horizon=time_horizon,
        )
    
    def _predict_brand_demand(self, brand_id: str, time_horizon: str) -> DemandPrediction:
        """Predict aggregate demand for entire brand."""
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        
        if not products:
            return DemandPrediction(
                product_id="brand_level",
                predicted_demand=0,
                confidence=0.5,
                factors={},
                recommendation="No products found for demand prediction",
                time_horizon=time_horizon,
            )
        
        total_demand = 0
        total_confidence = 0
        
        for product in products:
            pred = self.predict_demand(brand_id, product.id, time_horizon=time_horizon)
            total_demand += pred.predicted_demand
            total_confidence += pred.confidence
        
        avg_confidence = total_confidence / len(products) if products else 0.5
        
        return DemandPrediction(
            product_id="brand_level",
            predicted_demand=total_demand,
            confidence=avg_confidence,
            factors={"product_count": len(products)},
            recommendation=f"Aggregate demand across {len(products)} products",
            time_horizon=time_horizon,
        )
    
    def _get_current_season(self) -> str:
        """Determine current season based on month."""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "fall"
        return "winter"
    
    def _calculate_sales_velocity(self, product_id: str, brand_id: str) -> float:
        """Calculate average daily sales velocity."""
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        query = self._db.query(func.count(OrderItem.id)).join(Order).filter(
            Order.placed_at >= thirty_days_ago
        )
        
        if product_id:
            query = query.filter(OrderItem.product_id == product_id)
        else:
            # Brand-level: get all brand products
            brand_products = self._db.query(Product.id).filter_by(brand_id=brand_id).all()
            product_ids = [p.id for p in brand_products]
            query = query.filter(OrderItem.product_id.in_(product_ids))
        
        total_sales = query.scalar() or 0
        return total_sales / 30  # Daily average
    
    def _calculate_product_trend_alignment(self, product: Product) -> float:
        """Calculate how well product aligns with current trends."""
        if not product:
            return 0.5
        
        score = 0.5  # Base score
        
        # Check color alignment
        if product.color:
            color_lower = product.color.lower().replace(" ", "_")
            if color_lower in STYLE_TREND_INDICATORS["colors"]["rising"]:
                score += 0.15
            elif color_lower in STYLE_TREND_INDICATORS["colors"]["stable"]:
                score += 0.05
            elif color_lower in STYLE_TREND_INDICATORS["colors"]["declining"]:
                score -= 0.10
        
        # Check category trend alignment
        if product.category:
            # Would integrate with real trend data
            score += 0.05
        
        # Check tags for trend keywords
        if product.tags:
            tags = product.tags if isinstance(product.tags, list) else []
            for tag in tags:
                tag_lower = str(tag).lower()
                if any(t in tag_lower for t in STYLE_TREND_INDICATORS["silhouettes"]["rising"]):
                    score += 0.10
                if any(t in tag_lower for t in STYLE_TREND_INDICATORS["fabrics"]["rising"]):
                    score += 0.10
        
        return min(1.0, max(0.0, score))
    
    def _calculate_social_signals(self, product_id: str, brand_id: str) -> float:
        """Calculate social signal strength (views, wishlist, shares)."""
        # Would integrate with actual analytics
        # Mock calculation based on order data
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        orders = self._db.query(OrderItem).join(Order).filter(
            Order.placed_at >= thirty_days_ago
        )
        
        if product_id:
            orders = orders.filter(OrderItem.product_id == product_id)
        
        count = orders.count() or 0
        return min(100, count * 5)  # Scale to 0-100
    
    def _estimate_price_elasticity(self, product: Product) -> float:
        """Estimate price elasticity (demand sensitivity to price)."""
        if not product or not product.price:
            return 0.5
        
        # Higher price = higher elasticity (more sensitive)
        price = product.price
        
        if price < 50:
            return 0.3  # Low sensitivity
        elif price < 100:
            return 0.5  # Medium sensitivity
        elif price < 200:
            return 0.7  # High sensitivity
        return 0.9  # Very high sensitivity
    
    def _calculate_inventory_pressure(self, product_id: str) -> float:
        """Calculate inventory pressure (low stock urgency)."""
        # Would integrate with actual inventory system
        # Return moderate pressure as default
        return 0.5
    
    def _calculate_prediction_confidence(self, factors: Dict[str, float]) -> float:
        """Calculate confidence based on data availability."""
        # More factors with non-zero values = higher confidence
        active_factors = sum(1 for v in factors.values() if v > 0)
        total_factors = len(factors) if factors else 1
        
        base_confidence = active_factors / total_factors
        
        # Boost confidence if historical data exists
        if factors.get("historical_velocity", 0) > 0:
            base_confidence += 0.15
        
        return min(0.95, base_confidence)
    
    def _generate_demand_recommendation(
        self, predicted: float, factors: Dict, baseline: float
    ) -> str:
        """Generate actionable demand recommendation."""
        change = (predicted - baseline) / baseline if baseline > 0 else 0
        
        if change > 0.3:
            return "High demand expected - increase inventory and marketing investment"
        elif change > 0.1:
            return "Moderate demand growth - maintain current inventory levels"
        elif change > -0.1:
            return "Stable demand - optimize pricing and promotions"
        elif change > -0.3:
            return "Declining demand - consider promotions or markdowns"
        return "Significant demand decline - review product positioning and pricing"
    
    # ── Style Trend Analytics ─────────────────────────────────────────────
    
    def analyze_style_trends(self, brand_id: str) -> StyleTrendAnalysis:
        """
        Analyze brand's alignment with current style trends.
        
        Analyzes:
        - Color trends
        - Pattern trends
        - Silhouette trends
        - Fabric/material trends
        """
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        
        if not products:
            return StyleTrendAnalysis(
                brand_id=brand_id,
                trend_alignment_score=50.0,
                trending_elements={},
                declining_elements={},
                recommendations=["Add products to enable trend analysis"],
                category_scores={},
            )
        
        # Analyze each dimension
        trending_elements = {"colors": [], "patterns": [], "silhouettes": [], "fabrics": []}
        declining_elements = {"colors": [], "patterns": [], "silhouettes": [], "fabrics": []}
        category_scores = {}
        
        # Color analysis
        color_score = self._analyze_color_trends(products, trending_elements, declining_elements)
        category_scores["colors"] = color_score
        
        # Pattern analysis
        pattern_score = self._analyze_pattern_trends(products, trending_elements, declining_elements)
        category_scores["patterns"] = pattern_score
        
        # Silhouette analysis
        silhouette_score = self._analyze_silhouette_trends(products, trending_elements, declining_elements)
        category_scores["silhouettes"] = silhouette_score
        
        # Calculate overall alignment score
        trend_alignment_score = (
            color_score * 0.30 +
            pattern_score * 0.25 +
            silhouette_score * 0.25 +
            50.0 * 0.20  # Fabric score placeholder
        )
        
        # Generate recommendations
        recommendations = self._generate_trend_recommendations(
            trend_alignment_score, trending_elements, declining_elements
        )
        
        return StyleTrendAnalysis(
            brand_id=brand_id,
            trend_alignment_score=trend_alignment_score,
            trending_elements=trending_elements,
            declining_elements=declining_elements,
            recommendations=recommendations,
            category_scores=category_scores,
        )
    
    def _analyze_color_trends(
        self, products: List[Product], trending: Dict, declining: Dict
    ) -> float:
        """Analyze color trend alignment."""
        score = 50.0
        color_counts = defaultdict(int)
        
        for product in products:
            if product.color:
                color_lower = product.color.lower().replace(" ", "_")
                color_counts[color_lower] += 1
                
                if color_lower in STYLE_TREND_INDICATORS["colors"]["rising"]:
                    trending["colors"].append(product.color)
                    score += 5
                elif color_lower in STYLE_TREND_INDICATORS["colors"]["declining"]:
                    declining["colors"].append(product.color)
                    score -= 5
        
        return min(100, max(0, score))
    
    def _analyze_pattern_trends(
        self, products: List[Product], trending: Dict, declining: Dict
    ) -> float:
        """Analyze pattern trend alignment."""
        score = 50.0
        
        for product in products:
            if product.tags:
                tags = product.tags if isinstance(product.tags, list) else []
                for tag in tags:
                    tag_lower = str(tag).lower()
                    
                    for pattern in STYLE_TREND_INDICATORS["patterns"]["rising"]:
                        if pattern in tag_lower:
                            trending["patterns"].append(str(tag))
                            score += 3
                    
                    for pattern in STYLE_TREND_INDICATORS["patterns"]["declining"]:
                        if pattern in tag_lower:
                            declining["patterns"].append(str(tag))
                            score -= 3
        
        return min(100, max(0, score))
    
    def _analyze_silhouette_trends(
        self, products: List[Product], trending: Dict, declining: Dict
    ) -> float:
        """Analyze silhouette trend alignment."""
        score = 50.0
        
        for product in products:
            if product.tags:
                tags = product.tags if isinstance(product.tags, list) else []
                for tag in tags:
                    tag_lower = str(tag).lower()
                    
                    for silhouette in STYLE_TREND_INDICATORS["silhouettes"]["rising"]:
                        if silhouette in tag_lower:
                            trending["silhouettes"].append(str(tag))
                            score += 4
                    
                    for silhouette in STYLE_TREND_INDICATORS["silhouettes"]["declining"]:
                        if silhouette in tag_lower:
                            declining["silhouettes"].append(str(tag))
                            score -= 4
        
        return min(100, max(0, score))
    
    def _generate_trend_recommendations(
        self, score: float, trending: Dict, declining: Dict
    ) -> List[str]:
        """Generate trend alignment recommendations."""
        recommendations = []
        
        if score >= 75:
            recommendations.append("Excellent trend alignment - your collection is fashion-forward")
        elif score >= 50:
            recommendations.append("Good trend alignment - consider expanding trending categories")
        else:
            recommendations.append("Below-average trend alignment - review declining elements")
        
        if declining["colors"]:
            recommendations.append(
                f"Consider reducing inventory in declining colors: {', '.join(declining['colors'][:3])}"
            )
        
        if trending["colors"]:
            recommendations.append(
                f"Expand offerings in trending colors: {', '.join(set(trending['colors'][:3]))}"
            )
        
        if declining["silhouettes"]:
            recommendations.append(
                "Phase out declining silhouettes in upcoming collections"
            )
        
        return recommendations
    
    # ── Return Risk Scoring ───────────────────────────────────────────────
    
    def calculate_brand_return_risk(self, brand_id: str) -> BrandReturnRiskScore:
        """
        Calculate return risk score for brand products.
        
        Factors:
        - Historical return rate
        - Category-specific risk
        - Quality indicators
        - Fit consistency
        - Description accuracy
        """
        # Get brand's orders and returns
        brand_products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        product_ids = [p.id for p in brand_products]
        
        if not product_ids:
            return BrandReturnRiskScore(
                brand_id=brand_id,
                overall_risk_score=50.0,
                risk_level="unknown",
                category_risks={},
                top_risk_factors=[],
                mitigation_strategies=["Add products to enable return risk analysis"],
            )
        
        # Calculate historical return rate
        total_orders = self._db.query(OrderItem).filter(
            OrderItem.product_id.in_(product_ids)
        ).count()
        
        returns = self._db.query(ReturnRequest).filter(
            ReturnRequest.items.contains(str(brand_id))
        ).count()
        
        historical_rate = returns / total_orders if total_orders > 0 else 0.15
        
        # Calculate category-specific risks
        category_risks = {}
        for product in brand_products:
            cat = product.category
            if cat not in category_risks:
                category_risks[cat] = self._calculate_category_return_risk(cat, historical_rate)
        
        # Calculate overall risk score
        risk_factors = []
        
        # Historical return rate factor
        if historical_rate > 0.25:
            risk_factors.append({
                "factor": "high_return_rate",
                "value": f"{historical_rate:.1%}",
                "impact": "high",
            })
        elif historical_rate > 0.15:
            risk_factors.append({
                "factor": "elevated_return_rate",
                "value": f"{historical_rate:.1%}",
                "impact": "medium",
            })
        
        # Category risk factors
        high_risk_categories = [
            cat for cat, score in category_risks.items() if score > 60
        ]
        if high_risk_categories:
            risk_factors.append({
                "factor": "high_risk_categories",
                "value": ", ".join(high_risk_categories),
                "impact": "medium",
            })
        
        # Calculate overall score
        avg_category_risk = sum(category_risks.values()) / len(category_risks) if category_risks else 50
        overall_score = (
            historical_rate * 100 * RETURN_RISK_BRAND_WEIGHTS["historical_return_rate_weight"] +
            avg_category_risk * RETURN_RISK_BRAND_WEIGHTS["quality_score_weight"]
        )
        
        # Determine risk level
        if overall_score >= 60:
            risk_level = "high"
        elif overall_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate mitigation strategies
        strategies = self._generate_return_mitigation_strategies(overall_score, risk_factors)
        
        return BrandReturnRiskScore(
            brand_id=brand_id,
            overall_risk_score=min(100, overall_score),
            risk_level=risk_level,
            category_risks=category_risks,
            top_risk_factors=risk_factors[:5],
            mitigation_strategies=strategies,
        )
    
    def _calculate_category_return_risk(self, category: str, base_rate: float) -> float:
        """Calculate return risk for a specific category."""
        # Category-specific risk modifiers
        category_modifiers = {
            "dresses": 1.3,
            "shoes": 1.4,
            "pants": 1.2,
            "tops": 1.0,
            "outerwear": 1.1,
            "accessories": 0.8,
            "activewear": 0.9,
        }
        
        modifier = category_modifiers.get(category, 1.0)
        return min(100, base_rate * 100 * modifier)
    
    def _generate_return_mitigation_strategies(
        self, score: float, factors: List[Dict]
    ) -> List[str]:
        """Generate strategies to reduce return risk."""
        strategies = []
        
        if score >= 60:
            strategies.append("Implement enhanced size guides with body measurement recommendations")
            strategies.append("Add virtual try-on for high-risk categories")
            strategies.append("Review product descriptions for accuracy")
        
        if any(f["factor"] == "high_risk_categories" for f in factors):
            strategies.append("Focus quality improvements on high-risk categories")
            strategies.append("Add customer reviews for fit validation")
        
        strategies.append("Enable detailed product imagery from multiple angles")
        strategies.append("Implement fit prediction based on customer profiles")
        
        return strategies
    
    # ── AI Pricing Suggestions ───────────────────────────────────────────
    
    def generate_pricing_suggestions(
        self,
        brand_id: str,
        product_id: str = None,
        strategy: str = "competitive",
    ) -> List[PricingSuggestion]:
        """
        Generate AI-powered pricing suggestions.
        
        Strategies:
        - premium: Higher margins, brand positioning
        - value: Competitive pricing, volume focus
        - competitive: Market-aligned pricing
        """
        products = []
        if product_id:
            product = self._db.query(Product).filter_by(id=product_id).first()
            if product:
                products = [product]
        else:
            products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        
        suggestions = []
        
        for product in products:
            suggestion = self._calculate_pricing_suggestion(product, strategy)
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    def _calculate_pricing_suggestion(
        self, product: Product, strategy: str
    ) -> Optional[PricingSuggestion]:
        """Calculate pricing suggestion for a single product."""
        if not product or not product.price:
            return None
        
        current_price = product.price
        reasoning = []
        expected_impact = {}
        
        # Get strategy parameters
        params = PRICING_STRATEGY_FACTORS.get(strategy, PRICING_STRATEGY_FACTORS["competitive"])
        
        # Calculate demand-adjusted price
        demand = self.predict_demand(product.brand_id, product.id)
        
        # Calculate trend-adjusted price
        trend_score = self._calculate_product_trend_alignment(product)
        
        # Calculate competitive position
        competitive_price = self._estimate_competitive_price(product)
        
        # Calculate suggested price
        base_adjustment = 1.0
        
        # Demand factor
        if demand.predicted_demand > 100:
            base_adjustment += 0.05  # High demand = premium
            reasoning.append("High predicted demand supports premium pricing")
        elif demand.predicted_demand < 30:
            base_adjustment -= 0.10  # Low demand = reduce price
            reasoning.append("Low demand suggests price reduction")
        
        # Trend factor
        if trend_score > 0.7:
            base_adjustment += 0.08
            reasoning.append("Strong trend alignment supports higher pricing")
        elif trend_score < 0.4:
            base_adjustment -= 0.05
            reasoning.append("Below-average trend alignment suggests competitive pricing")
        
        # Competitive factor
        if competitive_price > 0:
            competitive_diff = (current_price - competitive_price) / competitive_price
            if competitive_diff > 0.2:
                base_adjustment -= 0.10
                reasoning.append("Price significantly above market average")
            elif competitive_diff < -0.1:
                base_adjustment += 0.05
                reasoning.append("Opportunity to increase price while staying competitive")
        
        # Apply strategy constraints
        margin_floor = params["margin_floor"]
        min_price = current_price * (1 - (1 - margin_floor))  # Floor based on margin
        
        suggested_price = current_price * base_adjustment
        suggested_price = max(min_price, suggested_price)
        
        # Calculate expected impact
        price_change = (suggested_price - current_price) / current_price
        
        if price_change > 0:
            expected_impact["revenue_change"] = price_change * 0.7  # Some volume loss
            expected_impact["margin_change"] = price_change * 0.8
        else:
            expected_impact["revenue_change"] = price_change * 0.5  # Volume gain
            expected_impact["margin_change"] = price_change * 0.9
        
        expected_impact["demand_change"] = -price_change * demand.factors.get("price_elasticity", 0.5) * 10
        
        confidence = demand.confidence * 0.8 + 0.2  # Base confidence
        
        return PricingSuggestion(
            product_id=product.id,
            current_price=current_price,
            suggested_price=round(suggested_price, 2),
            price_change_percent=price_change * 100,
            strategy=strategy,
            reasoning=reasoning,
            expected_impact=expected_impact,
            confidence=confidence,
        )
    
    def _estimate_competitive_price(self, product: Product) -> float:
        """Estimate competitive market price for product."""
        # Find similar products
        similar = self._db.query(Product).filter(
            Product.category == product.category,
            Product.id != product.id,
            Product.price != None,
        ).limit(10).all()
        
        if not similar:
            return 0.0
        
        prices = [p.price for p in similar if p.price]
        return sum(prices) / len(prices) if prices else 0.0
    
    # ── Inventory Intelligence ───────────────────────────────────────────
    
    def get_inventory_intelligence(self, brand_id: str) -> InventoryIntelligence:
        """
        Generate inventory intelligence report.
        
        Includes:
        - Stock health score
        - Overstock alerts
        - Understock alerts
        - Reorder recommendations
        - Dead stock alerts
        """
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        
        overstock = []
        understock = []
        reorder_recs = []
        dead_stock = []
        
        for product in products:
            # Get demand prediction
            demand = self.predict_demand(brand_id, product.id)
            
            # Mock inventory level (would integrate with actual inventory)
            current_stock = 50  # Placeholder
            
            # Calculate days of stock
            daily_demand = demand.predicted_demand / 30
            days_of_stock = current_stock / daily_demand if daily_demand > 0 else 999
            
            if days_of_stock > 90:
                overstock.append({
                    "product_id": product.id,
                    "name": product.name,
                    "days_of_stock": round(days_of_stock),
                    "recommended_action": "markdown" if days_of_stock > 120 else "promotion",
                })
            elif days_of_stock < 14:
                understock.append({
                    "product_id": product.id,
                    "name": product.name,
                    "days_of_stock": round(days_of_stock),
                    "urgency": "high" if days_of_stock < 7 else "medium",
                })
                reorder_recs.append({
                    "product_id": product.id,
                    "name": product.name,
                    "suggested_quantity": int(daily_demand * 45),  # 45-day supply
                    "priority": "urgent" if days_of_stock < 7 else "high",
                })
            
            # Dead stock detection (no sales in 60 days)
            # Would integrate with actual sales data
            if days_of_stock > 180:
                dead_stock.append({
                    "product_id": product.id,
                    "name": product.name,
                    "recommendation": "clearance or donation",
                })
        
        # Calculate stock health score
        total_products = len(products)
        healthy_count = total_products - len(overstock) - len(understock)
        stock_health = (healthy_count / total_products * 100) if total_products > 0 else 100
        
        return InventoryIntelligence(
            brand_id=brand_id,
            stock_health_score=stock_health,
            overstock_items=overstock,
            understock_items=understock,
            reorder_recommendations=reorder_recs,
            dead_stock_alerts=dead_stock,
        )
    
    # ── Performance Signals for AI Brain ───────────────────────────────────
    
    def get_brand_performance_signals(self, brand_id: str) -> Dict[str, Any]:
        """
        Generate performance signals for AI Central Brain integration.
        
        Signals include:
        - Item performance metrics
        - Styling popularity
        - Return data
        - Engagement analytics
        """
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        product_ids = [p.id for p in products]
        
        # Calculate performance metrics
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Order metrics
        orders = self._db.query(OrderItem).join(Order).filter(
            Order.placed_at >= thirty_days_ago,
            OrderItem.product_id.in_(product_ids) if product_ids else False,
        ).all()
        
        total_revenue = sum(item.price * item.quantity for item in orders)
        total_units = sum(item.quantity for item in orders)
        
        # Return metrics
        returns = self._db.query(ReturnRequest).filter(
            ReturnRequest.requested_at >= thirty_days_ago,
        ).all()
        
        return_count = sum(1 for r in returns if brand_id in str(r.items))
        
        # Calculate popularity scores
        popularity_scores = {}
        for product in products:
            product_orders = [o for o in orders if o.product_id == product.id]
            popularity_scores[product.id] = {
                "units_sold": sum(o.quantity for o in product_orders),
                "revenue": sum(o.price * o.quantity for o in product_orders),
                "popularity_rank": 0,  # Would calculate relative rank
            }
        
        # Rank products by sales
        ranked = sorted(popularity_scores.items(), key=lambda x: x[1]["units_sold"], reverse=True)
        for rank, (pid, _) in enumerate(ranked, 1):
            popularity_scores[pid]["popularity_rank"] = rank
        
        return {
            "brand_id": brand_id,
            "period": "30d",
            "performance": {
                "total_revenue": round(total_revenue, 2),
                "total_units_sold": total_units,
                "return_count": return_count,
                "return_rate": return_count / total_units if total_units > 0 else 0,
            },
            "item_performance": popularity_scores,
            "styling_popularity": self._calculate_styling_popularity(brand_id),
            "engagement_analytics": self._calculate_engagement_analytics(brand_id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _calculate_styling_popularity(self, brand_id: str) -> Dict[str, Any]:
        """Calculate how often brand items appear in styled outfits."""
        # Would integrate with outfit data
        return {
            "outfit_appearances": 0,
            "stylist_picks": 0,
            "user_favorites": 0,
        }
    
    def _calculate_engagement_analytics(self, brand_id: str) -> Dict[str, Any]:
        """Calculate engagement metrics for brand."""
        # Would integrate with analytics
        return {
            "views": 0,
            "wishlist_adds": 0,
            "try_on_sessions": 0,
            "shares": 0,
        }
    
    # ── AI Brain Integration: Receive Intelligence ─────────────────────────
    
    def apply_ranking_adjustments(
        self, brand_id: str, adjustments: Dict[str, float]
    ) -> Dict[str, Any]:
        """Apply ranking adjustments from AI Brain."""
        # Would update product rankings/visibility
        return {
            "brand_id": brand_id,
            "adjustments_applied": adjustments,
            "status": "applied",
        }
    
    def apply_recommendation_boost(
        self, brand_id: str, boost_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply recommendation boost from AI Brain."""
        # Would update recommendation weights
        return {
            "brand_id": brand_id,
            "boost_applied": boost_config,
            "status": "active",
        }
    
    def get_inventory_intelligence_for_brain(self, brand_id: str) -> Dict[str, Any]:
        """Get inventory intelligence formatted for AI Brain consumption."""
        intel = self.get_inventory_intelligence(brand_id)
        return {
            "brand_id": brand_id,
            "stock_health": intel.stock_health_score,
            "alerts": {
                "overstock_count": len(intel.overstock_items),
                "understock_count": len(intel.understock_items),
                "dead_stock_count": len(intel.dead_stock_alerts),
            },
            "reorder_priorities": [
                r["priority"] for r in intel.reorder_recommendations
            ],
        }
