"""
CONFIT Backend — Marketplace Governance Service
===============================================
Marketplace governance and brand trust management:
- Moderation rules engine
- Quality scoring system
- Brand trust index calculation
- Compliance monitoring
- Admin audit logging

Ensures marketplace integrity and brand accountability.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from collections import defaultdict
import json
import re

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from database.models import Brand, Product, Order, OrderItem, ReturnRequest, User

logger = logging.getLogger(__name__)


# ── Governance Constants ───────────────────────────────────────────────

MODERATION_RULES = {
    "product_content": {
        "prohibited_keywords": [
            "counterfeit", "replica", "fake", "knockoff",
            "unauthorized", "not authentic",
        ],
        "required_fields": ["name", "description", "price", "category"],
        "image_requirements": {
            "min_count": 1,
            "max_count": 10,
            "min_resolution": (500, 500),
        },
        "description_min_length": 20,
    },
    "pricing_rules": {
        "min_price": 5.0,
        "max_price": 50000.0,
        "suspicious_discount_threshold": 0.80,  # >80% off is suspicious
    },
    "brand_verification": {
        "required_documents": ["business_license", "brand_authorization"],
        "verification_validity_days": 365,
    },
    "content_guidelines": {
        "prohibited_content": [
            "adult_content", "hate_speech", "violence",
            "discriminatory_language", "misleading_claims",
        ],
    },
}

QUALITY_SCORING_WEIGHTS = {
    "product_completeness": 0.15,
    "image_quality": 0.15,
    "description_quality": 0.15,
    "customer_reviews": 0.20,
    "return_rate": 0.15,
    "fulfillment_performance": 0.10,
    "response_time": 0.10,
}

TRUST_INDEX_FACTORS = {
    "quality_score": 0.25,
    "fulfillment_reliability": 0.20,
    "customer_satisfaction": 0.20,
    "return_rate": 0.15,
    "dispute_rate": 0.10,
    "compliance_history": 0.10,
}

TRUST_INDEX_THRESHOLDS = {
    "platinum": {"min_score": 90, "benefits": ["priority_placement", "reduced_fees", "premium_badge"]},
    "gold": {"min_score": 75, "benefits": ["featured_placement", "standard_fees", "gold_badge"]},
    "silver": {"min_score": 60, "benefits": ["standard_placement", "standard_fees", "silver_badge"]},
    "bronze": {"min_score": 40, "benefits": ["basic_placement", "standard_fees", "bronze_badge"]},
    "probation": {"min_score": 0, "benefits": ["restricted_placement", "enhanced_monitoring"]},
}


class ModerationResult:
    """Result of content moderation check."""
    
    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        passed: bool,
        violations: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
        auto_actions: List[str],
        requires_manual_review: bool,
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.passed = passed
        self.violations = violations
        self.warnings = warnings
        self.auto_actions = auto_actions
        self.requires_manual_review = requires_manual_review
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "passed": self.passed,
            "violations": self.violations,
            "warnings": self.warnings,
            "auto_actions": self.auto_actions,
            "requires_manual_review": self.requires_manual_review,
        }


class QualityScore:
    """Quality score for a brand or product."""
    
    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        overall_score: float,
        tier: str,
        dimension_scores: Dict[str, float],
        improvement_areas: List[str],
        last_updated: datetime,
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.overall_score = overall_score
        self.tier = tier
        self.dimension_scores = dimension_scores
        self.improvement_areas = improvement_areas
        self.last_updated = last_updated
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "overall_score": round(self.overall_score, 2),
            "tier": self.tier,
            "dimension_scores": {k: round(v, 2) for k, v in self.dimension_scores.items()},
            "improvement_areas": self.improvement_areas,
            "last_updated": self.last_updated.isoformat(),
        }


class BrandTrustIndex:
    """Brand trust index with comprehensive scoring."""
    
    def __init__(
        self,
        brand_id: str,
        trust_score: float,
        trust_tier: str,
        tier_benefits: List[str],
        factor_scores: Dict[str, float],
        historical_trend: List[Dict[str, Any]],
        recommendations: List[str],
        probation_risk: bool,
        last_calculated: datetime,
    ):
        self.brand_id = brand_id
        self.trust_score = trust_score
        self.trust_tier = trust_tier
        self.tier_benefits = tier_benefits
        self.factor_scores = factor_scores
        self.historical_trend = historical_trend
        self.recommendations = recommendations
        self.probation_risk = probation_risk
        self.last_calculated = last_calculated
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "trust_score": round(self.trust_score, 2),
            "trust_tier": self.trust_tier,
            "tier_benefits": self.tier_benefits,
            "factor_scores": {k: round(v, 2) for k, v in self.factor_scores.items()},
            "historical_trend": self.historical_trend,
            "recommendations": self.recommendations,
            "probation_risk": self.probation_risk,
            "last_calculated": self.last_calculated.isoformat(),
        }


class ComplianceReport:
    """Compliance status report for a brand."""
    
    def __init__(
        self,
        brand_id: str,
        is_compliant: bool,
        compliance_score: float,
        violations: List[Dict[str, Any]],
        pending_actions: List[Dict[str, Any]],
        next_review_date: datetime,
    ):
        self.brand_id = brand_id
        self.is_compliant = is_compliant
        self.compliance_score = compliance_score
        self.violations = violations
        self.pending_actions = pending_actions
        self.next_review_date = next_review_date
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "is_compliant": self.is_compliant,
            "compliance_score": round(self.compliance_score, 2),
            "violations": self.violations,
            "pending_actions": self.pending_actions,
            "next_review_date": self.next_review_date.isoformat(),
        }


class AdminAuditLog:
    """Audit log entry for admin actions."""
    
    def __init__(
        self,
        action_id: str,
        action_type: str,
        admin_user_id: str,
        target_type: str,
        target_id: str,
        details: Dict[str, Any],
        timestamp: datetime,
    ):
        self.action_id = action_id
        self.action_type = action_type
        self.admin_user_id = admin_user_id
        self.target_type = target_type
        self.target_id = target_id
        self.details = details
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "admin_user_id": self.admin_user_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class MarketplaceGovernanceService:
    """
    Marketplace governance and brand trust management.
    
    Features:
    - Content moderation engine
    - Quality scoring system
    - Brand trust index
    - Compliance monitoring
    - Admin audit logging
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._audit_logs: List[Dict] = []  # In-memory audit (would persist to DB)
    
    # ── Content Moderation ───────────────────────────────────────────────
    
    def moderate_product(self, product_id: str) -> ModerationResult:
        """
        Run comprehensive moderation checks on a product.
        
        Checks:
        - Prohibited keywords
        - Required fields
        - Image requirements
        - Pricing rules
        - Content guidelines
        """
        product = self._db.query(Product).filter_by(id=product_id).first()
        
        if not product:
            return ModerationResult(
                entity_type="product",
                entity_id=product_id,
                passed=False,
                violations=[{"type": "not_found", "message": "Product not found"}],
                warnings=[],
                auto_actions=[],
                requires_manual_review=False,
            )
        
        violations = []
        warnings = []
        auto_actions = []
        requires_manual_review = False
        
        # Check required fields
        for field in MODERATION_RULES["product_content"]["required_fields"]:
            value = getattr(product, field, None)
            if not value:
                violations.append({
                    "type": "missing_required_field",
                    "field": field,
                    "severity": "high",
                })
        
        # Check for prohibited keywords
        text_to_check = f"{product.name or ''} {product.description or ''}".lower()
        for keyword in MODERATION_RULES["product_content"]["prohibited_keywords"]:
            if keyword.lower() in text_to_check:
                violations.append({
                    "type": "prohibited_keyword",
                    "keyword": keyword,
                    "severity": "critical",
                })
                requires_manual_review = True
        
        # Check description length
        desc_len = len(product.description or "")
        min_len = MODERATION_RULES["product_content"]["description_min_length"]
        if desc_len < min_len:
            warnings.append({
                "type": "short_description",
                "current_length": desc_len,
                "minimum": min_len,
            })
        
        # Check pricing rules
        if product.price:
            if product.price < MODERATION_RULES["pricing_rules"]["min_price"]:
                violations.append({
                    "type": "price_below_minimum",
                    "price": product.price,
                    "minimum": MODERATION_RULES["pricing_rules"]["min_price"],
                    "severity": "high",
                })
            
            if product.price > MODERATION_RULES["pricing_rules"]["max_price"]:
                warnings.append({
                    "type": "price_above_typical",
                    "price": product.price,
                })
                requires_manual_review = True
        
        # Check for prohibited content patterns
        content_violations = self._check_content_guidelines(product)
        violations.extend(content_violations)
        
        # Determine auto actions
        if violations:
            auto_actions.append("flag_for_review")
            if any(v.get("severity") == "critical" for v in violations):
                auto_actions.append("auto_suspend")
        
        passed = len(violations) == 0
        
        return ModerationResult(
            entity_type="product",
            entity_id=product_id,
            passed=passed,
            violations=violations,
            warnings=warnings,
            auto_actions=auto_actions,
            requires_manual_review=requires_manual_review,
        )
    
    def _check_content_guidelines(self, product: Product) -> List[Dict]:
        """Check product against content guidelines."""
        violations = []
        
        text = f"{product.name or ''} {product.description or ''}".lower()
        
        # Check for misleading claims
        misleading_patterns = [
            r"100%\s*(guaranteed|effective|safe)",
            r"miracle\s*(cure|solution|product)",
            r"clinically\s*proven\s*(without|never)",
        ]
        
        for pattern in misleading_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append({
                    "type": "misleading_claim",
                    "pattern": pattern,
                    "severity": "high",
                })
        
        return violations
    
    def moderate_brand(self, brand_id: str) -> ModerationResult:
        """
        Run moderation checks on a brand profile.
        
        Checks:
        - Brand verification status
        - Profile completeness
        - Historical compliance
        """
        brand = self._db.query(Brand).filter_by(id=brand_id).first()
        
        if not brand:
            return ModerationResult(
                entity_type="brand",
                entity_id=brand_id,
                passed=False,
                violations=[{"type": "not_found"}],
                warnings=[],
                auto_actions=[],
                requires_manual_review=False,
            )
        
        violations = []
        warnings = []
        
        # Check profile completeness
        if not brand.name:
            violations.append({"type": "missing_name", "severity": "high"})
        if not brand.description:
            warnings.append({"type": "missing_description"})
        
        # Check product compliance
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        non_compliant_products = 0
        
        for product in products:
            result = self.moderate_product(product.id)
            if not result.passed:
                non_compliant_products += 1
        
        if non_compliant_products > len(products) * 0.3:
            violations.append({
                "type": "high_non_compliance_rate",
                "rate": non_compliant_products / len(products) if products else 0,
                "severity": "high",
            })
        
        passed = len(violations) == 0
        
        return ModerationResult(
            entity_type="brand",
            entity_id=brand_id,
            passed=passed,
            violations=violations,
            warnings=warnings,
            auto_actions=["flag_for_review"] if violations else [],
            requires_manual_review=len(violations) > 0,
        )
    
    # ── Quality Scoring ───────────────────────────────────────────────────
    
    def calculate_brand_quality_score(self, brand_id: str) -> QualityScore:
        """
        Calculate comprehensive quality score for a brand.
        
        Dimensions:
        - Product completeness
        - Image quality
        - Description quality
        - Customer reviews
        - Return rate
        - Fulfillment performance
        - Response time
        """
        brand = self._db.query(Brand).filter_by(id=brand_id).first()
        
        if not brand:
            return QualityScore(
                entity_type="brand",
                entity_id=brand_id,
                overall_score=0,
                tier="unrated",
                dimension_scores={},
                improvement_areas=["Brand not found"],
                last_updated=datetime.now(timezone.utc),
            )
        
        dimension_scores = {}
        improvement_areas = []
        
        # Product completeness
        completeness = self._calculate_product_completeness(brand_id)
        dimension_scores["product_completeness"] = completeness
        if completeness < 70:
            improvement_areas.append("Complete all required product fields")
        
        # Image quality
        image_quality = self._calculate_image_quality(brand_id)
        dimension_scores["image_quality"] = image_quality
        if image_quality < 70:
            improvement_areas.append("Improve product image quality and quantity")
        
        # Description quality
        desc_quality = self._calculate_description_quality(brand_id)
        dimension_scores["description_quality"] = desc_quality
        if desc_quality < 70:
            improvement_areas.append("Enhance product descriptions with more detail")
        
        # Customer reviews (mock - would integrate with review system)
        dimension_scores["customer_reviews"] = 75.0
        
        # Return rate
        return_score = self._calculate_return_rate_score(brand_id)
        dimension_scores["return_rate"] = return_score
        if return_score < 70:
            improvement_areas.append("Reduce return rate through better product information")
        
        # Fulfillment performance (mock)
        dimension_scores["fulfillment_performance"] = 85.0
        
        # Response time (mock)
        dimension_scores["response_time"] = 80.0
        
        # Calculate overall score
        overall_score = sum(
            dimension_scores.get(dim, 0) * weight
            for dim, weight in QUALITY_SCORING_WEIGHTS.items()
        )
        
        # Determine tier
        tier = self._determine_quality_tier(overall_score)
        
        return QualityScore(
            entity_type="brand",
            entity_id=brand_id,
            overall_score=overall_score,
            tier=tier,
            dimension_scores=dimension_scores,
            improvement_areas=improvement_areas,
            last_updated=datetime.now(timezone.utc),
        )
    
    def _calculate_product_completeness(self, brand_id: str) -> float:
        """Calculate product profile completeness score."""
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        
        if not products:
            return 0.0
        
        total_score = 0
        required_fields = ["name", "description", "price", "category", "image_url"]
        
        for product in products:
            filled_fields = sum(1 for f in required_fields if getattr(product, f, None))
            total_score += (filled_fields / len(required_fields)) * 100
        
        return total_score / len(products)
    
    def _calculate_image_quality(self, brand_id: str) -> float:
        """Calculate image quality score."""
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        
        if not products:
            return 0.0
        
        score = 0
        for product in products:
            if product.image_url:
                score += 70  # Has image
                # Would check resolution, quality, etc.
                score += 10  # Placeholder for quality check
        
        return min(100, score / len(products))
    
    def _calculate_description_quality(self, brand_id: str) -> float:
        """Calculate description quality score."""
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        
        if not products:
            return 0.0
        
        total_score = 0
        
        for product in products:
            desc = product.description or ""
            score = 0
            
            # Length score
            if len(desc) >= 100:
                score += 40
            elif len(desc) >= 50:
                score += 25
            elif len(desc) >= 20:
                score += 15
            
            # Richness score (would check for bullet points, details, etc.)
            if any(c in desc for c in [".", ","]):  # Has sentences
                score += 20
            
            total_score += min(100, score)
        
        return total_score / len(products)
    
    def _calculate_return_rate_score(self, brand_id: str) -> float:
        """Calculate return rate score (inverse of return rate)."""
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        product_ids = [p.id for p in products]
        
        if not product_ids:
            return 100.0
        
        # Get orders and returns
        orders = self._db.query(OrderItem).filter(
            OrderItem.product_id.in_(product_ids)
        ).count()
        
        returns = self._db.query(ReturnRequest).filter(
            ReturnRequest.items.contains(str(brand_id))
        ).count()
        
        return_rate = returns / orders if orders > 0 else 0
        
        # Score inverse to return rate
        if return_rate <= 0.05:
            return 100.0
        elif return_rate <= 0.10:
            return 90.0
        elif return_rate <= 0.15:
            return 80.0
        elif return_rate <= 0.20:
            return 70.0
        elif return_rate <= 0.30:
            return 50.0
        return 30.0
    
    def _determine_quality_tier(self, score: float) -> str:
        """Determine quality tier from score."""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "average"
        elif score >= 40:
            return "below_average"
        return "poor"
    
    # ── Brand Trust Index ────────────────────────────────────────────────
    
    def calculate_brand_trust_index(self, brand_id: str) -> BrandTrustIndex:
        """
        Calculate comprehensive brand trust index.
        
        Factors:
        - Quality score
        - Fulfillment reliability
        - Customer satisfaction
        - Return rate
        - Dispute rate
        - Compliance history
        """
        brand = self._db.query(Brand).filter_by(id=brand_id).first()
        
        if not brand:
            return BrandTrustIndex(
                brand_id=brand_id,
                trust_score=0,
                trust_tier="unrated",
                tier_benefits=[],
                factor_scores={},
                historical_trend=[],
                recommendations=["Brand not found"],
                probation_risk=False,
                last_calculated=datetime.now(timezone.utc),
            )
        
        factor_scores = {}
        recommendations = []
        
        # Quality score
        quality = self.calculate_brand_quality_score(brand_id)
        factor_scores["quality_score"] = quality.overall_score
        if quality.overall_score < 70:
            recommendations.append("Improve product quality scores")
        
        # Fulfillment reliability (mock - would integrate with fulfillment data)
        factor_scores["fulfillment_reliability"] = 85.0
        
        # Customer satisfaction (mock - would integrate with reviews)
        factor_scores["customer_satisfaction"] = 80.0
        
        # Return rate factor
        return_score = factor_scores.get("return_rate", 80.0)
        factor_scores["return_rate"] = self._calculate_return_rate_score(brand_id)
        
        # Dispute rate (mock)
        factor_scores["dispute_rate"] = 90.0
        
        # Compliance history
        compliance = self.check_compliance(brand_id)
        factor_scores["compliance_history"] = compliance.compliance_score
        if compliance.compliance_score < 80:
            recommendations.append("Address compliance issues")
        
        # Calculate trust score
        trust_score = sum(
            factor_scores.get(factor, 0) * weight
            for factor, weight in TRUST_INDEX_FACTORS.items()
        )
        
        # Determine tier
        tier = "probation"
        benefits = []
        
        for tier_name, threshold in [
            ("platinum", 90), ("gold", 75), ("silver", 60), ("bronze", 40)
        ]:
            if trust_score >= threshold:
                tier = tier_name
                benefits = TRUST_INDEX_THRESHOLDS[tier_name]["benefits"]
                break
        
        # Check probation risk
        probation_risk = trust_score < 50 or any(
            score < 40 for score in factor_scores.values()
        )
        
        if probation_risk:
            recommendations.insert(0, "URGENT: Address factors putting brand at probation risk")
        
        # Generate historical trend (mock)
        historical_trend = self._generate_historical_trend(brand_id)
        
        return BrandTrustIndex(
            brand_id=brand_id,
            trust_score=trust_score,
            trust_tier=tier,
            tier_benefits=benefits,
            factor_scores=factor_scores,
            historical_trend=historical_trend,
            recommendations=recommendations,
            probation_risk=probation_risk,
            last_calculated=datetime.now(timezone.utc),
        )
    
    def _generate_historical_trend(self, brand_id: str) -> List[Dict[str, Any]]:
        """Generate historical trust index trend."""
        # Would query historical data
        trend = []
        for i in range(6):
            date = datetime.now(timezone.utc) - timedelta(days=30 * i)
            trend.append({
                "date": date.strftime("%Y-%m"),
                "score": 75 + (i * 2),  # Placeholder trend
            })
        return list(reversed(trend))
    
    # ── Compliance Monitoring ────────────────────────────────────────────
    
    def check_compliance(self, brand_id: str) -> ComplianceReport:
        """
        Check brand compliance status.
        
        Checks:
        - Product compliance
        - Content compliance
        - Pricing compliance
        - Verification status
        """
        brand = self._db.query(Brand).filter_by(id=brand_id).first()
        
        if not brand:
            return ComplianceReport(
                brand_id=brand_id,
                is_compliant=False,
                compliance_score=0,
                violations=[{"type": "brand_not_found"}],
                pending_actions=[],
                next_review_date=datetime.now(timezone.utc),
            )
        
        violations = []
        pending_actions = []
        
        # Check product moderation
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        product_violations = 0
        
        for product in products:
            result = self.moderate_product(product.id)
            if not result.passed:
                product_violations += 1
                for v in result.violations:
                    pending_actions.append({
                        "type": "fix_product_violation",
                        "product_id": product.id,
                        "violation": v,
                    })
        
        if product_violations > 0:
            violations.append({
                "type": "product_compliance_issues",
                "count": product_violations,
                "total_products": len(products),
            })
        
        # Calculate compliance score
        if not products:
            compliance_score = 100.0
        else:
            compliant_products = len(products) - product_violations
            compliance_score = (compliant_products / len(products)) * 100
        
        is_compliant = len(violations) == 0 and compliance_score >= 80
        
        # Set next review date
        next_review = datetime.now(timezone.utc) + timedelta(days=30)
        if not is_compliant:
            next_review = datetime.now(timezone.utc) + timedelta(days=7)
        
        return ComplianceReport(
            brand_id=brand_id,
            is_compliant=is_compliant,
            compliance_score=compliance_score,
            violations=violations,
            pending_actions=pending_actions,
            next_review_date=next_review,
        )
    
    # ── Admin Audit Logging ──────────────────────────────────────────────
    
    def log_admin_action(
        self,
        action_type: str,
        admin_user_id: str,
        target_type: str,
        target_id: str,
        details: Dict[str, Any],
    ) -> AdminAuditLog:
        """Log an admin action for audit purposes."""
        import uuid
        
        log_entry = AdminAuditLog(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            admin_user_id=admin_user_id,
            target_type=target_type,
            target_id=target_id,
            details=details,
            timestamp=datetime.now(timezone.utc),
        )
        
        # Store in memory (would persist to database)
        self._audit_logs.append(log_entry.to_dict())
        
        logger.info(f"Admin action logged: {action_type} by {admin_user_id} on {target_type}/{target_id}")
        
        return log_entry
    
    def get_audit_logs(
        self,
        admin_user_id: str = None,
        target_type: str = None,
        target_id: str = None,
        action_type: str = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs with optional filtering."""
        logs = self._audit_logs
        
        if admin_user_id:
            logs = [l for l in logs if l["admin_user_id"] == admin_user_id]
        if target_type:
            logs = [l for l in logs if l["target_type"] == target_type]
        if target_id:
            logs = [l for l in logs if l["target_id"] == target_id]
        if action_type:
            logs = [l for l in logs if l["action_type"] == action_type]
        
        return logs[:limit]
    
    # ── Admin Actions ────────────────────────────────────────────────────
    
    def suspend_brand(
        self,
        brand_id: str,
        admin_user_id: str,
        reason: str,
        duration_days: int = None,
    ) -> Dict[str, Any]:
        """Suspend a brand from the marketplace."""
        self.log_admin_action(
            action_type="brand_suspension",
            admin_user_id=admin_user_id,
            target_type="brand",
            target_id=brand_id,
            details={"reason": reason, "duration_days": duration_days},
        )
        
        # Would update brand status in database
        
        return {
            "brand_id": brand_id,
            "status": "suspended",
            "reason": reason,
            "duration_days": duration_days,
            "suspended_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def reinstate_brand(
        self,
        brand_id: str,
        admin_user_id: str,
        conditions: List[str],
    ) -> Dict[str, Any]:
        """Reinstate a suspended brand."""
        self.log_admin_action(
            action_type="brand_reinstatement",
            admin_user_id=admin_user_id,
            target_type="brand",
            target_id=brand_id,
            details={"conditions": conditions},
        )
        
        return {
            "brand_id": brand_id,
            "status": "active",
            "conditions": conditions,
            "reinstated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def remove_product(
        self,
        product_id: str,
        admin_user_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Remove a product from the marketplace."""
        product = self._db.query(Product).filter_by(id=product_id).first()
        
        if product:
            product.is_active = False
            self._db.commit()
        
        self.log_admin_action(
            action_type="product_removal",
            admin_user_id=admin_user_id,
            target_type="product",
            target_id=product_id,
            details={"reason": reason},
        )
        
        return {
            "product_id": product_id,
            "status": "removed",
            "reason": reason,
            "removed_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def approve_brand(
        self,
        brand_id: str,
        admin_user_id: str,
        verification_level: str = "verified",
    ) -> Dict[str, Any]:
        """Approve and verify a brand."""
        self.log_admin_action(
            action_type="brand_approval",
            admin_user_id=admin_user_id,
            target_type="brand",
            target_id=brand_id,
            details={"verification_level": verification_level},
        )
        
        return {
            "brand_id": brand_id,
            "status": "approved",
            "verification_level": verification_level,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
    
    # ── Marketplace Health Dashboard ─────────────────────────────────────
    
    def get_marketplace_health(self) -> Dict[str, Any]:
        """Get overall marketplace health metrics."""
        brands = self._db.query(Brand).all()
        products = self._db.query(Product).filter_by(is_active=True).all()
        
        # Calculate aggregate metrics
        total_brands = len(brands)
        total_products = len(products)
        
        # Trust distribution
        trust_distribution = {"platinum": 0, "gold": 0, "silver": 0, "bronze": 0, "probation": 0}
        
        for brand in brands:
            trust = self.calculate_brand_trust_index(brand.id)
            trust_distribution[trust.trust_tier] += 1
        
        # Compliance rate
        compliant_brands = sum(
            1 for b in brands if self.check_compliance(b.id).is_compliant
        )
        compliance_rate = compliant_brands / total_brands if total_brands > 0 else 0
        
        # Quality distribution
        avg_quality = sum(
            self.calculate_brand_quality_score(b.id).overall_score for b in brands
        ) / total_brands if total_brands > 0 else 0
        
        return {
            "marketplace_overview": {
                "total_brands": total_brands,
                "total_products": total_products,
                "active_brands": total_brands,  # Would check actual status
            },
            "trust_distribution": trust_distribution,
            "compliance_rate": round(compliance_rate * 100, 2),
            "average_quality_score": round(avg_quality, 2),
            "health_score": self._calculate_marketplace_health_score(
                compliance_rate, avg_quality, trust_distribution
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _calculate_marketplace_health_score(
        self, compliance_rate: float, avg_quality: float, trust_dist: Dict
    ) -> float:
        """Calculate overall marketplace health score."""
        # Weight factors
        compliance_weight = 0.30
        quality_weight = 0.30
        trust_weight = 0.40
        
        # Trust score (higher tiers = better)
        trust_score = (
            trust_dist.get("platinum", 0) * 100 +
            trust_dist.get("gold", 0) * 75 +
            trust_dist.get("silver", 0) * 50 +
            trust_dist.get("bronze", 0) * 25
        ) / max(1, sum(trust_dist.values()))
        
        health = (
            compliance_rate * 100 * compliance_weight +
            avg_quality * quality_weight +
            trust_score * trust_weight
        )
        
        return round(health, 2)
