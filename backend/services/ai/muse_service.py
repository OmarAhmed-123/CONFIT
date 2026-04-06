"""
CONFIT Backend - MUSE Virtual Stylist Service
=============================================
AI-powered personal styling assistant using OpenAI GPT-4o.

Features:
- Bilingual support (Arabic/English)
- RAG with Elasticsearch/pgvector
- Style profile integration
- Session context via Redis
- Rate limiting per user
- Cost tracking
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("MUSE_MODEL", "gpt-4o")
MUSE_MAX_TOKENS_IN = int(os.getenv("MUSE_MAX_TOKENS_IN", "4096"))
MUSE_MAX_TOKENS_OUT = int(os.getenv("MUSE_MAX_TOKENS_OUT", "1024"))
AI_DAILY_BUDGET_USD = float(os.getenv("AI_DAILY_BUDGET_USD", "100.0"))

# Pricing (GPT-4o as of 2024)
GPT4O_PRICE_INPUT_PER_1K = 0.005  # $5/1M tokens
GPT4O_PRICE_OUTPUT_PER_1K = 0.015  # $15/1M tokens


# System prompts
SYSTEM_PROMPT_EN = """You are MUSE, CONFIT's AI personal stylist. You help users discover their perfect style.

Your capabilities:
- Recommend outfits based on occasion, budget, and personal style
- Mix items from the user's closet with new catalog pieces
- Suggest styling tips and outfit combinations
- Answer fashion questions with expert knowledge

Guidelines:
- Be warm, encouraging, and fashion-forward
- Consider the user's "Your Signature" style profile
- Respect budget constraints
- Provide specific product recommendations when available
- Offer 2-3 outfit options when possible

When recommending products, use the recommend_outfits function with specific SKUs.
Always explain WHY each piece works together."""

SYSTEM_PROMPT_AR = """You are MUSE, CONFIT's AI personal stylist. You help users discover their perfect style. (Arabic version)

Your capabilities:
- Recommend outfits based on occasion, budget, and personal style
- Mix items from the user's closet with new catalog pieces
- Suggest styling tips and outfit combinations
- Answer fashion questions with expert knowledge

Guidelines:
- Be warm, encouraging, and fashion-forward
- Consider the user's "Your Signature" style profile
- Respect budget constraints
- Provide specific product recommendations when available
- Offer 2-3 outfit options when possible

When recommending products, use the recommend_outfits function with specific SKUs.
Always explain WHY each piece works together.

IMPORTANT: Respond in Arabic (Egyptian dialect preferred for casual contexts)."""


@dataclass
class MuseMessage:
    """A message in the Muse conversation."""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OutfitRecommendation:
    """A single outfit recommendation."""
    outfit_id: str
    title: str
    items: List[Dict[str, Any]]  # List of product info
    total_price: float
    currency: str = "USD"
    occasion: Optional[str] = None
    styling_tips: List[str] = field(default_factory=list)
    from_closet: List[str] = field(default_factory=list)  # Item IDs from user's closet
    from_catalog: List[str] = field(default_factory=list)  # SKUs from catalog


@dataclass
class MuseResponse:
    """Response from MUSE service."""
    reply: str
    outfits: List[OutfitRecommendation] = field(default_factory=list)
    follow_ups: List[str] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    session_id: str = ""


class MuseService:
    """
    MUSE Virtual Stylist Service.
    
    Usage:
        service = MuseService(db, redis_client)
        response = await service.chat(
            user_id="user-123",
            message="I need an outfit for a wedding",
            language="en"
        )
    """
    
    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.openai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
        # Cost tracker reference (will be set by dependency injection)
        self._cost_tracker = None
    
    def set_cost_tracker(self, cost_tracker):
        """Set the cost tracker for logging AI calls."""
        self._cost_tracker = cost_tracker
    
    # ==========================================
    # Main Chat Endpoint
    # ==========================================
    
    async def chat(
        self,
        user_id: str,
        message: str,
        language: str = "en",
        session_id: Optional[str] = None,
    ) -> MuseResponse:
        """
        Main chat endpoint for MUSE.
        
        Args:
            user_id: User UUID
            message: User's message
            language: "en" or "ar"
            session_id: Optional session ID for context continuity
            
        Returns:
            MuseResponse with reply, outfits, and metadata
        """
        start_time = time.perf_counter()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = f"muse-{uuid.uuid4().hex[:12]}"
        
        try:
            # 1. Get user's style profile
            style_profile = await self._get_style_profile(user_id)
            
            # 2. Get recent conversation context from Redis
            context_messages = await self._get_session_context(session_id)
            
            # 3. RAG: Search for relevant products
            relevant_products = await self._search_relevant_products(
                message, style_profile, language
            )
            
            # 4. Build messages for OpenAI
            messages = self._build_messages(
                user_message=message,
                language=language,
                style_profile=style_profile,
                context_messages=context_messages,
                relevant_products=relevant_products,
            )
            
            # 5. Call OpenAI GPT-4o
            response = await self._call_openai(messages, language)
            
            # 6. Parse response and extract outfit recommendations
            outfits, follow_ups = await self._parse_response(response, relevant_products)
            
            # 7. Store message in session context
            await self._store_message(session_id, "user", message)
            await self._store_message(session_id, "assistant", response.content)
            
            # Calculate metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            cost_usd = self._calculate_cost(
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
            
            # Track cost
            if self._cost_tracker:
                await self._cost_tracker.track(
                    service="muse",
                    model=OPENAI_MODEL,
                    user_id=user_id,
                    tokens_in=response.usage.prompt_tokens,
                    tokens_out=response.usage.completion_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                )
            
            return MuseResponse(
                reply=response.content,
                outfits=outfits,
                follow_ups=follow_ups,
                tokens_in=response.usage.prompt_tokens,
                tokens_out=response.usage.completion_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                session_id=session_id,
            )
            
        except Exception as e:
            logger.error(f"MUSE chat error: {e}")
            # Return fallback response
            return MuseResponse(
                reply=self._get_fallback_response(language),
                session_id=session_id,
            )
    
    # ==========================================
    # Helper Methods
    # ==========================================
    
    async def _get_style_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user's style profile from database."""
        try:
            from database.models import User, UserStyleProfile
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            profile = self.db.query(UserStyleProfile).filter(
                UserStyleProfile.user_id == user_id
            ).first()
            
            if not profile:
                # Return basic preferences from user record
                return {
                    "style_preference": user.style_preference,
                    "budget_range": user.budget_range,
                    "preferred_brands": user.preferred_brands,
                    "occasion_preferences": user.occasion_preferences,
                }
            
            return {
                "style_preference": profile.style_preference,
                "budget_range": profile.budget_range,
                "preferred_brands": profile.preferred_brands,
                "occasion_preferences": profile.occasion_preferences,
                "color_preferences": profile.color_preferences,
                "fit_preferences": profile.fit_preferences,
                "style_archetype": profile.style_archetype,
                "confidence_level": profile.confidence_level,
            }
            
        except Exception as e:
            logger.warning(f"Failed to get style profile: {e}")
            return {}
    
    async def _get_session_context(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent messages from Redis session context."""
        if not self.redis:
            return []
        
        try:
            key = f"muse:session:{session_id}:messages"
            messages = self.redis.lrange(key, -limit, -1)
            return [json.loads(msg) for msg in messages]
        except Exception as e:
            logger.warning(f"Failed to get session context: {e}")
            return []
    
    async def _store_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """Store message in Redis session context."""
        if not self.redis:
            return
        
        try:
            key = f"muse:session:{session_id}:messages"
            message = json.dumps({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self.redis.rpush(key, message)
            # Expire after 24 hours
            self.redis.expire(key, 86400)
        except Exception as e:
            logger.warning(f"Failed to store message: {e}")
    
    async def _search_relevant_products(
        self,
        message: str,
        style_profile: Dict[str, Any],
        language: str
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant products using RAG.
        
        Uses Elasticsearch for text search and pgvector for similarity.
        """
        products = []
        
        try:
            # Try Elasticsearch first
            products = await self._search_elasticsearch(message, style_profile)
            
            # If not enough results, try pgvector
            if len(products) < 10:
                vector_products = await self._search_pgvector(message, style_profile)
                products.extend(vector_products)
            
            # Deduplicate by SKU
            seen = set()
            unique = []
            for p in products:
                sku = p.get("sku") or p.get("id")
                if sku and sku not in seen:
                    seen.add(sku)
                    unique.append(p)
            
            return unique[:20]
            
        except Exception as e:
            logger.warning(f"Product search failed: {e}")
            return []
    
    async def _search_elasticsearch(
        self,
        query: str,
        style_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search products using Elasticsearch."""
        try:
            from elasticsearch import AsyncElasticsearch
            
            es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            es = AsyncElasticsearch([es_url])
            
            # Build query with filters
            filters = []
            
            # Add brand filter if preferred
            if style_profile.get("preferred_brands"):
                filters.append({
                    "terms": {"brand_id": style_profile["preferred_brands"]}
                })
            
            # Add price range filter
            if style_profile.get("budget_range"):
                budget = style_profile["budget_range"]
                if budget.get("min") or budget.get("max"):
                    price_filter = {"range": {"price": {}}}
                    if budget.get("min"):
                        price_filter["range"]["price"]["gte"] = budget["min"]
                    if budget.get("max"):
                        price_filter["range"]["price"]["lte"] = budget["max"]
                    filters.append(price_filter)
            
            # Execute search
            response = await es.search(
                index="products",
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["name^2", "description", "category", "tags"],
                                        "fuzziness": "AUTO",
                                    }
                                }
                            ],
                            "filter": filters if filters else [],
                        }
                    },
                    "size": 15,
                }
            )
            
            await es.close()
            
            # Parse results
            products = []
            for hit in response.get("hits", {}).get("hits", []):
                source = hit["_source"]
                products.append({
                    "id": hit["_id"],
                    "sku": source.get("sku"),
                    "name": source.get("name"),
                    "brand": source.get("brand_id"),
                    "price": source.get("price"),
                    "currency": source.get("currency", "USD"),
                    "category": source.get("category"),
                    "image_url": source.get("image_url"),
                    "url": source.get("url"),
                })
            
            return products
            
        except Exception as e:
            logger.debug(f"Elasticsearch search failed: {e}")
            return []
    
    async def _search_pgvector(
        self,
        query: str,
        style_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search products using pgvector embeddings."""
        try:
            from sqlalchemy import text
            
            # Generate embedding for query (would use CLIP or similar)
            # For now, use a simple text-based approach
            query_embedding = await self._generate_query_embedding(query)
            
            if not query_embedding:
                return []
            
            # Convert to string for SQL
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            # Search using cosine similarity
            sql = text("""
                SELECT 
                    id, sku, name, brand_id, price, currency, category, image_url,
                    1 - (embedding <=> :embedding::vector) as similarity
                FROM products
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> :embedding::vector
                LIMIT 15
            """)
            
            result = self.db.execute(sql, {"embedding": embedding_str})
            rows = result.fetchall()
            
            products = []
            for row in rows:
                products.append({
                    "id": str(row.id),
                    "sku": row.sku,
                    "name": row.name,
                    "brand": row.brand_id,
                    "price": float(row.price) if row.price else None,
                    "currency": row.currency or "USD",
                    "category": row.category,
                    "image_url": row.image_url,
                    "similarity": float(row.similarity) if row.similarity else 0,
                })
            
            return products
            
        except Exception as e:
            logger.debug(f"pgvector search failed: {e}")
            return []
    
    async def _generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for query text."""
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(query)
            return embedding.tolist()
            
        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
            return None
    
    def _build_messages(
        self,
        user_message: str,
        language: str,
        style_profile: Dict[str, Any],
        context_messages: List[Dict[str, str]],
        relevant_products: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Build messages array for OpenAI API."""
        messages = []
        
        # System prompt
        system_prompt = SYSTEM_PROMPT_AR if language == "ar" else SYSTEM_PROMPT_EN
        messages.append({"role": "system", "content": system_prompt})
        
        # Add style profile context
        if style_profile:
            profile_context = self._format_style_profile(style_profile, language)
            messages.append({"role": "system", "content": profile_context})
        
        # Add available products
        if relevant_products:
            products_context = self._format_products(relevant_products, language)
            messages.append({"role": "system", "content": products_context})
        
        # Add conversation context
        for msg in context_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _format_style_profile(
        self,
        profile: Dict[str, Any],
        language: str
    ) -> str:
        """Format style profile for context."""
        if language == "ar":
            parts = ["### User Style Profile (Your Signature)\n"]
            if profile.get("style_archetype"):
                parts.append(f"Style: {profile['style_archetype']}")
            if profile.get("color_preferences"):
                parts.append(f"Preferred colors: {', '.join(profile['color_preferences'])}")
            if profile.get("budget_range"):
                budget = profile["budget_range"]
                if budget.get("max"):
                    parts.append(f"Budget: up to ${budget['max']}")
            if profile.get("preferred_brands"):
                parts.append(f"Favorite brands: {', '.join(profile['preferred_brands'])}")
        else:
            parts = ["### User Style Profile (Your Signature)\n"]
            if profile.get("style_archetype"):
                parts.append(f"Style archetype: {profile['style_archetype']}")
            if profile.get("color_preferences"):
                parts.append(f"Preferred colors: {', '.join(profile['color_preferences'])}")
            if profile.get("budget_range"):
                budget = profile["budget_range"]
                if budget.get("max"):
                    parts.append(f"Budget: up to ${budget['max']}")
            if profile.get("preferred_brands"):
                parts.append(f"Favorite brands: {', '.join(profile['preferred_brands'])}")
        
        return "\n".join(parts)
    
    def _format_products(
        self,
        products: List[Dict[str, Any]],
        language: str
    ) -> str:
        """Format available products for context."""
        if language == "ar":
            header = "### Available Products for Recommendations\n"
        else:
            header = "### Available Products for Recommendations\n"
        
        lines = [header]
        for i, p in enumerate(products[:15], 1):
            price_str = f"${p.get('price', 'N/A')}" if p.get('price') else ""
            lines.append(
                f"{i}. SKU: {p.get('sku', p.get('id'))} | "
                f"{p.get('name', 'Unknown')} | "
                f"{p.get('brand', '')} | "
                f"{price_str} | "
                f"Category: {p.get('category', '')}"
            )
        
        return "\n".join(lines)
    
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        language: str
    ):
        """Call OpenAI GPT-4o API."""
        if not self.openai:
            raise ValueError("OpenAI API key not configured")
        
        # Define function for outfit recommendations
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "recommend_outfits",
                    "description": "Recommend outfit combinations with specific products",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "outfits": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "skus": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "occasion": {"type": "string"},
                                        "styling_tips": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                    },
                                    "required": ["title", "skus"]
                                }
                            },
                            "follow_up_questions": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["outfits"]
                    }
                }
            }
        ]
        
        response = await self.openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=MUSE_MAX_TOKENS_OUT,
            temperature=0.7,
        )
        
        return response.choices[0]
    
    async def _parse_response(
        self,
        response,
        products: List[Dict[str, Any]]
    ) -> tuple[List[OutfitRecommendation], List[str]]:
        """Parse OpenAI response and extract outfit recommendations."""
        outfits = []
        follow_ups = []
        
        # Check for function call
        if response.message.tool_calls:
            for tool_call in response.message.tool_calls:
                if tool_call.function.name == "recommend_outfits":
                    args = json.loads(tool_call.function.arguments)
                    
                    # Build product lookup
                    product_map = {p.get("sku") or p.get("id"): p for p in products}
                    
                    for outfit_data in args.get("outfits", []):
                        outfit_items = []
                        skus = outfit_data.get("skus", [])
                        
                        for sku in skus:
                            if sku in product_map:
                                outfit_items.append(product_map[sku])
                        
                        total_price = sum(
                            float(p.get("price", 0) or 0)
                            for p in outfit_items
                        )
                        
                        outfit = OutfitRecommendation(
                            outfit_id=f"outfit-{uuid.uuid4().hex[:8]}",
                            title=outfit_data.get("title", "Recommended Outfit"),
                            items=outfit_items,
                            total_price=total_price,
                            occasion=outfit_data.get("occasion"),
                            styling_tips=outfit_data.get("styling_tips", []),
                            from_catalog=skus,
                        )
                        outfits.append(outfit)
                    
                    follow_ups = args.get("follow_up_questions", [])
        
        return outfits, follow_ups
    
    def _calculate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Calculate cost in USD for the API call."""
        cost_in = (tokens_in / 1000) * GPT4O_PRICE_INPUT_PER_1K
        cost_out = (tokens_out / 1000) * GPT4O_PRICE_OUTPUT_PER_1K
        return cost_in + cost_out
    
    def _get_fallback_response(self, language: str) -> str:
        """Get fallback response when service fails."""
        if language == "ar":
            return (
                "I apologize, I'm having some technical difficulties right now. "
                "Please try again in a moment, or browse our collections for inspiration!"
            )
        return (
            "I apologize, I'm having some technical difficulties right now. "
            "Please try again in a moment, or browse our collections for inspiration!"
        )
    
    # ==========================================
    # Rate Limiting Helpers
    # ==========================================
    
    async def check_rate_limit(self, user_id: str, tier: str = "free") -> tuple[bool, int]:
        """
        Check if user is within rate limits.
        
        Returns:
            (is_allowed, retry_after_seconds)
        """
        if not self.redis:
            return True, 0
        
        limits = {
            "free": 20,      # 20 messages per hour
            "club": 100,     # 100 messages per hour
            "icon": 500,     # 500 messages per hour (donors)
        }
        
        limit = limits.get(tier, 20)
        key = f"muse:ratelimit:{user_id}"
        
        try:
            current = self.redis.get(key)
            if current is None:
                # First message, set expiry
                self.redis.setex(key, 3600, 1)
                return True, 0
            
            count = int(current)
            if count >= limit:
                ttl = self.redis.ttl(key)
                return False, max(ttl, 1)
            
            self.redis.incr(key)
            return True, 0
            
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True, 0
    
    # ==========================================
    # Session Management
    # ==========================================
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get full session history."""
        if not self.redis:
            return []
        
        try:
            key = f"muse:session:{session_id}:messages"
            messages = self.redis.lrange(key, 0, limit - 1)
            return [json.loads(msg) for msg in messages]
        except Exception as e:
            logger.warning(f"Failed to get session history: {e}")
            return []
    
    async def clear_session(self, session_id: str) -> bool:
        """Clear a session's context."""
        if not self.redis:
            return True
        
        try:
            key = f"muse:session:{session_id}:messages"
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Failed to clear session: {e}")
            return False
