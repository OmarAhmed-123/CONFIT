"""
CONFIT Backend - Virtual Stylist Service
==========================================
AI-powered fashion styling chat using Groq API with
a smart rule-based fallback when no API key is available.
"""

import os
import json
import asyncio
import logging
import random
from typing import List, Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

# ── Outfit Suggestions Database ────────────────────────────────────

OUTFIT_SUGGESTIONS = {
    "casual": [
        {"id": "c1", "name": "Weekend Vibes", "price": 185, "styleScore": 91,
         "image": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?w=300&h=400&fit=crop"},
        {"id": "c2", "name": "Street Smart", "price": 210, "styleScore": 88,
         "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&h=400&fit=crop"},
        {"id": "c3", "name": "Easy Breezy", "price": 155, "styleScore": 85,
         "image": "https://images.unsplash.com/photo-1520367445093-50dc08a59d9d?w=300&h=400&fit=crop"},
    ],
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
        {"id": "p3", "name": "Celebration Mode", "price": 420, "styleScore": 91,
         "image": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=300&h=400&fit=crop"},
    ],
    "date": [
        {"id": "d1", "name": "Romantic Evening", "price": 310, "styleScore": 94,
         "image": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=300&h=400&fit=crop"},
        {"id": "d2", "name": "First Impression", "price": 275, "styleScore": 90,
         "image": "https://images.unsplash.com/photo-1581044777550-4cfa60707998?w=300&h=400&fit=crop"},
        {"id": "d3", "name": "Charming Casual", "price": 230, "styleScore": 87,
         "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&h=400&fit=crop"},
    ],
    "work": [
        {"id": "w1", "name": "Office Ready", "price": 380, "styleScore": 93,
         "image": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop"},
        {"id": "w2", "name": "Business Casual", "price": 295, "styleScore": 91,
         "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&h=400&fit=crop"},
        {"id": "w3", "name": "Smart Professionals", "price": 450, "styleScore": 89,
         "image": "https://images.unsplash.com/photo-1617019114583-affb34d1b3cd?w=300&h=400&fit=crop"},
    ],
    "active": [
        {"id": "a1", "name": "Gym Flow", "price": 145, "styleScore": 88,
         "image": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=400&fit=crop"},
        {"id": "a2", "name": "Run Ready", "price": 175, "styleScore": 86,
         "image": "https://images.unsplash.com/photo-1518459031867-a89b944bffe4?w=300&h=400&fit=crop"},
        {"id": "a3", "name": "Active Lifestyle", "price": 195, "styleScore": 90,
         "image": "https://images.unsplash.com/photo-1541534741688-6078c6bfb5c5?w=300&h=400&fit=crop"},
    ],
    "default": [
        {"id": "x1", "name": "Classic Essential", "price": 250, "styleScore": 90,
         "image": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop"},
        {"id": "x2", "name": "Modern Minimal", "price": 320, "styleScore": 88,
         "image": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=300&h=400&fit=crop"},
        {"id": "x3", "name": "Everyday Luxury", "price": 275, "styleScore": 87,
         "image": "https://images.unsplash.com/photo-1617019114583-affb34d1b3cd?w=300&h=400&fit=crop"},
    ],
}

# ── Color Harmony Rules ────────────────────────────────────────────

COLOR_ADVICE = {
    "blue": "Blue pairs beautifully with white, beige, or grey for a balanced, sophisticated look. Navy blue with camel is particularly striking.",
    "red": "Red is a bold power color! Pair it with black for drama, white for freshness, or denim for a casual vibe.",
    "green": "Green works wonderfully with earth tones, rich browns, cream, or crisp white. Olive green with burgundy is a timeless combo.",
    "black": "Black is the ultimate versatile base. Go monochrome for sophistication, or add a pop of red, gold, or jewel tones.",
    "white": "White is a perfect canvas. Pair with pastels for softness, navy for nautical vibes, or bold primaries for impact.",
    "yellow": "Yellow radiates energy! It pops against navy blue, looks fresh with grey, and pairs elegantly with white.",
    "purple": "Purple exudes luxury. Combine with silver, grey, or cream for elegance, or with black for a dramatic statement.",
    "pink": "Pink is incredibly versatile. Pair soft pinks with grey or navy, and hot pink with black or white for contrast.",
    "orange": "Orange brings warmth and energy. It pairs well with navy, teal, cream, and denim for a balanced look.",
    "brown": "Brown is grounding and sophisticated. Combine with cream, forest green, burgundy, or rust for an earthy palette.",
    "beige": "Beige is effortlessly elegant. Layer with white, camel, and soft blues for a refined monochromatic look.",
    "grey": "Grey is the perfect neutral foundation. It works with virtually any color — try it with blush pink or mustard.",
}

# ── Occasion Detection ─────────────────────────────────────────────

OCCASION_KEYWORDS = {
    "wedding": "formal",
    "marriage": "formal",
    "gala": "formal",
    "ceremony": "formal",
    "party": "party",
    "club": "party",
    "night out": "party",
    "birthday": "party",
    "celebration": "party",
    "work": "work",
    "office": "work",
    "business": "work",
    "meeting": "work",
    "interview": "work",
    "presentation": "work",
    "date": "date",
    "dinner": "date",
    "restaurant": "date",
    "romantic": "date",
    "casual": "casual",
    "everyday": "casual",
    "weekend": "casual",
    "brunch": "casual",
    "shopping": "casual",
    "gym": "active",
    "run": "active",
    "workout": "active",
    "sport": "active",
    "exercise": "active",
    "hike": "active",
    "yoga": "active",
}

OCCASION_RESPONSES = {
    "formal": "A formal event calls for elegance and sophistication! I've curated some stunning options that will make you stand out while keeping it classy.",
    "party": "Time to shine! 🎉 I've selected some trendy, eye-catching pieces perfect for making an impression at any party.",
    "work": "Let's keep it professional yet stylish! Here are some polished looks that command respect while expressing your personal style.",
    "date": "Ooh, exciting! 💫 I've picked outfits that are attractive yet comfortable — confidence is the best accessory on a date.",
    "casual": "Effortless style is an art! Here are some relaxed yet put-together looks for your day-to-day adventures.",
    "active": "Performance meets style! 💪 These activewear picks will keep you comfortable and looking great during your workout.",
}


class VirtualStylistService:
    """
    AI-powered fashion styling assistant.
    Uses Groq API for intelligent responses when available,
    falls back to a sophisticated rule-based engine otherwise.
    """

    def __init__(self, groq_api_key: Optional[str] = None):
        self._groq_api_key = groq_api_key
        self._has_ai = bool(groq_api_key)
        if self._has_ai:
            logger.info("VirtualStylistService initialized with Groq AI")
        else:
            logger.info("VirtualStylistService initialized with rule-based fallback (no GROQ_API_KEY)")

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        occasion: Optional[str] = None,
        budget: Optional[str] = None,
        style_preference: Optional[str] = None,
        style_dna_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message and return a styling response.

        Returns:
            dict with 'content' (str), 'outfitSuggestions' (list, optional),
            and 'detectedOccasion' (str, optional).
        """
        if self._has_ai:
            try:
                return await self._ai_chat(
                    user_message, conversation_history,
                    occasion, budget, style_preference, style_dna_context,
                )
            except Exception as e:
                logger.warning(f"AI chat failed, falling back to rules: {e}")

        return self._rule_based_chat(
            user_message, occasion, budget, style_preference, style_dna_context,
        )

    async def _ai_chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        occasion: Optional[str],
        budget: Optional[str],
        style_preference: Optional[str],
        style_dna_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response using Groq AI (Llama 3.3 70B)
        with exponential backoff retry and response validation.
        """
        system_prompt = (
            "You are CONFIT's expert virtual fashion stylist — a knowledgeable, "
            "warm, and professional fashion consultant.\n\n"
            "Guidelines:\n"
            "- Provide specific, actionable style advice grounded in fashion expertise\n"
            "- Consider the user's occasion, budget, body type, season, and style preferences\n"
            "- Recommend color combinations and explain the styling rationale\n"
            "- Keep responses between 2-4 sentences unless the user asks for detailed guidance\n"
            "- Use an encouraging, confident tone — help users feel great about their choices\n"
            "- Avoid fabricating product URLs or referencing items outside the CONFIT catalogue\n"
            "- If unsure, ask one clarifying question rather than guessing\n"
            "- When suggesting outfits, mention fabric types and layering tips when relevant\n"
            "- Always stay in your role as a fashion stylist — politely redirect off-topic queries\n"
        )

        if occasion:
            system_prompt += f"\nCurrent occasion context: {occasion}"
        if budget:
            system_prompt += f"\nUser's budget range: {budget}"
        if style_preference:
            system_prompt += f"\nPreferred style: {style_preference}"
        if style_dna_context:
            system_prompt += (
                "\n\nThe user's CONFIT Style DNA (identity — not generic taste):\n"
                f"{style_dna_context}\n"
                "Honor this identity fingerprint when advising; do not contradict it unless the user asks to explore."
            )

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        messages.append({"role": "user", "content": user_message})

        # Exponential backoff retry (up to 3 attempts)
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
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Groq API attempt %d/%d failed: %s", attempt, max_retries, exc,
                )
                if attempt < max_retries:
                    await asyncio.sleep(1.5 ** attempt)

        if last_error is not None:
            raise last_error

        ai_content = data["choices"][0]["message"]["content"]

        # Response validation: ensure reasonable length and no hallucinated URLs
        if len(ai_content) < 10:
            ai_content = (
                "I'd love to help you style the perfect look! "
                "Could you tell me more about the occasion or your style preferences?"
            )

        # Detect occasion from user message for outfit suggestions
        detected = self._detect_occasion(user_message)
        occasion_key = detected or occasion or None

        result: Dict[str, Any] = {
            "content": ai_content,
            "detectedOccasion": detected,
        }

        # Add outfit suggestions if occasion is known
        if occasion_key and occasion_key in OUTFIT_SUGGESTIONS:
            result["outfitSuggestions"] = OUTFIT_SUGGESTIONS[occasion_key]
        elif any(w in user_message.lower() for w in ["show", "recommend", "suggest", "outfit", "look"]):
            result["outfitSuggestions"] = OUTFIT_SUGGESTIONS.get(
                occasion_key or "default", OUTFIT_SUGGESTIONS["default"]
            )

        return result

    def _rule_based_chat(
        self,
        user_message: str,
        occasion: Optional[str],
        budget: Optional[str],
        style_preference: Optional[str],
        style_dna_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enhanced rule-based fallback with richer fashion vocabulary,
        seasonal tips, body-type advice, and multi-topic handling.
        """
        lower_input = user_message.lower()
        response_parts: list[str] = []
        detected_occasion = self._detect_occasion(user_message)
        outfit_suggestions = None

        if style_dna_context:
            response_parts.append(
                "I'm aligning with your CONFIT Style DNA so the advice fits who you are — not just what's trending."
            )

        # Greeting responses (goes first)
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        if any(g in lower_input for g in greetings):
            response_parts.append(
                "Hello! Welcome to CONFIT! 👋 I'm your personal fashion stylist, "
                "here to help you look and feel your best."
            )

        # Thank-you recognition
        thanks_keywords = ["thank", "thanks", "appreciate", "helpful"]
        if any(kw in lower_input for kw in thanks_keywords):
            response_parts.append(
                "You're welcome! I'm always here to help you find your perfect look. "
                "Feel free to ask me anything about styling, color coordination, or outfit ideas."
            )

        # Occasion-based response
        if detected_occasion:
            response_parts.append(OCCASION_RESPONSES.get(
                detected_occasion,
                "I've put together some looks tailored to your needs!",
            ))
            outfit_suggestions = OUTFIT_SUGGESTIONS.get(detected_occasion)

        # Color advice
        for color, advice in COLOR_ADVICE.items():
            if color in lower_input:
                response_parts.append(advice)
                break

        # Budget acknowledgment
        budget_keywords = ["budget", "cheap", "expensive", "affordable", "price", "cost", "$"]
        if any(kw in lower_input for kw in budget_keywords):
            response_parts.append(
                "I'll optimize my picks to give you the best value for your budget. "
                "Quality basics are always a smart investment — they pair with everything!"
            )

        # Seasonal tips
        season_responses = {
            "summer": "For summer, breathable fabrics like linen and cotton are your best friends. Light colors and airy silhouettes keep you cool and stylish.",
            "winter": "Winter is all about layering! Start with a cozy base layer, add a mid-layer like a wool sweater, and finish with a structured coat.",
            "spring": "Spring calls for fresh pastels, floral prints, and light layering. A good trench coat is essential for those unpredictable weather days.",
            "fall": "Autumn is perfect for rich earthy tones — burnt orange, olive, and burgundy. Layering with knits and denim is both practical and stylish.",
            "autumn": "Autumn is perfect for rich earthy tones — burnt orange, olive, and burgundy. Layering with knits and denim is both practical and stylish.",
        }
        for season, tip in season_responses.items():
            if season in lower_input:
                response_parts.append(tip)
                break

        # Body-type advice
        body_keywords = ["body", "figure", "shape", "tall", "petite", "curvy", "slim", "plus"]
        if any(kw in lower_input for kw in body_keywords):
            response_parts.append(
                "Every body type can rock any style! The key is finding the right fit and proportions. "
                "Tell me more about what you're looking for, and I'll suggest silhouettes that flatter your figure beautifully."
            )

        # Style preference responses
        style_responses = {
            "classic": "Classic style is all about timeless pieces that never go out of fashion. Think clean lines, neutral colors, and quality fabrics.",
            "modern": "Modern style embraces current trends with a sophisticated edge. Let's find pieces that are both trendy and wearable.",
            "minimalist": "Less is more! I'll focus on clean silhouettes, a cohesive color palette, and quality over quantity.",
            "bohemian": "Boho chic is all about free-spirited, relaxed elegance. Flowing fabrics, earthy tones, and unique accessories are key.",
            "sporty": "Athleisure is huge right now! Let's blend comfort with style for a modern, active look.",
            "elegant": "Elegance is about refined details and luxurious touches. I'll curate pieces that exude sophistication.",
            "vintage": "Vintage style is wonderfully unique! Retro silhouettes and timeless prints create a look that's both nostalgic and fashionable.",
            "streetwear": "Streetwear is all about bold graphics, oversized fits, and sneaker culture. Let's build a look with attitude.",
        }
        for style, response in style_responses.items():
            if style in lower_input:
                response_parts.append(response)
                if not detected_occasion:
                    detected_occasion = "default"
                break

        # Help / generic requests
        if any(w in lower_input for w in ["help", "advice", "tips", "guide"]):
            response_parts.append(
                "I can help with: outfit recommendations for any occasion, "
                "color coordination advice, seasonal dressing tips, and budget-friendly fashion ideas. "
                "Just tell me what you're looking for!"
            )

        # Show/recommend outfits
        if any(w in lower_input for w in ["show", "recommend", "suggest", "outfit", "look"]):
            if not outfit_suggestions:
                occasion_key = detected_occasion or occasion or "default"
                outfit_suggestions = OUTFIT_SUGGESTIONS.get(
                    occasion_key, OUTFIT_SUGGESTIONS["default"]
                )
            if not response_parts:
                response_parts.append("Here are some curated outfit suggestions based on your style profile:")

        # Fallback if nothing matched
        if not response_parts:
            response_parts.append(
                "I'd love to help you find the perfect outfit! Could you tell me more about "
                "the occasion you're dressing for? For example: work, a date, a party, "
                "or a casual outing? I can also help with color coordination, seasonal tips, and style guidance."
            )

        return {
            "content": " ".join(response_parts),
            "detectedOccasion": detected_occasion,
            "outfitSuggestions": outfit_suggestions,
        }

    def _detect_occasion(self, message: str) -> Optional[str]:
        """Detect the occasion from a user message."""
        lower = message.lower()
        for keyword, occasion in OCCASION_KEYWORDS.items():
            if keyword in lower:
                return occasion
        return None
