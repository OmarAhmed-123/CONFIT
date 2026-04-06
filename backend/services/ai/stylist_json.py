"""
CONFIT — StylER JSON Brain (Python-ready)
===========================================
This module provides:
- Natural language extraction (occasion, budget, style, mood, season)
- Prompt engineering for structured JSON output
- Safe JSON extraction helper (robust to surrounding text)

Frontend can trust JSON because parsing is deterministic and bounded.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


OCCASION_MAP: Dict[str, List[str]] = {
    "wedding": ["wedding", "bride", "groom", "marriage", "nuptial", "ceremony"],
    "work": ["work", "office", "business", "meeting", "interview", "professional", "corporate"],
    "party": ["party", "club", "night out", "birthday", "celebration", "celebration mode"],
    "date": ["date", "dinner date", "romantic", "anniversary", "first date"],
    "casual": ["casual", "everyday", "weekend", "relaxed", "lounge", "shopping"],
    "active": ["gym", "workout", "exercise", "run", "running", "yoga", "sport", "athletic"],
    "formal": ["formal", "gala", "black tie", "red carpet", "award"],
}

STYLE_MAP: Dict[str, List[str]] = {
    "classic": ["classic", "timeless", "traditional", "elegant"],
    "modern": ["modern", "contemporary", "trendy", "current"],
    "minimalist": ["minimalist", "minimal", "clean", "capsule"],
    "bohemian": ["bohemian", "boho", "flowy", "free-spirited", "hippie"],
    "streetwear": ["streetwear", "street", "urban", "sneaker", "hypebeast"],
    "edgy": ["edgy", "rock", "punk", "alternative", "bold"],
}

MOOD_MAP: Dict[str, List[str]] = {
    "confident": ["confident", "bold", "power", "strong"],
    "soft": ["soft", "romantic", "feminine", "delicate"],
    "energetic": ["energetic", "fun", "playful", "vibrant", "party-ready"],
    "calm": ["calm", "serene", "relaxed"],
}

SEASON_MAP: Dict[str, List[str]] = {
    "spring": ["spring", "springtime"],
    "summer": ["summer", "hot", "summer-ready", "vacation"],
    "fall": ["fall", "autumn", "cozy", "crisp"],
    "winter": ["winter", "cold", "snow", "layered"],
}


def _contains_any(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return any(n.lower() in t for n in needles)


def extract_features(user_request: str) -> Dict[str, Optional[str]]:
    """
    Extract user constraints using keyword + pattern matching.
    Budget levels are normalized to: budget | moderate | premium | luxury
    """
    t = user_request.lower()

    occasion: Optional[str] = None
    for k, keywords in OCCASION_MAP.items():
        if _contains_any(t, keywords):
            occasion = k
            break

    style: Optional[str] = None
    for k, keywords in STYLE_MAP.items():
        if _contains_any(t, keywords):
            style = k
            break

    mood: Optional[str] = None
    for k, keywords in MOOD_MAP.items():
        if _contains_any(t, keywords):
            mood = k
            break

    season: Optional[str] = None
    for k, keywords in SEASON_MAP.items():
        if _contains_any(t, keywords):
            season = k
            break

    budget_level: Optional[str] = None
    # Numeric caps -> level normalization
    m = re.search(r"(under|below|<=|max)\s*\$?\s*([\d,]+)", t)
    if m and m.group(2):
        raw = m.group(2).replace(",", "")
        try:
            cap = float(raw)
            if cap <= 100:
                budget_level = "budget"
            elif cap <= 300:
                budget_level = "moderate"
            elif cap <= 500:
                budget_level = "premium"
            else:
                budget_level = "luxury"
        except Exception:
            budget_level = None

    # Keyword-based fallback
    if budget_level is None:
        if any(k in t for k in ["cheap", "inexpensive", "budget"]):
            budget_level = "budget"
        elif any(k in t for k in ["moderate", "mid", "affordable"]):
            budget_level = "moderate"
        elif any(k in t for k in ["premium", "quality", "investment"]):
            budget_level = "premium"
        elif any(k in t for k in ["luxury", "designer", "high-end", "expensive"]):
            budget_level = "luxury"

    return {
        "occasion": occasion,
        "budget": budget_level,
        "style": style,
        "mood": mood,
        "season": season,
    }


def build_stylist_json_prompt(user_request: str, extracted: Dict[str, Optional[str]]) -> str:
    """
    Builds the LLM prompt that forces structured JSON.
    Prompt includes the user request and extracted constraints.
    """
    extracted_block = json.dumps(extracted, ensure_ascii=False, indent=2)

    return (
        "You are an elite fashion stylist.\n"
        "Your job is to create stylish, realistic outfits.\n\n"
        "Constraints:\n"
        "- Stay within budget (if provided)\n"
        "- Ensure color harmony\n"
        "- Match occasion perfectly (if detected)\n"
        "- Suggest modern trends while keeping it wearable\n"
        "- Do not invent product URLs\n\n"
        "User request:\n"
        f"{user_request}\n\n"
        "Extracted constraints (may be null if not detected):\n"
        f"{extracted_block}\n\n"
        "Return JSON only (no markdown), with this exact shape:\n"
        "{\n"
        '  "outfit": {\n'
        '    "top": { "name": string, "price": number },\n'
        '    "bottom": { "name": string, "price": number },\n'
        '    "shoes": { "name": string, "price": number },\n'
        '    "accessories": [ { "name": string, "price": number } ]\n'
        "  },\n"
        '  "total_price": number,\n'
        '  "explanation": string,\n'
        '  "alternatives": [\n'
        "    {\n"
        '      "variant_reason": string,\n'
        '      "outfit": {\n'
        '        "top": { "name": string, "price": number },\n'
        '        "bottom": { "name": string, "price": number },\n'
        '        "shoes": { "name": string, "price": number },\n'
        '        "accessories": [ { "name": string, "price": number } ]\n'
        "      },\n"
        '      "total_price": number\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "\n"
        "Quality rules:\n"
        "- Prices should be plausible and sum to total_price.\n"
        "- Explanation must mention budget fit + color harmony in 1-2 sentences.\n"
        "- Alternatives must stay within the same occasion and budget band.\n"
    )


def _extract_first_json_object(text: str) -> Optional[str]:
    """
    Extracts the first top-level JSON object substring from possibly noisy text.
    """
    if not text:
        return None

    # Prefer fenced JSON blocks first.
    fence = re.search(r"```json\\s*({[\\s\\S]*?})\\s*```", text, flags=re.IGNORECASE)
    if fence:
        return fence.group(1)

    # Fallback: find first '{' and attempt balanced braces.
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def safe_extract_stylist_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Safely parses the JSON structure if present.
    Returns None if parsing fails or shape is invalid.
    """
    candidate = _extract_first_json_object(text)
    if not candidate:
        return None

    try:
        data = json.loads(candidate)
    except Exception:
        return None

    # Minimal schema validation.
    if not isinstance(data, dict):
        return None
    if "outfit" not in data or "total_price" not in data:
        return None
    if not isinstance(data["outfit"], dict):
        return None
    return data

