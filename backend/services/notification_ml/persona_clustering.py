"""
CONFIT — Notification ML Persona Clustering
===========================================
Segments recipients into behavioral personas using K-means clustering.
Creates persona definitions based on engagement patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score
import joblib
import os


# Persona name templates based on engagement patterns
PERSONA_NAME_TEMPLATES = {
    "early_morning": {
        "name": "Early Morning Engagers",
        "description": "Recipients who engage most actively with notifications in the early morning hours (6-9 AM). Typically check notifications before starting their day."
    },
    "mid_morning": {
        "name": "Mid-Morning Responders",
        "description": "Recipients who engage most during mid-morning hours (9-11 AM). Often professionals checking notifications during work breaks."
    },
    "lunch_time": {
        "name": "Lunch Time Browsers",
        "description": "Recipients who engage during lunch hours (11 AM-1 PM). Check notifications during their midday break."
    },
    "afternoon": {
        "name": "Afternoon Actives",
        "description": "Recipients who engage most in the afternoon (1-5 PM). Typically respond during work hours."
    },
    "evening": {
        "name": "Evening Browsers",
        "description": "Recipients who engage most in the evening (5-9 PM). Check notifications after work hours."
    },
    "night_owl": {
        "name": "Night Owl Engagers",
        "description": "Recipients who engage late at night (9 PM-2 AM). Active during late evening hours."
    },
    "weekend_warrior": {
        "name": "Weekend Responders",
        "description": "Recipients who engage primarily on weekends. Low weekday engagement but active on Saturday and Sunday."
    },
    "always_on": {
        "name": "Always-On Processors",
        "description": "Recipients with consistent engagement throughout the day. Quick to respond at any hour."
    },
    "selective_reader": {
        "name": "Selective Readers",
        "description": "Recipients with low overall engagement but high response quality. Only open relevant notifications."
    },
    "highly_engaged": {
        "name": "Highly Engaged Power Users",
        "description": "Recipients with very high engagement rates across all channels and times. Respond quickly to most notifications."
    },
    "low_engagement": {
        "name": "Low Engagement Recipients",
        "description": "Recipients with minimal notification interaction. May prefer fewer notifications or different channels."
    },
    "quick_responder": {
        "name": "Quick Responders",
        "description": "Owners who respond to order notifications very quickly. High priority for time-sensitive notifications."
    },
    "delayed_responder": {
        "name": "Delayed Responders",
        "description": "Owners who take longer to respond. May benefit from advance notifications for orders."
    }
}


@dataclass
class PersonaDefinition:
    """Definition of a behavioral persona."""
    id: str
    name: str
    description: str
    recipient_type: str  # 'customer' or 'owner'
    
    # Characteristics
    characteristics: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    recipient_count: int = 0
    avg_open_rate: float = 0.0
    avg_click_rate: float = 0.0
    avg_conversion_rate: float = 0.0
    avg_response_time_min: Optional[float] = None
    
    # Model metadata
    model_version: str = ""
    cluster_id: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "recipient_type": self.recipient_type,
            "characteristics": self.characteristics,
            "recipient_count": self.recipient_count,
            "avg_open_rate": self.avg_open_rate,
            "avg_click_rate": self.avg_click_rate,
            "avg_conversion_rate": self.avg_conversion_rate,
            "avg_response_time_min": self.avg_response_time_min,
            "model_version": self.model_version,
            "cluster_id": self.cluster_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class ClusteringResult:
    """Result of persona clustering."""
    personas: List[PersonaDefinition]
    recipient_assignments: Dict[str, Tuple[str, float]]  # recipient_id -> (persona_id, confidence)
    metrics: Dict[str, float]
    model_version: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "personas": [p.to_dict() for p in self.personas],
            "recipient_assignments": {
                k: {"persona_id": v[0], "confidence": v[1]}
                for k, v in self.recipient_assignments.items()
            },
            "metrics": self.metrics,
            "model_version": self.model_version,
        }


class PersonaClusterer:
    """
    Clusters recipients into behavioral personas using K-means.
    
    Usage:
        clusterer = PersonaClusterer(n_personas=5)
        result = clusterer.fit_predict(features_list)
        clusterer.save_model("models/persona_clustering_v1.pkl")
    """
    
    def __init__(
        self,
        n_personas: int = 5,
        min_personas: int = 3,
        max_personas: int = 8,
        random_state: int = 42,
        model_version: Optional[str] = None,
        auto_select_k: Optional[bool] = None,
    ):
        """
        Initialize persona clusterer.
        
        Args:
            n_personas: Number of personas to create (if auto_select=False)
            min_personas: Minimum personas for auto-selection
            max_personas: Maximum personas for auto-selection
            random_state: Random seed for reproducibility
            model_version: Version string for the model
        """
        self.n_personas = n_personas
        self.min_personas = min_personas
        self.max_personas = max_personas
        self.random_state = random_state
        self.model_version = model_version or f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        # Backward-compatible flag accepted by tests/callers; fit_predict controls behavior.
        self.auto_select_k = auto_select_k
        
        self.model: Optional[KMeans] = None
        self.scaler: Optional[StandardScaler] = None
        self._models_by_type: Dict[str, KMeans] = {}
        self._scalers_by_type: Dict[str, StandardScaler] = {}
        self.personas: List[PersonaDefinition] = []
        self.feature_names: List[str] = []
        self.is_fitted: bool = False
    
    def fit_predict(
        self,
        features_list: List["RecipientFeatures"],
        auto_select_k: bool = True
    ) -> ClusteringResult:
        """
        Fit clustering model and predict persona assignments.
        
        Args:
            features_list: List of RecipientFeatures objects
            auto_select_k: Whether to automatically select optimal number of clusters
            
        Returns:
            ClusteringResult with personas and assignments
        """
        if len(features_list) < self.min_personas * 10:
            raise ValueError(f"Need at least {self.min_personas * 10} recipients for clustering")
        
        # Convert to feature matrix
        X = np.array([f.to_feature_vector() for f in features_list])
        recipient_ids = [f.recipient_id for f in features_list]
        recipient_types = list(set(f.recipient_type for f in features_list))
        
        if len(recipient_types) > 1:
            # Cluster each recipient type separately
            return self._fit_predict_multi_type(features_list, X, recipient_ids, recipient_types)
        
        recipient_type = recipient_types[0]
        
        # Standardize features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Select optimal k if auto_select
        if auto_select_k:
            self.n_personas = self._select_optimal_k(X_scaled)
        
        # Fit K-means
        self.model = KMeans(
            n_clusters=self.n_personas,
            random_state=self.random_state,
            n_init=10,
            max_iter=300
        )
        
        labels = self.model.fit_predict(X_scaled)
        self.is_fitted = True
        
        # Compute distances for confidence scores
        distances = self.model.transform(X_scaled)
        min_distances = distances.min(axis=1)
        max_distance = min_distances.max() if min_distances.max() > 0 else 1
        confidence_scores = 1 - (min_distances / max_distance)
        
        # Create persona definitions
        self.personas = self._create_persona_definitions(
            features_list, labels, recipient_type
        )
        
        # Create recipient assignments
        recipient_assignments = {}
        for i, recipient_id in enumerate(recipient_ids):
            persona_id = self.personas[labels[i]].id
            recipient_assignments[recipient_id] = (persona_id, float(confidence_scores[i]))
        
        # Compute metrics
        metrics = {
            "silhouette_score": float(silhouette_score(X_scaled, labels)),
            "calinski_harabasz_score": float(calinski_harabasz_score(X_scaled, labels)),
            "inertia": float(self.model.inertia_),
            "n_clusters": self.n_personas,
            "n_recipients": len(features_list)
        }
        
        return ClusteringResult(
            personas=self.personas,
            recipient_assignments=recipient_assignments,
            metrics=metrics,
            model_version=self.model_version
        )
    
    def _fit_predict_multi_type(
        self,
        features_list: List["RecipientFeatures"],
        X: np.ndarray,
        recipient_ids: List[str],
        recipient_types: List[str]
    ) -> ClusteringResult:
        """Cluster each recipient type separately."""
        all_personas: List[PersonaDefinition] = []
        all_assignments: Dict[str, Tuple[str, float]] = {}
        all_metrics: Dict[str, float] = {}
        self._models_by_type = {}
        self._scalers_by_type = {}
        
        for rtype in recipient_types:
            # Filter by type
            indices = [i for i, f in enumerate(features_list) if f.recipient_type == rtype]
            X_type = X[indices]
            ids_type = [recipient_ids[i] for i in indices]
            
            # Scale
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_type)
            
            # Select k
            n_clusters = self._select_optimal_k(X_scaled)
            
            # Fit
            model = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
            labels = model.fit_predict(X_scaled)
            self._models_by_type[rtype] = model
            self._scalers_by_type[rtype] = scaler
            
            # Compute confidence
            distances = model.transform(X_scaled)
            min_distances = distances.min(axis=1)
            max_distance = min_distances.max() if min_distances.max() > 0 else 1
            confidence_scores = 1 - (min_distances / max_distance)
            
            # Create personas for this type/cluster count
            type_features = [features_list[i] for i in indices]
            personas = self._create_persona_definitions_with_n_clusters(
                type_features, labels, rtype, n_clusters
            )
            
            # Prefix persona IDs with type
            for p in personas:
                p.id = f"{rtype}_{p.id}"
            all_personas.extend(personas)
            
            # Assignments
            for i, rid in enumerate(ids_type):
                persona_id = personas[labels[i]].id
                all_assignments[rid] = (persona_id, float(confidence_scores[i]))
            
            # Metrics
            all_metrics[f"{rtype}_silhouette"] = float(silhouette_score(X_scaled, labels))
            all_metrics[f"{rtype}_n_clusters"] = n_clusters
        
        silhouette_keys = [k for k in all_metrics.keys() if k.endswith("_silhouette")]
        if silhouette_keys:
            all_metrics["silhouette_score"] = float(np.mean([all_metrics[k] for k in silhouette_keys]))
        all_metrics["n_recipients"] = len(features_list)
        self.personas = all_personas
        # Provide a default model/scaler (prefer customer) for generic access.
        if "customer" in self._models_by_type:
            self.model = self._models_by_type["customer"]
            self.scaler = self._scalers_by_type.get("customer")
        elif self._models_by_type:
            first_type = next(iter(self._models_by_type.keys()))
            self.model = self._models_by_type[first_type]
            self.scaler = self._scalers_by_type.get(first_type)
        self.is_fitted = True
        
        return ClusteringResult(
            personas=all_personas,
            recipient_assignments=all_assignments,
            metrics=all_metrics,
            model_version=self.model_version
        )
    
    def _select_optimal_k(self, X: np.ndarray) -> int:
        """Select optimal number of clusters using elbow method and silhouette score."""
        k_range = range(self.min_personas, min(self.max_personas + 1, len(X) // 10 + 1))
        
        if len(k_range) < 2:
            return self.min_personas
        
        inertias = []
        silhouettes = []
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=5)
            labels = kmeans.fit_predict(X)
            inertias.append(kmeans.inertia_)
            silhouettes.append(silhouette_score(X, labels))
        
        # Find elbow point (simplified: max silhouette score)
        best_k = list(k_range)[np.argmax(silhouettes)]
        
        return best_k
    
    def _create_persona_definitions(
        self,
        features_list: List["RecipientFeatures"],
        labels: np.ndarray,
        recipient_type: str
    ) -> List[PersonaDefinition]:
        """Create persona definitions from cluster assignments."""
        return self._create_persona_definitions_with_n_clusters(
            features_list, labels, recipient_type, self.n_personas
        )

    def _create_persona_definitions_with_n_clusters(
        self,
        features_list: List["RecipientFeatures"],
        labels: np.ndarray,
        recipient_type: str,
        n_clusters: int,
    ) -> List[PersonaDefinition]:
        """Create persona definitions from cluster assignments with explicit cluster count."""
        personas = []
        
        for cluster_id in range(n_clusters):
            # Get features for this cluster
            cluster_mask = labels == cluster_id
            cluster_features = [f for i, f in enumerate(features_list) if cluster_mask[i]]
            
            if not cluster_features:
                continue
            
            # Compute aggregate characteristics
            characteristics = self._compute_cluster_characteristics(cluster_features)
            
            # Generate persona name
            persona_template = self._select_persona_template(characteristics, recipient_type)
            
            persona = PersonaDefinition(
                id=f"persona_{cluster_id}",
                name=persona_template["name"],
                description=persona_template["description"],
                recipient_type=recipient_type,
                characteristics=characteristics,
                recipient_count=len(cluster_features),
                avg_open_rate=float(np.mean([f.overall_open_rate for f in cluster_features])),
                avg_click_rate=float(np.mean([f.overall_click_rate for f in cluster_features])),
                model_version=self.model_version,
                cluster_id=cluster_id
            )
            
            # Add type-specific metrics
            if recipient_type == "owner":
                response_times = [f.avg_response_time_min for f in cluster_features if f.avg_response_time_min]
                if response_times:
                    persona.avg_response_time_min = float(np.mean(response_times))
            else:
                conversions = [f.conversion_rate_30d for f in cluster_features]
                persona.avg_conversion_rate = float(np.mean(conversions))
            
            personas.append(persona)
        
        return personas
    
    def _compute_cluster_characteristics(
        self,
        features_list: List["RecipientFeatures"]
    ) -> Dict[str, Any]:
        """Compute aggregate characteristics for a cluster."""
        # Peak hours (most common peak hour)
        peak_hours = [f.peak_hour for f in features_list if f.peak_hour is not None]
        peak_hour = int(np.median(peak_hours)) if peak_hours else None
        
        # Peak days
        peak_days = [f.peak_day for f in features_list if f.peak_day is not None]
        peak_day = int(np.median(peak_days)) if peak_days else None
        
        # Average hourly profile
        hourly_open_rates = np.mean([f.hourly_open_rates for f in features_list], axis=0).tolist()
        
        # Engagement pattern classification
        engagement_pattern = self._classify_engagement_pattern(hourly_open_rates, peak_hour)
        
        # Preferred channel
        channels = [f.preferred_channel for f in features_list if f.preferred_channel]
        preferred_channel = max(set(channels), key=channels.count) if channels else "in_app"
        
        # Consistency
        consistency = float(np.mean([f.consistency_score for f in features_list]))
        
        return {
            "peak_hour": peak_hour,
            "peak_day": peak_day,
            "peak_hours": self._get_peak_hours(hourly_open_rates),
            "peak_days": self._get_peak_days(features_list),
            "avg_open_rate": float(np.mean([f.overall_open_rate for f in features_list])),
            "avg_click_rate": float(np.mean([f.overall_click_rate for f in features_list])),
            "consistency_score": consistency,
            "preferred_channel": preferred_channel,
            "engagement_pattern": engagement_pattern,
            "hourly_open_rates": hourly_open_rates,
        }
    
    def _classify_engagement_pattern(
        self,
        hourly_rates: List[float],
        peak_hour: Optional[int]
    ) -> str:
        """Classify engagement pattern based on hourly profile."""
        if peak_hour is None:
            return "low_engagement"
        
        # Morning (6-11)
        morning_rate = np.mean(hourly_rates[6:12])
        # Afternoon (12-17)
        afternoon_rate = np.mean(hourly_rates[12:18])
        # Evening (18-23)
        evening_rate = np.mean(hourly_rates[18:24])
        # Night (0-5)
        night_rate = np.mean(hourly_rates[0:6])
        
        # Check for consistent engagement
        rates = [morning_rate, afternoon_rate, evening_rate, night_rate]
        if max(rates) < 0.1:
            return "low_engagement"
        
        cv = np.std(rates) / (np.mean(rates) + 1e-9)
        if cv < 0.3:
            return "always_on"
        
        # Determine pattern based on peak time
        if 6 <= peak_hour < 9:
            return "early_morning"
        elif 9 <= peak_hour < 12:
            return "mid_morning"
        elif 12 <= peak_hour < 14:
            return "lunch_time"
        elif 14 <= peak_hour < 18:
            return "afternoon"
        elif 18 <= peak_hour < 22:
            return "evening"
        else:
            return "night_owl"
    
    def _get_peak_hours(self, hourly_rates: List[float], top_n: int = 3) -> List[int]:
        """Get top N peak hours."""
        indices = np.argsort(hourly_rates)[-top_n:][::-1]
        return [int(i) for i in indices if hourly_rates[i] > 0]
    
    def _get_peak_days(self, features_list: List["RecipientFeatures"]) -> List[int]:
        """Get most common peak days."""
        days = [f.peak_day for f in features_list if f.peak_day is not None]
        if not days:
            return []
        
        # Return most common days
        day_counts = {}
        for d in days:
            day_counts[d] = day_counts.get(d, 0) + 1
        
        sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)
        return [d[0] for d in sorted_days[:3]]
    
    def _select_persona_template(
        self,
        characteristics: Dict[str, Any],
        recipient_type: str
    ) -> Dict[str, str]:
        """Select appropriate persona name template."""
        pattern = characteristics.get("engagement_pattern", "low_engagement")
        
        # Check for owner-specific patterns
        if recipient_type == "owner":
            response_time = characteristics.get("avg_response_time_min")
            if response_time is not None:
                if response_time < 15:
                    return PERSONA_NAME_TEMPLATES["quick_responder"]
                elif response_time > 60:
                    return PERSONA_NAME_TEMPLATES["delayed_responder"]
        
        # Check for high engagement
        if characteristics.get("avg_open_rate", 0) > 0.7:
            return PERSONA_NAME_TEMPLATES["highly_engaged"]
        
        # Use pattern-based template
        if pattern in PERSONA_NAME_TEMPLATES:
            return PERSONA_NAME_TEMPLATES[pattern]
        
        return {
            "name": f"Persona Group {characteristics.get('peak_hour', 'Unknown')}",
            "description": "A distinct group of recipients with unique engagement patterns."
        }
    
    def predict_persona(
        self,
        features: "RecipientFeatures"
    ) -> Tuple[str, float]:
        """
        Predict persona for a single recipient.
        
        Args:
            features: RecipientFeatures object
            
        Returns:
            Tuple of (persona_id, confidence_score)
        """
        model = self.model
        scaler = self.scaler
        if features.recipient_type in self._models_by_type:
            model = self._models_by_type[features.recipient_type]
            scaler = self._scalers_by_type.get(features.recipient_type)

        if model is None or scaler is None:
            raise ValueError("Model not fitted. Call fit_predict first.")
        
        X = features.to_feature_vector().reshape(1, -1)
        X_scaled = scaler.transform(X)
        
        label = model.predict(X_scaled)[0]
        
        # Compute confidence
        distances = model.transform(X_scaled)
        min_distance = distances.min()
        max_distance = float(np.max(distances)) if distances.size else 1.0
        confidence = 1 - (min_distance / (max_distance + 1e-9))
        confidence = float(max(0.0, min(1.0, confidence)))
        
        persona_id = self.personas[label].id
        return persona_id, float(confidence)
    
    def save_model(self, path: str) -> None:
        """Save model and scaler to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "personas": [p.to_dict() for p in self.personas],
            "n_personas": self.n_personas,
            "model_version": self.model_version,
            "random_state": self.random_state,
        }
        
        joblib.dump(model_data, path)
    
    def load_model(self, path: str) -> None:
        """Load model and scaler from disk."""
        model_data = joblib.load(path)
        
        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.n_personas = model_data["n_personas"]
        self.model_version = model_data["model_version"]
        self.random_state = model_data.get("random_state", 42)
        
        # Reconstruct personas
        self.personas = []
        for p_dict in model_data["personas"]:
            persona = PersonaDefinition(
                id=p_dict["id"],
                name=p_dict["name"],
                description=p_dict["description"],
                recipient_type=p_dict["recipient_type"],
                characteristics=p_dict["characteristics"],
                recipient_count=p_dict["recipient_count"],
                avg_open_rate=p_dict["avg_open_rate"],
                avg_click_rate=p_dict["avg_click_rate"],
                avg_conversion_rate=p_dict.get("avg_conversion_rate", 0),
                avg_response_time_min=p_dict.get("avg_response_time_min"),
                model_version=p_dict["model_version"],
                cluster_id=p_dict["cluster_id"],
            )
            self.personas.append(persona)
    
    def get_persona_by_id(self, persona_id: str) -> Optional[PersonaDefinition]:
        """Get persona definition by ID."""
        for persona in self.personas:
            if persona.id == persona_id:
                return persona
        return None
