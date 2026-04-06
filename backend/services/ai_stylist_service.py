"""
CONFIT Backend — AI Stylist Service
====================================
Enhanced AI-powered fashion styling with:
- LLM integration (Groq/OpenAI compatible)
- Prompt engineering for fashion expertise
- User context injection (profile, wardrobe, preferences)
- Product catalog search integration
- Vector similarity search for fashion knowledge
- Recommendation caching with Redis
"""

import os
import json
import asyncio
import logging
import re
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

# JSON-first stylist brain utilities
from services.ai.stylist_json import (
    extract_features as extract_json_features,
    build_stylist_json_prompt,
    safe_extract_stylist_json,
)

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # "groq" or "openai"
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 30
MAX_TOKENS_PER_REQUEST = 2000

# ── Data Classes ──────────────────────────────────────────────────────────

@dataclass
class StylistContext:
    """Context for generating stylist responses."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    # User profile context
    style_profile: Optional[Dict[str, Any]] = None
    body_profile: Optional[Dict[str, Any]] = None
    budget_profile: Optional[Dict[str, Any]] = None
    brand_affinities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Wardrobe context
    wardrobe_items: List[Dict[str, Any]] = field(default_factory=list)
    recent_outfits: List[Dict[str, Any]] = field(default_factory=list)
    
    # Detected intent
    detected_occasion: Optional[str] = None
    detected_budget: Optional[str] = None
    detected_style: Optional[str] = None
    detected_colors: List[str] = field(default_factory=list)
    
    # Product search results
    relevant_products: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StylistResponse:
    """Generated response from the AI stylist."""
    content: str
    detected_occasion: Optional[str] = None
    detected_budget: Optional[str] = None
    detected_style: Optional[str] = None
    detected_colors: List[str] = field(default_factory=list)
    
    # Recommendations
    outfit_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    product_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    wardrobe_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    style_tips: List[str] = field(default_factory=list)
    
    # Metadata
    tokens_used: int = 0
    response_time_ms: int = 0
    model_version: str = ""
    cached: bool = False


# ── Prompt Engineering Layer ─────────────────────────────────────────────

class PromptEngineer:
    """Constructs fashion-specific prompts for the LLM."""
    
    SYSTEM_PROMPT = """You are CONFIT's expert AI fashion stylist — a knowledgeable, warm, and professional fashion consultant with deep expertise in:

• Style archetypes (Classic, Modern, Bohemian, Minimalist, Edgy, Romantic, Streetwear)
• Color theory and personal color analysis (seasonal palettes, undertones)
• Body proportions and flattering silhouettes
• Occasion-appropriate dressing
• Sustainable and ethical fashion
• Current trends and timeless classics

You help users discover their personal style, build outfits from their wardrobe, and find new pieces that complement their existing collection.

Guidelines:
1. Be specific and actionable — give concrete styling advice, not vague suggestions
2. Consider the user's body type, skin tone, style preferences, and budget
3. Recommend color combinations and explain the styling rationale
4. Keep responses concise (2-4 sentences) unless asked for detailed guidance
5. Use an encouraging, confident tone — help users feel great about their choices
6. When suggesting outfits, mention fabric types and layering tips when relevant
7. If the user has wardrobe items, prioritize suggesting outfits using their existing pieces
8. Always stay in character as a fashion stylist — politely redirect off-topic queries
9. If unsure about user preferences, ask one clarifying question rather than guessing
10. Never fabricate product URLs — only reference items from the provided context

JSON output rule:
- If the user message asks for a specific JSON schema, output JSON only (no markdown, no extra text)."""

    @classmethod
    def build_system_prompt(cls, context: StylistContext) -> str:
        """Build system prompt with injected context."""
        prompt_parts = [cls.SYSTEM_PROMPT]
        
        # Add user profile context
        if context.style_profile:
            profile_context = cls._build_profile_context(context)
            if profile_context:
                prompt_parts.append("\n\n## User Style Profile\n" + profile_context)
        
        # Add wardrobe context
        if context.wardrobe_items:
            wardrobe_context = cls._build_wardrobe_context(context)
            if wardrobe_context:
                prompt_parts.append("\n\n## User's Wardrobe\n" + wardrobe_context)
        
        # Add detected intent context
        if context.detected_occasion or context.detected_budget or context.detected_style:
            intent_context = cls._build_intent_context(context)
            prompt_parts.append("\n\n## Current Request Context\n" + intent_context)
        
        return "".join(prompt_parts)
    
    @classmethod
    def _build_profile_context(cls, context: StylistContext) -> str:
        """Build user profile context string."""
        parts = []
        
        profile = context.style_profile or {}
        
        if profile.get("primary_archetype"):
            parts.append(f"- Style archetype: {profile['primary_archetype']}")
        
        if profile.get("fit_preference"):
            parts.append(f"- Fit preference: {profile['fit_preference']}")
        
        if profile.get("skin_undertone"):
            parts.append(f"- Skin undertone: {profile['skin_undertone']}")
        
        if profile.get("preferred_colors"):
            colors = ", ".join(profile["preferred_colors"][:5])
            parts.append(f"- Preferred colors: {colors}")
        
        if profile.get("avoided_colors"):
            colors = ", ".join(profile["avoided_colors"][:3])
            parts.append(f"- Colors to avoid: {colors}")
        
        body = context.body_profile or {}
        if body.get("body_shape"):
            parts.append(f"- Body shape: {body['body_shape']}")
        if body.get("height_cm"):
            parts.append(f"- Height: {body['height_cm']}cm")
        
        budget = context.budget_profile or {}
        if budget.get("per_item_max"):
            parts.append(f"- Budget per item: up to ${budget['per_item_max']}")
        
        if context.brand_affinities:
            brands = [b.get("brand_id", "") for b in context.brand_affinities[:3]]
            parts.append(f"- Preferred brands: {', '.join(brands)}")
        
        return "\n".join(parts) if parts else ""
    
    @classmethod
    def _build_wardrobe_context(cls, context: StylistContext) -> str:
        """Build wardrobe context string."""
        if not context.wardrobe_items:
            return ""
        
        parts = ["Here are items from the user's wardrobe that you can reference:"]
        
        # Group by category
        categories = {}
        for item in context.wardrobe_items[:20]:  # Limit to prevent context overflow
            cat = item.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for cat, items in categories.items():
            item_descs = []
            for item in items[:5]:  # Max 5 per category
                desc = f"{item.get('name', 'Unknown')}"
                if item.get("color"):
                    desc += f" ({item['color']})"
                if item.get("brand"):
                    desc += f" by {item['brand']}"
                item_descs.append(desc)
            parts.append(f"- {cat.title()}: {', '.join(item_descs)}")
        
        return "\n".join(parts)
    
    @classmethod
    def _build_intent_context(cls, context: StylistContext) -> str:
        """Build detected intent context."""
        parts = []
        
        if context.detected_occasion:
            parts.append(f"- Occasion: {context.detected_occasion}")
        
        if context.detected_budget:
            parts.append(f"- Budget: {context.detected_budget}")
        
        if context.detected_style:
            parts.append(f"- Style preference: {context.detected_style}")
        
        if context.detected_colors:
            parts.append(f"- Colors mentioned: {', '.join(context.detected_colors)}")
        
        return "\n".join(parts)
    
    @classmethod
    def build_messages(cls, context: StylistContext, user_message: str) -> List[Dict[str, str]]:
        """Build complete message list for LLM API call."""
        messages = [{"role": "system", "content": cls.build_system_prompt(context)}]
        
        # Add conversation history (last 10 messages)
        for msg in context.conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages


# ── Intent Detection ─────────────────────────────────────────────────────

class IntentDetector:
    """Detects user intent from messages."""
    
    OCCASION_KEYWORDS = {
        "wedding": ["wedding", "bride", "groom", "marriage", "nuptial"],
        "work": ["work", "office", "business", "meeting", "interview", "professional", "corporate"],
        "casual": ["casual", "everyday", "weekend", "relaxed", "lounge"],
        "date": ["date", "romantic", "dinner date", "first date", "anniversary"],
        "party": ["party", "club", "night out", "birthday", "celebration", "clubbing"],
        "interview": ["interview", "job interview", "audition"],
        "travel": ["travel", "vacation", "trip", "flight", "airport"],
        "gym": ["gym", "workout", "exercise", "running", "yoga", "athletic", "sport"],
        "beach": ["beach", "pool", "swim", "vacation", "resort"],
        "formal": ["formal", "gala", "black tie", "red carpet", "ceremony", "award"],
        "brunch": ["brunch", "lunch", "cafe", "coffee"],
        "outdoor": ["hiking", "camping", "outdoor", "nature", "trail"],
    }
    
    BUDGET_PATTERNS = {
        "budget": [r"under \$?\d{2,3}", r"cheap", r"affordable", r"budget", r"inexpensive"],
        "moderate": [r"\$?\d{3}-\$?\d{3}", r"mid.?range", r"moderate"],
        "premium": [r"\$?\d{3,4}", r"premium", r"quality", r"investment"],
        "luxury": [r"luxury", r"designer", r"high.?end", r"expensive", r"\$?\d{3,4}\+"],
    }
    
    STYLE_KEYWORDS = {
        "classic": ["classic", "timeless", "traditional", "elegant"],
        "modern": ["modern", "contemporary", "current", "trendy"],
        "bohemian": ["bohemian", "boho", "hippie", "free-spirited", "flowy"],
        "minimalist": ["minimalist", "minimal", "clean", "simple", "capsule"],
        "edgy": ["edgy", "rock", "punk", "alternative", "bold"],
        "romantic": ["romantic", "feminine", "soft", "delicate", "floral"],
        "streetwear": ["streetwear", "street", "urban", "sneaker", "hypebeast"],
        "preppy": ["preppy", "ivy league", "collegiate", "polished"],
    }
    
    COLOR_KEYWORDS = [
        "black", "white", "red", "blue", "green", "yellow", "orange", "purple",
        "pink", "brown", "grey", "gray", "beige", "navy", "burgundy", "maroon",
        "teal", "turquoise", "coral", "mustard", "olive", "cream", "ivory",
        "gold", "silver", "bronze", "copper", "blush", "lavender", "mint"
    ]
    
    @classmethod
    def detect_occasion(cls, message: str) -> Optional[str]:
        """Detect occasion from message."""
        lower = message.lower()
        for occasion, keywords in cls.OCCASION_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return occasion
        return None
    
    @classmethod
    def detect_budget(cls, message: str) -> Optional[str]:
        """Detect budget level from message."""
        lower = message.lower()
        for budget, patterns in cls.BUDGET_PATTERNS.items():
            if any(re.search(p, lower) for p in patterns):
                return budget
        return None
    
    @classmethod
    def detect_style(cls, message: str) -> Optional[str]:
        """Detect style preference from message."""
        lower = message.lower()
        for style, keywords in cls.STYLE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return style
        return None
    
    @classmethod
    def detect_colors(cls, message: str) -> List[str]:
        """Detect mentioned colors from message."""
        lower = message.lower()
        found = []
        for color in cls.COLOR_KEYWORDS:
            if color in lower:
                found.append(color)
        return found
    
    @classmethod
    def detect_all(cls, message: str) -> Dict[str, Any]:
        """Detect all intents from message."""
        return {
            "occasion": cls.detect_occasion(message),
            "budget": cls.detect_budget(message),
            "style": cls.detect_style(message),
            "colors": cls.detect_colors(message),
        }


# ── LLM Provider ──────────────────────────────────────────────────────────

class LLMProvider:
    """Handles LLM API calls with retry logic."""
    
    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        self.provider = provider or LLM_PROVIDER
        self.api_key = api_key or (GROQ_API_KEY if self.provider == "groq" else OPENAI_API_KEY)
        self.model = model or LLM_MODEL
        self._has_api = bool(self.api_key)
        
        if self._has_api:
            logger.info(f"LLMProvider initialized with {self.provider} ({self.model})")
        else:
            logger.warning("No LLM API key configured - using rule-based fallback")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> Tuple[str, int]:
        """Generate response from LLM. Returns (content, tokens_used)."""
        if not self._has_api:
            raise ValueError("No API key configured")
        
        if self.provider == "groq":
            return await self._call_groq(messages, temperature, max_tokens)
        elif self.provider == "openai":
            return await self._call_openai(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    async def _call_groq(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, int]:
        """Call Groq API with exponential backoff."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        max_retries = 3
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    return content, tokens
                    
            except Exception as exc:
                last_error = exc
                logger.warning(f"Groq API attempt {attempt}/{max_retries} failed: {exc}")
                if attempt < max_retries:
                    await asyncio.sleep(1.5 ** attempt)
        
        raise last_error
    
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, int]:
        """Call OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return content, tokens


# ── Response Cache ────────────────────────────────────────────────────────

class ResponseCache:
    """Caches responses for common queries using Redis or in-memory fallback."""
    
    def __init__(self, redis_url: str = None):
        self._redis = None
        self._memory_cache: Dict[str, Any] = {}
        self._redis_url = redis_url or REDIS_URL
        self._ttl = 3600  # 1 hour
    
    async def _get_redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self._redis_url)
            except Exception as e:
                logger.warning(f"Redis not available, using memory cache: {e}")
                self._redis = False
        return self._redis if self._redis else None
    
    def _cache_key(self, context: StylistContext, message: str) -> str:
        """Generate cache key from context and message."""
        key_data = f"{context.user_id}:{context.detected_occasion}:{context.detected_budget}:{message.lower()}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, context: StylistContext, message: str) -> Optional[StylistResponse]:
        """Get cached response if available."""
        key = self._cache_key(context, message)
        
        redis = await self._get_redis()
        if redis:
            try:
                cached = await redis.get(key)
                if cached:
                    data = json.loads(cached)
                    data["cached"] = True
                    return StylistResponse(**data)
            except Exception as e:
                logger.warning(f"Cache get error: {e}")
        else:
            if key in self._memory_cache:
                data = self._memory_cache[key]
                data["cached"] = True
                return StylistResponse(**data)
        
        return None
    
    async def set(self, context: StylistContext, message: str, response: StylistResponse):
        """Cache a response."""
        key = self._cache_key(context, message)
        
        redis = await self._get_redis()
        data = {
            "content": response.content,
            "detected_occasion": response.detected_occasion,
            "detected_budget": response.detected_budget,
            "detected_style": response.detected_style,
            "detected_colors": response.detected_colors,
            "outfit_suggestions": response.outfit_suggestions,
            "product_recommendations": response.product_recommendations,
            "wardrobe_suggestions": response.wardrobe_suggestions,
            "style_tips": response.style_tips,
            "tokens_used": response.tokens_used,
            "model_version": response.model_version,
        }
        
        if redis:
            try:
                await redis.setex(key, self._ttl, json.dumps(data))
            except Exception as e:
                logger.warning(f"Cache set error: {e}")
        else:
            self._memory_cache[key] = data


# ── Main AI Stylist Service ───────────────────────────────────────────────

class AIStylistService:
    """
    Enhanced AI-powered fashion styling service.
    
    Features:
    - LLM integration with Groq/OpenAI
    - Prompt engineering for fashion expertise
    - User context injection (profile, wardrobe, preferences)
    - Intent detection (occasion, budget, style, colors)
    - Response caching
    - Rule-based fallback when no API key
    """
    
    def __init__(
        self,
        db: Session = None,
        llm_provider: str = None,
        llm_api_key: str = None,
        llm_model: str = None,
    ):
        self.db = db
        self.llm = LLMProvider(llm_provider, llm_api_key, llm_model)
        self.cache = ResponseCache()
        self.prompt_engineer = PromptEngineer()
    
    async def chat(
        self,
        user_message: str,
        context: StylistContext,
    ) -> StylistResponse:
        """
        Process a chat message and return a styling response.
        
        Args:
            user_message: The user's message
            context: StylistContext with user profile, wardrobe, conversation history
            
        Returns:
            StylistResponse with content and recommendations
        """
        start_time = datetime.now(timezone.utc)
        
        # Detect intent from message
        detected = IntentDetector.detect_all(user_message)
        context.detected_occasion = context.detected_occasion or detected["occasion"]
        context.detected_budget = context.detected_budget or detected["budget"]
        context.detected_style = context.detected_style or detected["style"]
        context.detected_colors = detected["colors"]
        
        # Check cache
        cached = await self.cache.get(context, user_message)
        if cached:
            cached.response_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return cached
        
        # Try LLM generation
        if self.llm._has_api:
            try:
                # JSON-first generation: ask the model to produce structured outfit JSON.
                # The UI already has local outfit builds as fallback; this improves trust,
                # and lets us extract an explanation reliably.
                json_features = extract_json_features(user_message)
                json_user_prompt = build_stylist_json_prompt(user_message, json_features)
                messages = self.prompt_engineer.build_messages(context, json_user_prompt)
                content, tokens = await self.llm.generate(messages)

                parsed = safe_extract_stylist_json(content)
                response_content = content
                outfit_suggestions: List[Dict[str, Any]] = []

                if parsed:
                    response_content = str(parsed.get("explanation") or content)

                    # Optional: convert the structured outfit JSON into the existing
                    # outfitSuggestions model (best-effort; images may be empty).
                    try:
                        outfit = parsed.get("outfit") or {}
                        total_price = parsed.get("total_price")
                        if isinstance(total_price, (int, float)):
                            outfit_suggestions.append(
                                {
                                    "id": "json-outfit-main",
                                    "name": "CONFIT JSON Look",
                                    "price": float(total_price),
                                    "styleScore": 90,
                                    "image": "",
                                }
                            )
                    except Exception:
                        outfit_suggestions = []

                    # Alternatives: treat as additional suggestions (max 3).
                    alternatives = parsed.get("alternatives") or []
                    if isinstance(alternatives, list):
                        for idx, alt in enumerate(alternatives[:3]):
                            if not isinstance(alt, dict):
                                continue
                            alt_total = alt.get("total_price")
                            variant_reason = alt.get("variant_reason") or f"Alternative {idx + 1}"
                            if isinstance(alt_total, (int, float)):
                                outfit_suggestions.append(
                                    {
                                        "id": f"json-outfit-alt-{idx}",
                                        "name": str(variant_reason),
                                        "price": float(alt_total),
                                        "styleScore": 86,
                                        "image": "",
                                    }
                                )

                response = StylistResponse(
                    content=response_content,
                    detected_occasion=context.detected_occasion,
                    detected_budget=context.detected_budget,
                    detected_style=context.detected_style,
                    detected_colors=context.detected_colors,
                    tokens_used=tokens,
                    model_version=self.llm.model,
                )

                if outfit_suggestions:
                    response.outfit_suggestions = outfit_suggestions
                
                # Generate recommendations based on context
                if not response.outfit_suggestions:
                    await self._generate_recommendations(response, context)
                
                # Cache the response
                await self.cache.set(context, user_message, response)
                
                response.response_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                return response
                
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
        
        # Fallback to rule-based response
        response = self._rule_based_response(user_message, context)
        response.response_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        return response
    
    async def _generate_recommendations(self, response: StylistResponse, context: StylistContext):
        """Generate product/outfit recommendations based on context."""
        # This will be implemented with product catalog integration
        # For now, use the existing outfit suggestions from stylist_service
        from services.stylist_service import OUTFIT_SUGGESTIONS
        
        if context.detected_occasion and context.detected_occasion in OUTFIT_SUGGESTIONS:
            response.outfit_suggestions = OUTFIT_SUGGESTIONS[context.detected_occasion]
    
    def _rule_based_response(self, message: str, context: StylistContext) -> StylistResponse:
        """Generate response using rule-based logic when LLM is unavailable."""
        from services.stylist_service import (
            VirtualStylistService, OCCASION_RESPONSES, COLOR_ADVICE
        )
        
        service = VirtualStylistService()
        result = service._rule_based_chat(
            message,
            context.detected_occasion,
            context.detected_budget,
            context.detected_style,
        )
        
        return StylistResponse(
            content=result.get("content", ""),
            detected_occasion=result.get("detectedOccasion"),
            detected_budget=context.detected_budget,
            detected_style=context.detected_style,
            detected_colors=context.detected_colors,
            outfit_suggestions=result.get("outfitSuggestions", []),
        )
    
    def health(self) -> Dict[str, Any]:
        """Health check for the service."""
        return {
            "status": "healthy",
            "llm_provider": self.llm.provider,
            "llm_available": self.llm._has_api,
            "model": self.llm.model,
        }
