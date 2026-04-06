"""
CONFIT Backend — Enhanced Virtual Stylist Service
=================================================
Advanced AI-powered styling with:
- Conversational memory and context
- Intent refinement and clarification
- Contextual styling recommendations
- Confidence scoring for suggestions
- Explainable recommendations with reasoning
"""

import os
import json
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum

import httpx

from services.ai_brain_service import AIBrainService, get_ai_brain_service
from services.behavior_signal_service import BehaviorSignalService

logger = logging.getLogger(__name__)


class StylistIntent(Enum):
    """Detected user intent types."""
    OUTFIT_REQUEST = "outfit_request"
    STYLE_ADVICE = "style_advice"
    COLOR_HELP = "color_help"
    OCCASION_GUIDANCE = "occasion_guidance"
    TREND_INQUIRY = "trend_inquiry"
    WARDROBE_HELP = "wardrobe_help"
    BUDGET_QUESTION = "budget_question"
    FIT_ADVICE = "fit_advice"
    CLARIFICATION = "clarification"
    FEEDBACK = "feedback"
    GENERAL_CHAT = "general_chat"


class ConversationMemory:
    """Manages conversational context and memory."""
    
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {
            "occasion": None,
            "budget": None,
            "style_preference": None,
            "body_type": None,
            "colors_mentioned": [],
            "brands_mentioned": [],
            "items_discussed": [],
            "rejected_suggestions": [],
            "accepted_suggestions": [],
            "clarification_needed": False,
        }
        self.user_goals: List[str] = []
        self.last_recommendation_ids: List[str] = []
    
    def add_turn(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a conversation turn with metadata."""
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self.turns.append(turn)
        
        # Trim old turns if needed
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
    
    def update_context(self, key: str, value: Any):
        """Update conversation context."""
        self.context[key] = value
    
    def get_relevant_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent relevant conversation history."""
        return [
            {"role": t["role"], "content": t["content"]}
            for t in self.turns[-limit:]
        ]
    
    def get_context_summary(self) -> str:
        """Generate a context summary for AI prompts."""
        parts = []
        
        if self.context.get("occasion"):
            parts.append(f"Occasion: {self.context['occasion']}")
        if self.context.get("budget"):
            parts.append(f"Budget: {self.context['budget']}")
        if self.context.get("style_preference"):
            parts.append(f"Style preference: {self.context['style_preference']}")
        if self.context.get("body_type"):
            parts.append(f"Body type: {self.context['body_type']}")
        if self.context.get("colors_mentioned"):
            parts.append(f"Colors discussed: {', '.join(self.context['colors_mentioned'])}")
        if self.context.get("rejected_suggestions"):
            parts.append(f"Previously rejected: {len(self.context['rejected_suggestions'])} suggestions")
        
        return " | ".join(parts) if parts else "No specific context established"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation state."""
        return {
            "turns": self.turns,
            "context": self.context,
            "user_goals": self.user_goals,
            "last_recommendation_ids": self.last_recommendation_ids,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Deserialize conversation state."""
        memory = cls()
        memory.turns = data.get("turns", [])
        memory.context = data.get("context", {})
        memory.user_goals = data.get("user_goals", [])
        memory.last_recommendation_ids = data.get("last_recommendation_ids", [])
        return memory


class IntentClassifier:
    """Classifies user intent from messages."""
    
    INTENT_KEYWORDS = {
        StylistIntent.OUTFIT_REQUEST: [
            "outfit", "look", "wear", "dress", "ensemble", "put together",
            "what should i wear", "help me choose", "suggest an outfit",
            "build me", "create an outfit", "make me"
        ],
        StylistIntent.STYLE_ADVICE: [
            "style advice", "how do i style", "styling tips", "style this",
            "fashion advice", "style help", "how to wear"
        ],
        StylistIntent.COLOR_HELP: [
            "color", "colour", "match", "combine", "goes with",
            "what color", "which color", "color combination"
        ],
        StylistIntent.OCCASION_GUIDANCE: [
            "occasion", "event", "party", "wedding", "date", "interview",
            "meeting", "work", "formal", "casual", "what to wear to"
        ],
        StylistIntent.TREND_INQUIRY: [
            "trend", "trending", "fashion now", "in style", "popular",
            "current fashion", "what's hot", "latest"
        ],
        StylistIntent.WARDROBE_HELP: [
            "wardrobe", "closet", "my clothes", "what i have", "my items",
            "from my wardrobe", "use what i own"
        ],
        StylistIntent.BUDGET_QUESTION: [
            "budget", "affordable", "cheap", "expensive", "price",
            "cost", "under $", "within my budget", "how much"
        ],
        StylistIntent.FIT_ADVICE: [
            "fit", "size", "body type", "flatter", "look good on me",
            "my shape", "my figure", "petite", "tall", "curvy"
        ],
        StylistIntent.CLARIFICATION: [
            "what do you mean", "can you explain", "i don't understand",
            "clarify", "more details", "tell me more"
        ],
        StylistIntent.FEEDBACK: [
            "i like", "i don't like", "love it", "hate it", "not for me",
            "perfect", "too", "not enough", "prefer"
        ],
    }
    
    @classmethod
    def classify(cls, message: str) -> StylistIntent:
        """Classify the primary intent of a message."""
        lower = message.lower()
        
        scores = {}
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > 0:
                scores[intent] = score
        
        if not scores:
            return StylistIntent.GENERAL_CHAT
        
        return max(scores, key=scores.get)
    
    @classmethod
    def extract_entities(cls, message: str) -> Dict[str, Any]:
        """Extract relevant entities from message."""
        entities = {
            "colors": [],
            "occasions": [],
            "budget": None,
            "styles": [],
            "items": [],
        }
        
        lower = message.lower()
        
        # Extract colors
        color_list = [
            "black", "white", "red", "blue", "green", "yellow", "purple",
            "pink", "orange", "brown", "grey", "gray", "navy", "beige",
            "burgundy", "emerald", "mustard", "teal", "coral", "cream"
        ]
        entities["colors"] = [c for c in color_list if c in lower]
        
        # Extract occasions
        occasion_list = [
            "wedding", "party", "date", "work", "interview", "meeting",
            "casual", "formal", "gym", "beach", "dinner", "brunch"
        ]
        entities["occasions"] = [o for o in occasion_list if o in lower]
        
        # Extract budget
        import re
        budget_match = re.search(r'\$(\d+)|(\d+)\s*dollars|under\s*(\d+)', lower)
        if budget_match:
            entities["budget"] = int(budget_match.group(1) or budget_match.group(2) or budget_match.group(3))
        
        # Extract styles
        style_list = [
            "classic", "modern", "bohemian", "minimalist", "edgy",
            "romantic", "vintage", "streetwear", "sporty", "elegant"
        ]
        entities["styles"] = [s for s in style_list if s in lower]
        
        return entities


class ConfidenceScorer:
    """Calculates confidence scores for recommendations."""
    
    @staticmethod
    def calculate_outfit_confidence(
        outfit_data: Dict[str, Any],
        user_style_vector: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate multi-dimensional confidence scores."""
        scores = {
            "style_match": 0.0,
            "occasion_fit": 0.0,
            "color_harmony": 0.0,
            "budget_alignment": 0.0,
            "trend_factor": 0.0,
            "overall": 0.0,
        }
        
        # Style match score
        if user_style_vector.get("archetype"):
            scores["style_match"] = user_style_vector.get("archetype_confidence", 0.5) * 100
        
        # Occasion fit
        if context.get("occasion"):
            scores["occasion_fit"] = 85.0  # Would calculate based on dress code
        
        # Color harmony
        scores["color_harmony"] = 90.0  # Would validate colors
        
        # Budget alignment
        if context.get("budget") and outfit_data.get("total_price"):
            ratio = outfit_data["total_price"] / context["budget"]
            if ratio <= 1.0:
                scores["budget_alignment"] = 95.0
            elif ratio <= 1.2:
                scores["budget_alignment"] = 70.0
            else:
                scores["budget_alignment"] = 40.0
        else:
            scores["budget_alignment"] = 80.0
        
        # Trend factor
        scores["trend_factor"] = 75.0  # Would check against trends
        
        # Overall weighted score
        weights = {
            "style_match": 0.25,
            "occasion_fit": 0.20,
            "color_harmony": 0.20,
            "budget_alignment": 0.15,
            "trend_factor": 0.20,
        }
        
        scores["overall"] = sum(
            scores[k] * weights[k]
            for k in weights
        )
        
        return scores


class RecommendationExplainer:
    """Generates human-readable explanations for recommendations."""
    
    @staticmethod
    def explain_outfit(
        outfit: Dict[str, Any],
        scores: Dict[str, float],
        style_vector: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """Generate explanation for outfit recommendation."""
        reasons = []
        
        # Style alignment
        if scores.get("style_match", 0) > 70:
            archetype = style_vector.get("archetype", "your")
            reasons.append(f"This outfit perfectly matches your {archetype} style")
        
        # Occasion fit
        occasion = context.get("occasion")
        if occasion and scores.get("occasion_fit", 0) > 70:
            reasons.append(f"Ideal for a {occasion} setting")
        
        # Color harmony
        if scores.get("color_harmony", 0) > 80:
            reasons.append("The colors create a harmonious, cohesive look")
        
        # Budget
        if scores.get("budget_alignment", 0) > 85:
            reasons.append("Stays comfortably within your budget")
        
        # Trend
        if scores.get("trend_factor", 0) > 70:
            reasons.append("Incorporates current fashion trends")
        
        # Combine into natural language
        if not reasons:
            return "A versatile piece that works well with your wardrobe."
        
        explanation = "✨ " + ". ".join(reasons[:3]) + "."
        return explanation
    
    @staticmethod
    def explain_color_advice(color1: str, color2: str, harmony_type: str) -> str:
        """Explain color combination advice."""
        explanations = {
            "complementary": f"{color1.title()} and {color2.title()} are complementary colors on the color wheel, creating a bold, high-contrast look that really pops.",
            "analogous": f"{color1.title()} and {color2.title()} sit next to each other on the color wheel, creating a naturally harmonious and cohesive palette.",
            "triadic": f"{color1.title()} and {color2.title()} are part of a triadic color scheme, offering balanced visual interest while maintaining harmony.",
            "monochromatic": f"Using different shades of {color1} creates a sophisticated, elegant monochromatic look.",
            "neutral_safe": f"{color1.title()} and {color2.title()} are timeless neutrals that pair effortlessly for a classic, versatile combination.",
        }
        
        return explanations.get(harmony_type, f"{color1.title()} and {color2.title()} work well together.")
    
    @staticmethod
    def explain_style_match(user_style: str, item_style: str, match_score: float) -> str:
        """Explain style matching."""
        if match_score > 85:
            return f"This piece is a perfect match for your {user_style} aesthetic."
        elif match_score > 70:
            return f"This complements your {user_style} style beautifully."
        elif match_score > 50:
            return f"This adds variety to your {user_style} wardrobe while staying true to your taste."
        else:
            return f"This offers a chance to explore beyond your usual {user_style} style."


class EnhancedVirtualStylistService:
    """
    Enhanced virtual stylist with advanced AI capabilities.
    
    Features:
    - Conversational memory for context-aware responses
    - Intent classification and refinement
    - Confidence scoring for all recommendations
    - Explainable recommendations with reasoning
    - Integration with AI Central Brain for personalization
    """
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        ai_brain: AIBrainService = None,
    ):
        self._groq_api_key = groq_api_key
        self._has_ai = bool(groq_api_key)
        self._ai_brain = ai_brain
        self._conversations: Dict[str, ConversationMemory] = {}
        
        if self._has_ai:
            logger.info("EnhancedVirtualStylistService initialized with Groq AI")
        else:
            logger.info("EnhancedVirtualStylistService initialized with rule-based fallback")
    
    def get_or_create_conversation(self, user_id: str) -> ConversationMemory:
        """Get or create conversation memory for user."""
        if user_id not in self._conversations:
            self._conversations[user_id] = ConversationMemory()
        return self._conversations[user_id]
    
    async def chat(
        self,
        user_message: str,
        user_id: str = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        occasion: Optional[str] = None,
        budget: Optional[str] = None,
        style_preference: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message with enhanced context awareness.
        
        Returns:
            dict with 'content', 'outfitSuggestions', 'detectedOccasion',
            'confidence', 'explanation', and 'intent'
        """
        # Get or create conversation memory
        memory = self.get_or_create_conversation(user_id) if user_id else ConversationMemory()
        
        # Add user message to memory
        memory.add_turn("user", user_message)
        
        # Classify intent
        intent = IntentClassifier.classify(user_message)
        
        # Extract entities
        entities = IntentClassifier.extract_entities(user_message)
        
        # Update conversation context
        if entities["occasions"]:
            memory.update_context("occasion", entities["occasions"][0])
        if entities["budget"]:
            memory.update_context("budget", entities["budget"])
        if entities["styles"]:
            memory.update_context("style_preference", entities["styles"][0])
        if entities["colors"]:
            memory.context["colors_mentioned"].extend(entities["colors"])
        
        # Merge with provided context
        context_occasion = occasion or memory.context.get("occasion")
        context_budget = budget or str(memory.context.get("budget")) if memory.context.get("budget") else None
        context_style = style_preference or memory.context.get("style_preference")
        
        # Handle different intents
        if intent == StylistIntent.CLARIFICATION:
            response = await self._handle_clarification(user_message, memory, user_id)
        elif intent == StylistIntent.FEEDBACK:
            response = await self._handle_feedback(user_message, memory, user_id)
        else:
            # Use AI or fallback
            if self._has_ai:
                response = await self._ai_chat(
                    user_message, memory, user_id,
                    context_occasion, context_budget, context_style, gender
                )
            else:
                response = self._rule_based_chat(
                    user_message, memory, user_id,
                    context_occasion, context_budget, context_style, gender
                )
        
        # Add response to memory
        memory.add_turn(
            "assistant",
            response["content"],
            metadata={
                "intent": intent.value,
                "outfit_ids": [o.get("id") for o in response.get("outfitSuggestions", [])],
            }
        )
        
        # Store last recommendations for feedback tracking
        if response.get("outfitSuggestions"):
            memory.last_recommendation_ids = [o.get("id") for o in response["outfitSuggestions"]]
        
        # Add intent to response
        response["intent"] = intent.value
        
        return response
    
    async def _ai_chat(
        self,
        user_message: str,
        memory: ConversationMemory,
        user_id: str,
        occasion: Optional[str],
        budget: Optional[str],
        style_preference: Optional[str],
        gender: Optional[str],
    ) -> Dict[str, Any]:
        """Generate AI-powered response with context."""
        
        # Build context-aware system prompt
        context_summary = memory.get_context_summary()
        
        system_prompt = f"""You are CONFIT's expert virtual fashion stylist — a knowledgeable, warm, and professional fashion consultant.

CONVERSATION CONTEXT:
{context_summary}

USER PROFILE CONTEXT:
- Gender: {gender or 'not specified'}
- Occasion focus: {occasion or 'not specified'}
- Budget consideration: {budget or 'flexible'}
- Style preference: {style_preference or 'discovering'}

GUIDELINES:
- Provide specific, actionable style advice grounded in fashion expertise
- Reference previous conversation context when relevant
- Ask clarifying questions when the user's intent is unclear
- Offer outfit suggestions with brief explanations of why they work
- Keep responses conversational but informative (2-4 sentences typically)
- Use an encouraging, confident tone — help users feel great about their choices
- When suggesting outfits, explain the styling rationale
- Always stay in your role as a fashion stylist — politely redirect off-topic queries

INTENT HANDLING:
- If the user wants outfit suggestions, provide 2-3 specific options
- If asking for color advice, explain color theory principles
- If asking about trends, mention what's currently popular
- If asking about fit, provide body-positive styling advice"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        history = memory.get_relevant_history(10)
        messages.extend(history)
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Call Groq API with retry
        max_retries = 3
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._groq_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 500,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    ai_content = data["choices"][0]["message"]["content"]
                    
                    # Build response
                    result = {
                        "content": ai_content,
                        "detectedOccasion": occasion,
                        "outfitSuggestions": None,
                        "confidence": 0.85,
                        "explanation": None,
                    }
                    
                    # Add outfit suggestions if appropriate
                    if any(w in user_message.lower() for w in ["show", "recommend", "suggest", "outfit", "look", "wear"]):
                        result["outfitSuggestions"] = self._get_outfit_suggestions(occasion or "default")
                        result["explanation"] = "Personalized recommendations based on your style profile and occasion."
                    
                    return result
                    
            except Exception as exc:
                last_error = exc
                logger.warning(f"Groq API attempt {attempt}/{max_retries} failed: {exc}")
                if attempt < max_retries:
                    await asyncio.sleep(1.5 ** attempt)
        
        # Fallback to rule-based
        return self._rule_based_chat(
            user_message, memory, user_id, occasion, budget, style_preference, gender
        )
    
    def _rule_based_chat(
        self,
        user_message: str,
        memory: ConversationMemory,
        user_id: str,
        occasion: Optional[str],
        budget: Optional[str],
        style_preference: Optional[str],
        gender: Optional[str],
    ) -> Dict[str, Any]:
        """Enhanced rule-based fallback with context awareness."""
        lower_input = user_message.lower()
        response_parts = []
        detected_occasion = None
        outfit_suggestions = None
        confidence = 0.75
        
        # Intent-based responses
        intent = IntentClassifier.classify(user_message)
        
        # Greeting
        if intent == StylistIntent.GENERAL_CHAT and any(g in lower_input for g in ["hello", "hi", "hey"]):
            context_ref = ""
            if memory.context.get("occasion"):
                context_ref = f" I remember you were looking for something for a {memory.context['occasion']}."
            response_parts.append(
                f"Hello! Welcome to CONFIT! 👋 I'm your personal fashion stylist.{context_ref} "
                "How can I help you look and feel your best today?"
            )
        
        # Outfit request
        elif intent == StylistIntent.OUTFIT_REQUEST:
            detected_occasion = self._detect_occasion(user_message) or occasion or "default"
            response_parts.append(self._get_occasion_response(detected_occasion))
            outfit_suggestions = self._get_outfit_suggestions(detected_occasion)
            confidence = 0.88
        
        # Color help
        elif intent == StylistIntent.COLOR_HELP:
            entities = IntentClassifier.extract_entities(user_message)
            colors = entities.get("colors", [])
            if len(colors) >= 2:
                harmony = self._get_color_harmony(colors[0], colors[1])
                response_parts.append(
                    RecommendationExplainer.explain_color_advice(
                        colors[0], colors[1], harmony
                    )
                )
                confidence = 0.92
            elif len(colors) == 1:
                response_parts.append(
                    f"{colors[0].title()} is a versatile color! "
                    f"{self._get_color_pairing_advice(colors[0])}"
                )
                confidence = 0.85
            else:
                response_parts.append(
                    "Color is one of my favorite topics! Tell me which colors you're "
                    "considering, and I'll help you create the perfect palette."
                )
        
        # Occasion guidance
        elif intent == StylistIntent.OCCASION_GUIDANCE:
            entities = IntentClassifier.extract_entities(user_message)
            occasions = entities.get("occasions", [])
            if occasions:
                detected_occasion = occasions[0]
                response_parts.append(self._get_occasion_response(detected_occasion))
                outfit_suggestions = self._get_outfit_suggestions(detected_occasion)
                confidence = 0.90
            else:
                response_parts.append(
                    "I'd love to help you dress for the right occasion! "
                    "Are you preparing for work, a date, a party, or something else?"
                )
        
        # Trend inquiry
        elif intent == StylistIntent.TREND_INQUIRY:
            response_parts.append(
                "Current fashion trends include oversized blazers, wide-leg pants, "
                "chunky loafers, and rich earth tones like sage green and terracotta. "
                "Statement accessories and layered jewelry are also very popular! "
                "Would you like specific trend recommendations for your style?"
            )
            confidence = 0.82
        
        # Budget question
        elif intent == StylistIntent.BUDGET_QUESTION:
            entities = IntentClassifier.extract_entities(user_message)
            budget_value = entities.get("budget") or budget
            if budget_value:
                response_parts.append(
                    f"I'll help you find amazing pieces within your ${budget_value} budget! "
                    "Smart shopping is about investing in versatile basics and adding "
                    "trendier, affordable accessories. Let me show you some options."
                )
                outfit_suggestions = self._get_budget_friendly_suggestions(budget_value)
                confidence = 0.87
            else:
                response_parts.append(
                    "Budget-friendly fashion is one of my specialties! "
                    "What's your price range? I'll find you the best value pieces."
                )
        
        # Fit advice
        elif intent == StylistIntent.FIT_ADVICE:
            response_parts.append(
                "Every body type can rock any style! The key is finding the right "
                "proportions and silhouettes. Tell me more about what you're "
                "looking for, and I'll suggest pieces that flatter your figure beautifully. "
                "What specific fit concerns do you have?"
            )
            confidence = 0.80
        
        # Style advice
        elif intent == StylistIntent.STYLE_ADVICE:
            entities = IntentClassifier.extract_entities(user_message)
            styles = entities.get("styles", [])
            if styles:
                response_parts.append(
                    f"{styles[0].title()} style is all about "
                    f"{self._get_style_description(styles[0])} "
                    "Let me suggest some pieces that capture that aesthetic perfectly."
                )
                outfit_suggestions = self._get_outfit_suggestions("default")
                confidence = 0.85
            else:
                response_parts.append(
                    "I'd love to give you styling advice! What specific piece or "
                    "look are you trying to style? And what's the occasion?"
                )
        
        # Default fallback
        if not response_parts:
            response_parts.append(
                "I'm here to help with your fashion journey! I can assist with "
                "outfit recommendations, color coordination, trend information, "
                "and personalized styling advice. What would you like to explore?"
            )
        
        # Build response
        content = " ".join(response_parts)
        
        # Generate explanation if we have suggestions
        explanation = None
        if outfit_suggestions:
            explanation = f"Recommendations tailored for {detected_occasion or 'your style'} with {confidence:.0%} confidence."
        
        return {
            "content": content,
            "detectedOccasion": detected_occasion or occasion,
            "outfitSuggestions": outfit_suggestions,
            "confidence": confidence,
            "explanation": explanation,
        }
    
    async def _handle_clarification(
        self,
        user_message: str,
        memory: ConversationMemory,
        user_id: str,
    ) -> Dict[str, Any]:
        """Handle clarification requests."""
        last_bot_message = None
        for turn in reversed(memory.turns):
            if turn["role"] == "assistant":
                last_bot_message = turn["content"]
                break
        
        return {
            "content": (
                "Let me clarify! I'm here to help you find the perfect outfit. "
                "Could you tell me more about what you're looking for? "
                "For example: What occasion? Any color preferences? Budget range?"
            ),
            "confidence": 0.70,
            "explanation": None,
        }
    
    async def _handle_feedback(
        self,
        user_message: str,
        memory: ConversationMemory,
        user_id: str,
    ) -> Dict[str, Any]:
        """Handle user feedback on recommendations."""
        lower = user_message.lower()
        
        # Determine if positive or negative
        positive_keywords = ["like", "love", "perfect", "great", "beautiful", "yes", "want"]
        negative_keywords = ["don't like", "not for me", "too", "hate", "no", "different"]
        
        is_positive = any(kw in lower for kw in positive_keywords)
        is_negative = any(kw in lower for kw in negative_keywords)
        
        # Track feedback if we have user_id and recommendations
        if user_id and memory.last_recommendation_ids:
            for outfit_id in memory.last_recommendation_ids:
                if is_positive:
                    memory.context["accepted_suggestions"].append(outfit_id)
                elif is_negative:
                    memory.context["rejected_suggestions"].append(outfit_id)
        
        if is_positive:
            return {
                "content": (
                    "I'm so glad you like it! ✨ Would you like to try it on virtually, "
                    "or shall I suggest similar styles? I can also help you complete the look "
                    "with accessories or shoes."
                ),
                "confidence": 0.90,
                "explanation": None,
            }
        elif is_negative:
            # Try to understand why
            reason = None
            if "too expensive" in lower or "pricey" in lower:
                reason = "budget"
            elif "too formal" in lower or "too casual" in lower:
                reason = "formality"
            elif "color" in lower:
                reason = "color"
            elif "fit" in lower or "style" in lower:
                reason = "style"
            
            response = "I understand! Let me adjust my suggestions. "
            if reason == "budget":
                response += "Here are some more budget-friendly options that still look amazing."
            elif reason == "formality":
                response += "I'll find something with a different level of formality."
            elif reason == "color":
                response += "Let me show you different color options."
            elif reason == "style":
                response += "I'll explore a different style direction for you."
            else:
                response += "What specifically isn't working for you? The color, style, or price point?"
            
            return {
                "content": response,
                "outfitSuggestions": self._get_outfit_suggestions(memory.context.get("occasion", "default")),
                "confidence": 0.75,
                "explanation": "Adjusted recommendations based on your feedback.",
            }
        
        return {
            "content": "Thanks for the feedback! What specifically would you like to change?",
            "confidence": 0.70,
            "explanation": None,
        }
    
    # ── Helper Methods ────────────────────────────────────────────────
    
    def _detect_occasion(self, message: str) -> Optional[str]:
        """Detect occasion from message."""
        occasion_keywords = {
            "wedding": "formal", "gala": "formal", "ceremony": "formal",
            "party": "party", "club": "party", "night out": "party",
            "work": "work", "office": "work", "meeting": "work", "interview": "work",
            "date": "date", "dinner": "date", "romantic": "date",
            "casual": "casual", "weekend": "casual", "everyday": "casual",
            "gym": "active", "workout": "active", "run": "active",
        }
        
        lower = message.lower()
        for keyword, occasion in occasion_keywords.items():
            if keyword in lower:
                return occasion
        
        return None
    
    def _get_occasion_response(self, occasion: str) -> str:
        """Get response for occasion type."""
        responses = {
            "formal": "A formal occasion calls for elegance and sophistication! I've curated stunning options that will make you stand out while keeping it classy.",
            "party": "Time to shine! 🎉 I've selected trendy, eye-catching pieces perfect for making an impression.",
            "work": "Let's keep it professional yet stylish! Here are polished looks that command respect while expressing your personality.",
            "date": "Ooh, exciting! 💫 I've picked outfits that are attractive yet comfortable — confidence is your best accessory.",
            "casual": "Effortless style is an art! Here are relaxed yet put-together looks for your day-to-day adventures.",
            "active": "Performance meets style! 💪 These activewear picks will keep you comfortable and looking great.",
        }
        
        return responses.get(occasion, "I've put together some looks tailored to your needs!")
    
    def _get_outfit_suggestions(self, occasion: str) -> List[Dict[str, Any]]:
        """Get outfit suggestions for occasion."""
        suggestions = {
            "formal": [
                {"id": "f1", "name": "Executive Elegance", "price": 485, "styleScore": 95,
                 "image": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop"},
                {"id": "f2", "name": "Power Meeting", "price": 520, "styleScore": 92,
                 "image": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=300&h=400&fit=crop"},
                {"id": "f3", "name": "Corporate Chic", "price": 395, "styleScore": 90,
                 "image": "https://images.unsplash.com/photo-1617019114583-affb34d1b3cd?w=300&h=400&fit=crop"},
            ],
            "party": [
                {"id": "p1", "name": "Night Out Glam", "price": 350, "styleScore": 93,
                 "image": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=300&h=400&fit=crop"},
                {"id": "p2", "name": "Club Ready", "price": 290, "styleScore": 89,
                 "image": "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=300&h=400&fit=crop"},
            ],
            "work": [
                {"id": "w1", "name": "Office Ready", "price": 380, "styleScore": 93,
                 "image": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop"},
                {"id": "w2", "name": "Business Casual", "price": 295, "styleScore": 91,
                 "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&h=400&fit=crop"},
            ],
            "date": [
                {"id": "d1", "name": "Romantic Evening", "price": 310, "styleScore": 94,
                 "image": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=300&h=400&fit=crop"},
                {"id": "d2", "name": "First Impression", "price": 275, "styleScore": 90,
                 "image": "https://images.unsplash.com/photo-1581044777550-4cfa60707998?w=300&h=400&fit=crop"},
            ],
            "casual": [
                {"id": "c1", "name": "Weekend Vibes", "price": 185, "styleScore": 91,
                 "image": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?w=300&h=400&fit=crop"},
                {"id": "c2", "name": "Street Smart", "price": 210, "styleScore": 88,
                 "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&h=400&fit=crop"},
            ],
            "active": [
                {"id": "a1", "name": "Gym Flow", "price": 145, "styleScore": 88,
                 "image": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=400&fit=crop"},
                {"id": "a2", "name": "Run Ready", "price": 175, "styleScore": 86,
                 "image": "https://images.unsplash.com/photo-1518459031867-a89b944bffe4?w=300&h=400&fit=crop"},
            ],
            "default": [
                {"id": "x1", "name": "Classic Essential", "price": 250, "styleScore": 90,
                 "image": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop"},
                {"id": "x2", "name": "Modern Minimal", "price": 320, "styleScore": 88,
                 "image": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=300&h=400&fit=crop"},
            ],
        }
        
        return suggestions.get(occasion, suggestions["default"])
    
    def _get_budget_friendly_suggestions(self, budget: int) -> List[Dict[str, Any]]:
        """Get suggestions within budget."""
        all_suggestions = self._get_outfit_suggestions("default")
        return [s for s in all_suggestions if s["price"] <= budget] or all_suggestions
    
    def _get_color_harmony(self, color1: str, color2: str) -> str:
        """Determine color harmony type."""
        for harmony_type, rules in [
            ("complementary", [("blue", "orange"), ("red", "green"), ("yellow", "purple")]),
            ("analogous", [("blue", "green"), ("red", "orange"), ("yellow", "orange")]),
        ]:
            for pair in rules:
                if (color1 in pair and color2 in pair):
                    return harmony_type
        return "neutral_safe"
    
    def _get_color_pairing_advice(self, color: str) -> str:
        """Get pairing advice for a single color."""
        advice = {
            "black": "It pairs beautifully with everything — try it with white for classic contrast, gold for elegance, or bright colors for a pop.",
            "white": "It goes with virtually anything — pair with pastels for softness, navy for nautical vibes, or bold colors for impact.",
            "blue": "It pairs wonderfully with white, beige, grey, or camel. Navy blue with gold is particularly sophisticated.",
            "red": "This bold color looks stunning with black, white, or denim. For a softer look, try it with pink or nude tones.",
            "green": "It works beautifully with earth tones, cream, and white. Olive green with burgundy is a timeless combination.",
            "navy": "A versatile neutral that pairs with white, cream, camel, and even soft pink for a refined palette.",
        }
        
        return advice.get(color, f"{color.title()} is a versatile choice that can be styled many ways!")
    
    def _get_style_description(self, style: str) -> str:
        """Get description for style type."""
        descriptions = {
            "classic": "timeless pieces that never go out of fashion. Think clean lines, neutral colors, and quality fabrics.",
            "modern": "current trends with a sophisticated edge. Contemporary silhouettes with fresh, updated details.",
            "minimalist": "clean silhouettes, a cohesive neutral palette, and quality over quantity. Less is more.",
            "bohemian": "free-spirited, relaxed elegance with flowing fabrics, earthy tones, and unique accessories.",
            "edgy": "bold choices, unexpected combinations, and statement pieces that show personality.",
            "romantic": "soft, feminine details with delicate fabrics, pretty prints, and dreamy silhouettes.",
            "vintage": "retro-inspired pieces with nostalgic charm and timeless appeal.",
            "streetwear": "bold graphics, oversized fits, and sneaker culture with urban attitude.",
        }
        
        return descriptions.get(style, "a unique and personal aesthetic.")
    
    def clear_conversation(self, user_id: str) -> None:
        """Clear conversation memory for user."""
        if user_id in self._conversations:
            del self._conversations[user_id]
    
    def get_conversation_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get serializable conversation state."""
        if user_id in self._conversations:
            return self._conversations[user_id].to_dict()
        return None
    
    def restore_conversation(self, user_id: str, state: Dict[str, Any]) -> None:
        """Restore conversation from serialized state."""
        self._conversations[user_id] = ConversationMemory.from_dict(state)
