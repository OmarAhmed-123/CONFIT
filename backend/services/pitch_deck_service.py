"""
CONFIT Backend — Investor Pitch Deck Service
==============================================
Generates pitch-deck slide structures (title + bullets) for the frontend.
This is deterministic and does not require external LLM calls.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal


PitchVariant = Literal["A", "B"]


def generate_pitch_deck(variant: PitchVariant = "A") -> Dict[str, Any]:
    """
    Returns:
      { "deckTitle": string, "slides": [{ "title": string, "bullets": [string] }] }
    """
    deck_title = "CONFIT — Investor Pitch"

    variant_hooks: Dict[str, Dict[str, str]] = {
        "A": {
            "vision_line": "AI that converts confidence into wear-now outfits.",
            "demo_line": "Prompt → structured build → Try-On → edit loop.",
            "market_line": "Personal styling at scale, powered by trust-first AI.",
        },
        "B": {
            "vision_line": "A billion-dollar closet experience that feels instant and trustworthy.",
            "demo_line": "User intent → style logic → outfit cards you can refine.",
            "market_line": "Fashion discovery rebuilt with clarity, speed, and personalization.",
        },
    }

    hooks = variant_hooks.get(variant, variant_hooks["A"])

    slides: List[Dict[str, Any]] = [
        {
            "id": "s1",
            "title": "Vision",
            "bullets": [
                "Make fashion decisions feel safe, fast, and exciting.",
                hooks["vision_line"],
                "Apple-level UX: clarity in seconds, refinement in minutes.",
            ],
        },
        {
            "id": "s2",
            "title": "Problem",
            "bullets": [
                "Choosing what to wear is slow, noisy, and emotionally expensive.",
                "Users face decision fatigue and don’t trust “suggestions.”",
                "Buyers need proof: fit, budget fit, and style logic.",
            ],
        },
        {
            "id": "s3",
            "title": "Solution (CONFIT)",
            "bullets": [
                "Natural-language AI stylist that returns structured outfit builds.",
                "Try-On + edit loop so confidence compounds with every refinement.",
                "Budget optimizer + color harmony explanations to build trust.",
            ],
        },
        {
            "id": "s4",
            "title": "Product Demo",
            "bullets": [
                hooks["demo_line"],
                "Replace items without losing the vibe.",
                "Outcome: “I need this now” energy, not guesswork.",
            ],
        },
        {
            "id": "s5",
            "title": "Market Opportunity",
            "bullets": [
                hooks["market_line"],
                "Styling is huge; trust-first AI is the missing layer.",
                "From MVP to personalization → wardrobe → marketplace → social.",
            ],
        },
        {
            "id": "s6",
            "title": "Business Model",
            "bullets": [
                "Brand commissions on assisted purchases.",
                "Premium subscription for deeper personalization and perks.",
                "Featured placements powered by recommendation relevance.",
            ],
        },
        {
            "id": "s7",
            "title": "Traction (Placeholder)",
            "bullets": [
                "Early pilot: users return to refine outfits repeatedly.",
                "Strong engagement signals: Try-On loops drive time-to-commit.",
                "Next milestone: conversions from AI builds to purchases.",
            ],
        },
        {
            "id": "s8",
            "title": "Future Vision",
            "bullets": [
                "Phase 1: AI styling MVP + try-on.",
                "Phase 2: wardrobe + personalization.",
                "Phase 3: marketplace + brand storefronts.",
                "Phase 4: community, sharing, and viral AI looks.",
            ],
        },
    ]

    return {"deckTitle": deck_title, "variant": variant, "slides": slides}

