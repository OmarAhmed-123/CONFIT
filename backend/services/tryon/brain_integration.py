"""
CONFIT Backend — AI Brain Integration for Virtual Try-On
========================================================
Bidirectional communication between Virtual Try-On and AI Central Brain.

Sends signals:
- Try-on success rate
- User satisfaction signals
- Fit adjustments
- Comparison choices

Receives:
- Size prediction
- Garment ranking
- Visual preference learning
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class TryOnSignalType(Enum):
    """Types of signals sent to AI Brain."""
    TRY_ON_SUCCESS = "try_on_success"
    TRY_ON_FAILURE = "try_on_failure"
    SATISFACTION_RATING = "satisfaction_rating"
    FIT_ADJUSTMENT = "fit_adjustment"
    COMPARISON_CHOICE = "comparison_choice"
    GARMENT_REJECTION = "garment_rejection"
    SIZE_FEEDBACK = "size_feedback"
    QUALITY_FEEDBACK = "quality_feedback"
    SESSION_COMPLETE = "session_complete"


class BrainResponseType(Enum):
    """Types of responses from AI Brain."""
    SIZE_PREDICTION = "size_prediction"
    GARMENT_RANKING = "garment_ranking"
    PREFERENCE_UPDATE = "preference_update"
    STYLE_RECOMMENDATION = "style_recommendation"
    FIT_SUGGESTION = "fit_suggestion"


@dataclass
class TryOnSignal:
    """Signal to send to AI Brain."""
    signal_type: TryOnSignalType
    user_id: str
    session_id: str
    garment_id: str
    
    # Signal data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0


@dataclass
class BrainResponse:
    """Response from AI Brain."""
    response_type: BrainResponseType
    data: Dict[str, Any]
    confidence: float
    reasoning: Optional[str] = None


class TryOnBrainIntegration:
    """
    Manages bidirectional communication between Virtual Try-On and AI Brain.
    
    Usage:
        integration = TryOnBrainIntegration(db_session, ai_brain_service)
        
        # Send signal
        await integration.send_try_on_signal(signal)
        
        # Get predictions
        size_pred = await integration.get_size_prediction(user_id, garment_id)
    """
    
    def __init__(self, db_session, ai_brain_service):
        """
        Initialize integration.
        
        Args:
            db_session: Database session for persistence
            ai_brain_service: AI Brain service instance
        """
        self.db = db_session
        self.brain = ai_brain_service
        
        # Signal queue for batching
        self._signal_queue: List[TryOnSignal] = []
        self._batch_size = 10
    
    # ==========================================
    # Signal Sending (OUTPUT to Brain)
    # ==========================================
    
    async def send_try_on_signal(self, signal: TryOnSignal) -> bool:
        """
        Send a signal to AI Brain.
        
        Args:
            signal: TryOnSignal to send
            
        Returns:
            True if signal was processed successfully
        """
        try:
            # Add to queue
            self._signal_queue.append(signal)
            
            # Process immediately for critical signals
            if signal.signal_type in [
                TryOnSignalType.TRY_ON_FAILURE,
                TryOnSignalType.SATISFACTION_RATING,
                TryOnSignalType.SIZE_FEEDBACK,
            ]:
                await self._process_signal(signal)
            else:
                # Batch process
                if len(self._signal_queue) >= self._batch_size:
                    await self._flush_signal_queue()
            
            # Persist signal
            await self._persist_signal(signal)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send signal: {e}")
            return False
    
    async def track_try_on_success(
        self,
        user_id: str,
        session_id: str,
        garment_id: str,
        quality_score: float,
        processing_time_ms: float,
        body_measurements: Dict[str, Any],
        fit_confidence: float
    ) -> None:
        """
        Track successful try-on completion.
        
        Args:
            user_id: User identifier
            session_id: Try-on session ID
            garment_id: Garment tried on
            quality_score: Result quality score
            processing_time_ms: Processing duration
            body_measurements: Extracted body measurements
            fit_confidence: Fit confidence score
        """
        signal = TryOnSignal(
            signal_type=TryOnSignalType.TRY_ON_SUCCESS,
            user_id=user_id,
            session_id=session_id,
            garment_id=garment_id,
            data={
                'quality_score': quality_score,
                'processing_time_ms': processing_time_ms,
                'fit_confidence': fit_confidence,
            },
            context={
                'body_measurements': body_measurements,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
            confidence=quality_score,
        )
        
        await self.send_try_on_signal(signal)
        
        # Also track as interaction
        self.brain.track_interaction(
            user_id=user_id,
            interaction_type="try_on_success",
            entity_type="garment",
            entity_id=garment_id,
            context={
                'session_id': session_id,
                'quality_score': quality_score,
                'fit_confidence': fit_confidence,
            },
            duration_ms=int(processing_time_ms),
        )
    
    async def track_try_on_failure(
        self,
        user_id: str,
        session_id: str,
        garment_id: str,
        failure_reason: str,
        failure_stage: str,
        user_photo_quality: float
    ) -> None:
        """
        Track failed try-on attempt.
        
        Args:
            user_id: User identifier
            session_id: Try-on session ID
            garment_id: Attempted garment
            failure_reason: Reason for failure
            failure_stage: Pipeline stage where failure occurred
            user_photo_quality: Quality score of user photo
        """
        signal = TryOnSignal(
            signal_type=TryOnSignalType.TRY_ON_FAILURE,
            user_id=user_id,
            session_id=session_id,
            garment_id=garment_id,
            data={
                'failure_reason': failure_reason,
                'failure_stage': failure_stage,
            },
            context={
                'photo_quality': user_photo_quality,
            },
            confidence=0.0,
        )
        
        await self.send_try_on_signal(signal)
        
        # Track as negative interaction
        self.brain.track_interaction(
            user_id=user_id,
            interaction_type="try_on_failure",
            entity_type="garment",
            entity_id=garment_id,
            context={
                'failure_reason': failure_reason,
                'failure_stage': failure_stage,
            },
        )
    
    async def track_satisfaction_rating(
        self,
        user_id: str,
        session_id: str,
        garment_id: str,
        rating: int,  # 1-5 stars
        feedback_text: Optional[str] = None,
        would_purchase: Optional[bool] = None
    ) -> None:
        """
        Track user satisfaction rating for try-on result.
        
        Args:
            user_id: User identifier
            session_id: Try-on session ID
            garment_id: Garment rated
            rating: Star rating (1-5)
            feedback_text: Optional user feedback
            would_purchase: Whether user would purchase
        """
        # Normalize rating to 0-1
        normalized_rating = (rating - 1) / 4
        
        signal = TryOnSignal(
            signal_type=TryOnSignalType.SATISFACTION_RATING,
            user_id=user_id,
            session_id=session_id,
            garment_id=garment_id,
            data={
                'rating': rating,
                'normalized_rating': normalized_rating,
                'would_purchase': would_purchase,
            },
            context={
                'feedback_text': feedback_text,
            },
            confidence=1.0,  # Explicit feedback = high confidence
        )
        
        await self.send_try_on_signal(signal)
        
        # Track as outfit feedback equivalent
        self.brain.track_outfit_feedback(
            user_id=user_id,
            outfit_id=f"tryon_{session_id}",
            accepted=rating >= 3,
            feedback_type="explicit",
            reason=feedback_text,
            context={
                'garment_id': garment_id,
                'rating': rating,
                'would_purchase': would_purchase,
            },
        )
    
    async def track_fit_adjustment(
        self,
        user_id: str,
        session_id: str,
        garment_id: str,
        original_size: str,
        adjusted_size: str,
        adjustment_type: str,  # 'size_up', 'size_down', 'fit_type'
        user_body_profile: Dict[str, Any]
    ) -> None:
        """
        Track fit adjustment made by user.
        
        Args:
            user_id: User identifier
            session_id: Try-on session ID
            garment_id: Garment being adjusted
            original_size: Original recommended size
            adjusted_size: User-selected size
            adjustment_type: Type of adjustment
            user_body_profile: User's body profile data
        """
        signal = TryOnSignal(
            signal_type=TryOnSignalType.FIT_ADJUSTMENT,
            user_id=user_id,
            session_id=session_id,
            garment_id=garment_id,
            data={
                'original_size': original_size,
                'adjusted_size': adjusted_size,
                'adjustment_type': adjustment_type,
            },
            context={
                'body_profile': user_body_profile,
            },
            confidence=0.9,
        )
        
        await self.send_try_on_signal(signal)
        
        # Update size preference learning
        self.brain.track_style_preference(
            user_id=user_id,
            preference_type="size_preference",
            value=adjusted_size,
            source="try_on_adjustment",
            confidence=0.9,
        )
    
    async def track_comparison_choice(
        self,
        user_id: str,
        session_id: str,
        compared_garments: List[str],
        chosen_garment_id: str,
        comparison_duration_ms: float,
        rejection_reasons: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Track user's choice when comparing multiple garments.
        
        Args:
            user_id: User identifier
            session_id: Try-on session ID
            compared_garments: List of garment IDs compared
            chosen_garment_id: Garment user selected
            comparison_duration_ms: Time spent comparing
            rejection_reasons: Reasons for rejecting each garment
        """
        signal = TryOnSignal(
            signal_type=TryOnSignalType.COMPARISON_CHOICE,
            user_id=user_id,
            session_id=session_id,
            garment_id=chosen_garment_id,
            data={
                'chosen_garment': chosen_garment_id,
                'comparison_count': len(compared_garments),
            },
            context={
                'compared_garments': compared_garments,
                'rejection_reasons': rejection_reasons or {},
                'comparison_duration_ms': comparison_duration_ms,
            },
            confidence=0.85,
        )
        
        await self.send_try_on_signal(signal)
        
        # Track choice as preference signal
        self.brain.track_interaction(
            user_id=user_id,
            interaction_type="comparison_choice",
            entity_type="garment",
            entity_id=chosen_garment_id,
            context={
                'alternatives': compared_garments,
                'rejection_reasons': rejection_reasons,
            },
            duration_ms=int(comparison_duration_ms),
        )
    
    async def track_garment_rejection(
        self,
        user_id: str,
        session_id: str,
        garment_id: str,
        rejection_reason: str,
        try_on_count: int,
        quality_score: float
    ) -> None:
        """
        Track when user rejects a try-on result.
        
        Args:
            user_id: User identifier
            session_id: Try-on session ID
            garment_id: Rejected garment
            rejection_reason: Why user rejected
            try_on_count: Number of times tried
            quality_score: Quality score of result
        """
        signal = TryOnSignal(
            signal_type=TryOnSignalType.GARMENT_REJECTION,
            user_id=user_id,
            session_id=session_id,
            garment_id=garment_id,
            data={
                'rejection_reason': rejection_reason,
                'try_on_count': try_on_count,
            },
            context={
                'quality_score': quality_score,
            },
            confidence=0.8,
        )
        
        await self.send_try_on_signal(signal)
        
        # Track as negative feedback
        self.brain.track_outfit_feedback(
            user_id=user_id,
            outfit_id=f"tryon_{session_id}",
            accepted=False,
            feedback_type="explicit",
            reason=rejection_reason,
            context={
                'garment_id': garment_id,
                'try_on_count': try_on_count,
            },
        )
    
    # ==========================================
    # Brain Requests (INPUT from Brain)
    # ==========================================
    
    async def get_size_prediction(
        self,
        user_id: str,
        garment_id: str,
        garment_category: str,
        brand: Optional[str] = None
    ) -> BrainResponse:
        """
        Get size prediction from AI Brain.
        
        Uses user's body profile and purchase history to predict
        optimal size for a garment.
        
        Args:
            user_id: User identifier
            garment_id: Garment to predict size for
            garment_category: Category (tops, pants, etc.)
            brand: Optional brand for brand-specific sizing
            
        Returns:
            BrainResponse with size prediction
        """
        try:
            # Get user's style vector (includes body profile)
            style_vector = self.brain.get_user_style_vector(user_id)
            
            # Get wardrobe context for size history
            wardrobe = self.brain.get_wardrobe_context(user_id)
            
            # Get contextual factors
            context = self.brain.get_contextual_factors(user_id)
            
            # Build prediction context
            prediction_context = {
                'style_vector': style_vector,
                'wardrobe': wardrobe,
                'context': context,
                'garment_category': garment_category,
                'brand': brand,
            }
            
            # In production, this would call a size prediction model
            # For now, use heuristics based on body profile
            dimensions = style_vector.get('dimensions', {})
            
            # Simple heuristic: map body proportions to size
            # This would be replaced with ML model in production
            size_prediction = self._predict_size_heuristic(
                dimensions, garment_category, brand
            )
            
            return BrainResponse(
                response_type=BrainResponseType.SIZE_PREDICTION,
                data={
                    'predicted_size': size_prediction['size'],
                    'confidence': size_prediction['confidence'],
                    'alternatives': size_prediction.get('alternatives', []),
                    'reasoning': size_prediction.get('reasoning'),
                },
                confidence=size_prediction['confidence'],
                reasoning=size_prediction.get('reasoning'),
            )
            
        except Exception as e:
            logger.error(f"Size prediction failed: {e}")
            return BrainResponse(
                response_type=BrainResponseType.SIZE_PREDICTION,
                data={'predicted_size': 'M', 'confidence': 0.5},
                confidence=0.5,
            )
    
    def _predict_size_heuristic(
        self,
        dimensions: Dict[str, float],
        category: str,
        brand: Optional[str]
    ) -> Dict[str, Any]:
        """Heuristic size prediction based on style dimensions."""
        # This is a placeholder - production would use ML model
        
        # Use dimension scores as proxy for body type
        # In reality, would use actual body measurements
        
        # Default prediction
        return {
            'size': 'M',
            'confidence': 0.7,
            'alternatives': ['S', 'L'],
            'reasoning': 'Based on your profile, medium size is recommended',
        }
    
    async def get_garment_ranking(
        self,
        user_id: str,
        garment_ids: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> BrainResponse:
        """
        Get personalized ranking of garments.
        
        Ranks garments based on:
        - Style alignment
        - Size match probability
        - Past preferences
        - Visual similarity to liked items
        
        Args:
            user_id: User identifier
            garment_ids: List of garment IDs to rank
            context: Optional context (occasion, budget, etc.)
            
        Returns:
            BrainResponse with ranked garment list
        """
        try:
            # Get user's style vector
            style_vector = self.brain.get_user_style_vector(user_id)
            
            # Get wardrobe for similarity matching
            wardrobe = self.brain.get_wardrobe_context(user_id)
            
            # Get occasion context if provided
            occasion = context.get('occasion') if context else None
            
            # Generate recommendations with scores
            recommendations = self.brain.generate_outfit_recommendations(
                user_id=user_id,
                occasion=occasion,
                budget=context.get('budget') if context else None,
                limit=len(garment_ids),
            )
            
            # Rank provided garments based on recommendation scores
            ranked = self._rank_garments(
                garment_ids, recommendations, style_vector
            )
            
            return BrainResponse(
                response_type=BrainResponseType.GARMENT_RANKING,
                data={
                    'ranked_garments': ranked,
                    'total_count': len(ranked),
                },
                confidence=style_vector.get('signal_strength', 0) / 100,
            )
            
        except Exception as e:
            logger.error(f"Garment ranking failed: {e}")
            return BrainResponse(
                response_type=BrainResponseType.GARMENT_RANKING,
                data={'ranked_garments': [{'id': gid, 'score': 0.5} for gid in garment_ids]},
                confidence=0.3,
            )
    
    def _rank_garments(
        self,
        garment_ids: List[str],
        recommendations: List[Dict],
        style_vector: Dict
    ) -> List[Dict[str, Any]]:
        """Rank garments based on recommendations and style alignment."""
        ranked = []
        
        for gid in garment_ids:
            # Calculate score based on style alignment
            # In production, would use actual garment features
            
            # Default score
            score = 0.5
            
            # Check if in recommendations
            for rec in recommendations:
                if gid in str(rec.get('items', [])):
                    score = rec.get('confidence', 0.5)
                    break
            
            ranked.append({
                'id': gid,
                'score': score,
                'style_alignment': score,  # Simplified
            })
        
        # Sort by score descending
        ranked.sort(key=lambda x: x['score'], reverse=True)
        
        return ranked
    
    async def get_visual_preference_learning(
        self,
        user_id: str,
        recent_interactions: int = 20
    ) -> BrainResponse:
        """
        Get learned visual preferences from try-on history.
        
        Analyzes patterns in:
        - Garment styles tried
        - Colors preferred
        - Fit types chosen
        - Rejection patterns
        
        Args:
            user_id: User identifier
            recent_interactions: Number of recent interactions to analyze
            
        Returns:
            BrainResponse with learned preferences
        """
        try:
            # Get style vector
            style_vector = self.brain.get_user_style_vector(user_id)
            
            # Get confidence breakdown
            confidence = self.brain.get_confidence_breakdown(user_id)
            
            # Extract visual preferences
            visual_prefs = {
                'preferred_colors': style_vector.get('colors', {}).get('preferred', {}),
                'avoided_colors': style_vector.get('colors', {}).get('avoided', []),
                'preferred_brands': style_vector.get('brands', {}),
                'style_dimensions': style_vector.get('dimensions', {}),
                'archetype': style_vector.get('archetype'),
                'confidence_level': style_vector.get('confidence_level'),
            }
            
            # Add trend adaptation
            trend_sensitivity = confidence.get('experimentation_level', 0.5)
            adapted_trends = self.brain.adapt_to_trends(style_vector, trend_sensitivity)
            
            visual_prefs['trend_adaptation'] = adapted_trends
            
            return BrainResponse(
                response_type=BrainResponseType.PREFERENCE_UPDATE,
                data=visual_prefs,
                confidence=style_vector.get('archetype_confidence', 0.5),
                reasoning=f"Learned from {style_vector.get('signal_strength', 0)} interactions",
            )
            
        except Exception as e:
            logger.error(f"Visual preference learning failed: {e}")
            return BrainResponse(
                response_type=BrainResponseType.PREFERENCE_UPDATE,
                data={},
                confidence=0.3,
            )
    
    async def get_fit_suggestion(
        self,
        user_id: str,
        garment_id: str,
        garment_metadata: Dict[str, Any],
        body_measurements: Dict[str, Any]
    ) -> BrainResponse:
        """
        Get fit suggestion from AI Brain.
        
        Suggests optimal fit type based on:
        - Body proportions
        - Garment style
        - Past fit preferences
        
        Args:
            user_id: User identifier
            garment_id: Garment to suggest fit for
            garment_metadata: Garment details
            body_measurements: User's body measurements
            
        Returns:
            BrainResponse with fit suggestion
        """
        try:
            # Get style preferences
            style_vector = self.brain.get_user_style_vector(user_id)
            
            # Analyze body proportions
            proportions = {
                'shoulder_to_hip': body_measurements.get('shoulder_to_hip_ratio', 1.0),
                'torso_to_leg': body_measurements.get('torso_to_leg_ratio', 1.0),
            }
            
            # Determine optimal fit
            fit_suggestion = self._suggest_fit(
                proportions, garment_metadata, style_vector
            )
            
            return BrainResponse(
                response_type=BrainResponseType.FIT_SUGGESTION,
                data={
                    'recommended_fit': fit_suggestion['fit_type'],
                    'recommended_size': fit_suggestion['size'],
                    'confidence': fit_suggestion['confidence'],
                    'adjustments': fit_suggestion.get('adjustments', []),
                },
                confidence=fit_suggestion['confidence'],
                reasoning=fit_suggestion.get('reasoning'),
            )
            
        except Exception as e:
            logger.error(f"Fit suggestion failed: {e}")
            return BrainResponse(
                response_type=BrainResponseType.FIT_SUGGESTION,
                data={'recommended_fit': 'regular', 'confidence': 0.5},
                confidence=0.5,
            )
    
    def _suggest_fit(
        self,
        proportions: Dict[str, float],
        garment_metadata: Dict,
        style_vector: Dict
    ) -> Dict[str, Any]:
        """Suggest fit type based on body and preferences."""
        # Placeholder logic - production would use ML model
        
        shoulder_hip = proportions['shoulder_to_hip']
        
        # Body type considerations
        if shoulder_hip > 1.4:
            # Broad shoulders
            return {
                'fit_type': 'regular',
                'size': 'L',
                'confidence': 0.7,
                'adjustments': ['Consider relaxed fit for comfort'],
                'reasoning': 'Regular fit accommodates broader shoulders',
            }
        elif shoulder_hip < 1.1:
            # Narrower shoulders
            return {
                'fit_type': 'fitted',
                'size': 'S',
                'confidence': 0.7,
                'adjustments': ['Fitted styles will flatter your frame'],
                'reasoning': 'Fitted styles complement your proportions',
            }
        else:
            # Balanced proportions
            return {
                'fit_type': 'regular',
                'size': 'M',
                'confidence': 0.8,
                'reasoning': 'Regular fit suits your balanced proportions',
            }
    
    # ==========================================
    # Internal Methods
    # ==========================================
    
    async def _process_signal(self, signal: TryOnSignal) -> None:
        """Process a single signal through AI Brain."""
        try:
            # Route to appropriate brain method
            if signal.signal_type == TryOnSignalType.TRY_ON_SUCCESS:
                self._process_success_signal(signal)
            elif signal.signal_type == TryOnSignalType.TRY_ON_FAILURE:
                self._process_failure_signal(signal)
            elif signal.signal_type == TryOnSignalType.SATISFACTION_RATING:
                self._process_satisfaction_signal(signal)
            elif signal.signal_type == TryOnSignalType.FIT_ADJUSTMENT:
                self._process_fit_adjustment_signal(signal)
            elif signal.signal_type == TryOnSignalType.COMPARISON_CHOICE:
                self._process_comparison_signal(signal)
            elif signal.signal_type == TryOnSignalType.GARMENT_REJECTION:
                self._process_rejection_signal(signal)
                
        except Exception as e:
            logger.error(f"Signal processing failed: {e}")
    
    def _process_success_signal(self, signal: TryOnSignal) -> None:
        """Process try-on success signal."""
        # Update engagement metrics
        self.brain.track_interaction(
            user_id=signal.user_id,
            interaction_type="try_on_complete",
            entity_type="garment",
            entity_id=signal.garment_id,
            context=signal.context,
        )
    
    def _process_failure_signal(self, signal: TryOnSignal) -> None:
        """Process try-on failure signal."""
        # Track for UX improvement
        self.brain.track_interaction(
            user_id=signal.user_id,
            interaction_type="try_on_failed",
            entity_type="garment",
            entity_id=signal.garment_id,
            context={
                'failure_reason': signal.data.get('failure_reason'),
                'failure_stage': signal.data.get('failure_stage'),
            },
        )
    
    def _process_satisfaction_signal(self, signal: TryOnSignal) -> None:
        """Process satisfaction rating signal."""
        rating = signal.data.get('rating', 3)
        
        # Update preferences based on rating
        if rating >= 4:
            # High satisfaction - reinforce preference
            self.brain.track_style_preference(
                user_id=signal.user_id,
                preference_type="liked_garment",
                value=signal.garment_id,
                source="try_on_rating",
                confidence=signal.data.get('normalized_rating', 0.75),
            )
        elif rating <= 2:
            # Low satisfaction - track avoidance
            self.brain.track_style_preference(
                user_id=signal.user_id,
                preference_type="disliked_garment",
                value=signal.garment_id,
                source="try_on_rating",
                confidence=1 - signal.data.get('normalized_rating', 0.25),
            )
    
    def _process_fit_adjustment_signal(self, signal: TryOnSignal) -> None:
        """Process fit adjustment signal."""
        # Learn size preferences
        adjusted_size = signal.data.get('adjusted_size')
        
        self.brain.track_style_preference(
            user_id=signal.user_id,
            preference_type="preferred_size",
            value=adjusted_size,
            source="fit_adjustment",
            confidence=signal.confidence,
        )
    
    def _process_comparison_signal(self, signal: TryOnSignal) -> None:
        """Process comparison choice signal."""
        # Track preference for chosen garment
        self.brain.track_style_preference(
            user_id=signal.user_id,
            preference_type="comparison_winner",
            value=signal.garment_id,
            source="comparison",
            confidence=signal.confidence,
        )
    
    def _process_rejection_signal(self, signal: TryOnSignal) -> None:
        """Process garment rejection signal."""
        # Track as negative preference
        self.brain.track_style_preference(
            user_id=signal.user_id,
            preference_type="rejected_garment",
            value=signal.garment_id,
            source="try_on_rejection",
            confidence=signal.confidence,
        )
    
    async def _flush_signal_queue(self) -> None:
        """Flush queued signals to AI Brain."""
        if not self._signal_queue:
            return
        
        # Process all queued signals
        for signal in self._signal_queue:
            await self._process_signal(signal)
        
        # Clear queue
        self._signal_queue.clear()
        
        logger.debug("Signal queue flushed")
    
    async def _persist_signal(self, signal: TryOnSignal) -> None:
        """Persist signal to database for analytics."""
        try:
            from models.profile_models import UserBehaviorSignal
            
            db_signal = UserBehaviorSignal(
                user_id=signal.user_id,
                signal_type=signal.signal_type.value,
                entity_type="garment",
                entity_id=signal.garment_id,
                context={
                    'session_id': signal.session_id,
                    'data': signal.data,
                    'context': signal.context,
                    'confidence': signal.confidence,
                },
            )
            
            self.db.add(db_signal)
            self.db.commit()
            
        except Exception as e:
            logger.warning(f"Failed to persist signal: {e}")
            self.db.rollback()


# ==========================================
# Convenience Functions
# ==========================================

def create_brain_integration(db_session, ai_brain_service=None):
    """
    Create TryOnBrainIntegration instance.
    
    Args:
        db_session: Database session
        ai_brain_service: Optional AI Brain service (will be created if None)
        
    Returns:
        TryOnBrainIntegration instance
    """
    if ai_brain_service is None:
        from services.ai_brain_service import AIBrainService
        ai_brain_service = AIBrainService(db_session)
    
    return TryOnBrainIntegration(db_session, ai_brain_service)
