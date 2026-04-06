"""
CONFIT — Notification ML Explainability Module
=============================================
Generates human-readable explanations for delivery time predictions.
Provides feature importance, historical context, and confidence reasoning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import numpy as np


@dataclass
class PredictionExplanation:
    """Human-readable explanation for a prediction."""
    recipient_id: str
    recommended_hour: int
    confidence_score: float
    
    # Core explanation
    reason: str
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Historical context
    historical_context: Optional[str] = None
    similar_recipients_outcome: Optional[str] = None
    
    # Confidence breakdown
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Fallback reasoning (if confidence is low)
    fallback_reason: Optional[str] = None
    
    # Supporting data
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "recipient_id": self.recipient_id,
            "recommended_hour": self.recommended_hour,
            "confidence_score": self.confidence_score,
            "reason": self.reason,
            "feature_importance": self.feature_importance,
            "historical_context": self.historical_context,
            "similar_recipients_outcome": self.similar_recipients_outcome,
            "confidence_breakdown": self.confidence_breakdown,
            "fallback_reason": self.fallback_reason,
            "supporting_data": self.supporting_data,
        }
    
    def to_json(self) -> Dict[str, Any]:
        """Alias for to_dict for JSON serialization."""
        return self.to_dict()


class Explainer:
    """
    Generates human-readable explanations for ML predictions.
    
    Usage:
        explainer = Explainer()
        explanation = explainer.explain_prediction(
            prediction=prediction,
            features=features,
            persona=persona
        )
    """
    
    # Time period descriptions
    TIME_PERIODS = {
        (0, 5): "late night",
        (5, 9): "early morning",
        (9, 12): "morning",
        (12, 14): "midday",
        (14, 17): "afternoon",
        (17, 21): "evening",
        (21, 24): "night",
    }
    
    # Feature importance descriptions
    FEATURE_DESCRIPTIONS = {
        "hourly_open": "Engagement rate at this hour",
        "daily_open": "Engagement rate on this day",
        "overall_open_rate": "Overall engagement rate",
        "consistency_score": "Engagement pattern consistency",
        "recency_weighted_engagement": "Recent engagement activity",
        "peak_hour": "Historical peak engagement hour",
        "peak_day": "Historical peak engagement day",
        "trend_30d": "Engagement trend over 30 days",
        "response_time": "Typical response time",
        "conversion_rate": "Conversion rate",
    }
    
    def __init__(self):
        """Initialize explainer."""
        pass
    
    def explain_prediction(
        self,
        prediction: "DeliveryPrediction",
        features: "RecipientFeatures",
        persona: Optional["PersonaDefinition"] = None,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> PredictionExplanation:
        """
        Generate comprehensive explanation for a prediction.
        
        Args:
            prediction: DeliveryPrediction object
            features: RecipientFeatures used for prediction
            persona: Assigned persona (optional)
            historical_data: Additional historical context
            
        Returns:
            PredictionExplanation with human-readable reasoning
        """
        recommended_hour = prediction.recommended_hour
        confidence = prediction.confidence_score
        
        # Get top features
        feature_importance = self._get_top_features(
            prediction.feature_values,
            prediction.explanation.get("feature_importance", {}),
            features
        )
        
        # Generate main reason
        reason = self._generate_reason(
            recommended_hour,
            confidence,
            features,
            persona
        )
        
        # Generate historical context
        historical_context = self._generate_historical_context(
            recommended_hour,
            features,
            historical_data
        )
        
        # Generate similar recipients outcome
        similar_recipients_outcome = self._generate_similar_recipients_outcome(
            recommended_hour,
            persona,
            historical_data
        )
        
        # Confidence breakdown
        confidence_breakdown = self._compute_confidence_breakdown(
            confidence,
            features,
            persona
        )
        
        # Fallback reason for low confidence
        fallback_reason = None
        if confidence < 0.5:
            fallback_reason = self._generate_fallback_reason(
                confidence,
                features,
                persona
            )
        
        # Supporting data
        supporting_data = {
            "recipient_engagement_profile": {
                "peak_hour": features.peak_hour,
                "peak_day": features.peak_day,
                "overall_open_rate": round(features.overall_open_rate * 100, 1),
                "consistency_score": round(features.consistency_score * 100, 1),
            },
            "hourly_profile": features.hourly_open_rates,
            "recommended_hours": prediction.recommended_hours,
        }
        
        if persona:
            supporting_data["persona"] = {
                "name": persona.name,
                "recipient_count": persona.recipient_count,
                "avg_open_rate": round(persona.avg_open_rate * 100, 1),
            }
        
        return PredictionExplanation(
            recipient_id=prediction.recipient_id,
            recommended_hour=recommended_hour,
            confidence_score=confidence,
            reason=reason,
            feature_importance=feature_importance,
            historical_context=historical_context,
            similar_recipients_outcome=similar_recipients_outcome,
            confidence_breakdown=confidence_breakdown,
            fallback_reason=fallback_reason,
            supporting_data=supporting_data
        )
    
    def _get_top_features(
        self,
        feature_values: Dict[str, float],
        model_importance: Dict[str, float],
        features: "RecipientFeatures"
    ) -> Dict[str, float]:
        """Get top contributing features with descriptions."""
        # Combine model importance with feature values
        combined = {}
        
        for name, importance in model_importance.items():
            if importance > 0.01:  # Threshold for significance
                combined[name] = {
                    "importance": importance,
                    "value": feature_values.get(name, 0),
                    "description": self._describe_feature(name, features)
                }
        
        # Sort by importance
        sorted_features = sorted(
            combined.items(),
            key=lambda x: x[1]["importance"],
            reverse=True
        )[:5]  # Top 5 features
        
        return {
            name: {
                "importance": round(data["importance"] * 100, 1),
                "value": round(data["value"], 3),
                "description": data["description"]
            }
            for name, data in sorted_features
        }
    
    def _describe_feature(self, feature_name: str, features: "RecipientFeatures") -> str:
        """Generate human-readable description for a feature."""
        if feature_name.startswith("hourly_open_"):
            hour = int(feature_name.split("_")[-1])
            rate = features.hourly_open_rates[hour] if hour < 24 else 0
            period = self._get_time_period(hour)
            return f"{period} engagement rate: {round(rate * 100, 1)}%"
        
        elif feature_name.startswith("daily_open_"):
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_idx = int(feature_name.split("_")[-1])
            if day_idx < 7:
                rate = features.daily_open_rates[day_idx]
                return f"{days[day_idx]} engagement rate: {round(rate * 100, 1)}%"
        
        elif feature_name == "overall_open_rate":
            return f"Overall engagement rate: {round(features.overall_open_rate * 100, 1)}%"
        
        elif feature_name == "consistency_score":
            return f"Engagement consistency: {round(features.consistency_score * 100, 1)}%"
        
        elif feature_name == "peak_hour_norm":
            return f"Peak engagement hour: {features.peak_hour or 'N/A'}"
        
        elif feature_name == "recency_weighted_engagement":
            return f"Recent engagement score: {round(features.recency_weighted_engagement * 100, 1)}%"
        
        return feature_name
    
    def _generate_reason(
        self,
        recommended_hour: int,
        confidence: float,
        features: "RecipientFeatures",
        persona: Optional["PersonaDefinition"]
    ) -> str:
        """Generate main reason for the recommendation."""
        period = self._get_time_period(recommended_hour)
        hour_str = self._format_hour(recommended_hour)
        
        # Get engagement at recommended hour vs average
        hourly_rates = features.hourly_open_rates
        recommended_rate = hourly_rates[recommended_hour] if recommended_hour < 24 else 0
        avg_rate = np.mean(hourly_rates) if hourly_rates else 0
        
        if recommended_rate > avg_rate * 1.5 and avg_rate > 0:
            comparison = f"{round(recommended_rate * 100, 1)}% vs {round(avg_rate * 100, 1)}% average"
            comparison_text = f" ({comparison})"
        else:
            comparison_text = ""
        
        if persona:
            return (
                f"Recommended delivery at {hour_str} ({period}) based on your persona "
                f"'{persona.name}' which shows {round(persona.avg_open_rate * 100, 1)}% "
                f"average engagement during this period{comparison_text}."
            )
        
        if features.peak_hour == recommended_hour:
            return (
                f"Recommended delivery at {hour_str} ({period}) - this is your peak "
                f"engagement hour with {round(recommended_rate * 100, 1)}% open rate{comparison_text}."
            )
        
        return (
            f"Recommended delivery at {hour_str} ({period}) based on your engagement "
            f"patterns showing {round(recommended_rate * 100, 1)}% open rate during "
            f"this hour{comparison_text}."
        )
    
    def _generate_historical_context(
        self,
        recommended_hour: int,
        features: "RecipientFeatures",
        historical_data: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate historical context for the recommendation."""
        if not historical_data:
            # Use recipient's own history
            if features.total_notifications_sent < 5:
                return None
            
            rate = features.hourly_open_rates[recommended_hour] if recommended_hour < 24 else 0
            if rate > 0:
                return (
                    f"You have received {features.total_notifications_sent} notifications "
                    f"with {round(features.overall_open_rate * 100, 1)}% overall engagement. "
                    f"At {self._format_hour(recommended_hour)}, your engagement rate is "
                    f"{round(rate * 100, 1)}%."
                )
            return None
        
        # Use provided historical data
        context_parts = []
        
        if "avg_engagement_at_hour" in historical_data:
            avg_eng = historical_data["avg_engagement_at_hour"]
            context_parts.append(
                f"Average engagement at {self._format_hour(recommended_hour)}: "
                f"{round(avg_eng * 100, 1)}%"
            )
        
        if "best_hour_comparison" in historical_data:
            best = historical_data["best_hour_comparison"]
            context_parts.append(
                f"Compared to your best hour ({self._format_hour(best['hour'])}): "
                f"{round(best['rate'] * 100, 1)}%"
            )
        
        return " | ".join(context_parts) if context_parts else None
    
    def _generate_similar_recipients_outcome(
        self,
        recommended_hour: int,
        persona: Optional["PersonaDefinition"],
        historical_data: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate outcome description for similar recipients."""
        if not persona and not historical_data:
            return None
        
        if persona:
            # Use persona statistics
            lift = historical_data.get("persona_lift", 1.0) if historical_data else 1.0
            
            if persona.recipient_type == "customer":
                conv_rate = persona.avg_conversion_rate
                return (
                    f"Similar recipients in the '{persona.name}' persona had "
                    f"{round(conv_rate * 100, 1)}% conversion rate when notified "
                    f"at {self._format_hour(recommended_hour)} "
                    f"({round(lift, 1)}x compared to other times)."
                )
            else:
                resp_time = persona.avg_response_time_min
                if resp_time:
                    return (
                        f"Similar owners in the '{persona.name}' persona responded "
                        f"in {round(resp_time, 1)} minutes on average when notified "
                        f"at {self._format_hour(recommended_hour)}."
                    )
        
        if historical_data and "similar_recipients" in historical_data:
            similar = historical_data["similar_recipients"]
            return (
                f"{similar.get('count', 0)} similar recipients showed "
                f"{round(similar.get('open_rate', 0) * 100, 1)}% engagement "
                f"at {self._format_hour(recommended_hour)}."
            )
        
        return None
    
    def _compute_confidence_breakdown(
        self,
        confidence: float,
        features: "RecipientFeatures",
        persona: Optional["PersonaDefinition"]
    ) -> Dict[str, float]:
        """Break down confidence score into components."""
        breakdown = {
            "data_quality": 0.0,
            "pattern_clarity": 0.0,
            "persona_match": 0.0,
            "recency": 0.0,
        }
        
        # Data quality: based on number of events
        n_events = features.total_notifications_sent
        breakdown["data_quality"] = min(n_events / 50, 1.0) * 0.3
        
        # Pattern clarity: based on consistency
        breakdown["pattern_clarity"] = features.consistency_score * 0.3
        
        # Persona match: based on persona confidence if available
        if persona:
            breakdown["persona_match"] = 0.2
        else:
            breakdown["persona_match"] = 0.1
        
        # Recency: based on recent engagement
        breakdown["recency"] = features.recency_weighted_engagement * 0.2
        
        # Normalize
        total = sum(breakdown.values())
        if total > 0:
            breakdown = {k: v / total for k, v in breakdown.items()}
        
        return {k: round(v, 3) for k, v in breakdown.items()}
    
    def _generate_fallback_reason(
        self,
        confidence: float,
        features: "RecipientFeatures",
        persona: Optional["PersonaDefinition"]
    ) -> str:
        """Generate explanation for low confidence predictions."""
        reasons = []
        
        if features.total_notifications_sent < 10:
            reasons.append("limited notification history")
        
        if features.consistency_score < 0.3:
            reasons.append("variable engagement patterns")
        
        if features.last_engagement_at:
            days_since = (datetime.utcnow() - features.last_engagement_at).days
            if days_since > 30:
                reasons.append("no recent engagement activity")
        
        if not reasons:
            reasons.append("insufficient pattern clarity")
        
        return (
            f"Lower confidence ({round(confidence * 100, 1)}%) due to: "
            f"{', '.join(reasons)}. Consider using default timing or "
            f"gathering more engagement data."
        )
    
    def _get_time_period(self, hour: int) -> str:
        """Get time period description for an hour."""
        for (start, end), period in self.TIME_PERIODS.items():
            if start <= hour < end:
                return period
        return "unknown time"
    
    def _format_hour(self, hour: int) -> str:
        """Format hour in 12-hour format."""
        if hour == 0:
            return "12 AM"
        elif hour < 12:
            return f"{hour} AM"
        elif hour == 12:
            return "12 PM"
        else:
            return f"{hour - 12} PM"


def generate_explanation(
    prediction: "DeliveryPrediction",
    features: "RecipientFeatures",
    persona: Optional["PersonaDefinition"] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate explanation for a prediction.
    
    Args:
        prediction: DeliveryPrediction object
        features: RecipientFeatures used for prediction
        persona: Assigned persona (optional)
        
    Returns:
        Dictionary with explanation
    """
    explainer = Explainer()
    explanation = explainer.explain_prediction(prediction, features, persona)
    return explanation.to_dict()
