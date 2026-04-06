# GROUP 1 — USER IDENTITY & PROFILE MANAGEMENT
## Production-Level Audit & Expansion

**Project:** CONFIT — Confidence, Styled  
**Audit Date:** March 2026  
**Purpose:** Understand the user once, personalize forever.

---

# 1. COMPLETENESS SCORE

## Current Implementation Assessment

| Category | Score | Weight | Weighted |
|----------|-------|--------|----------|
| **Product Logic** | 45% | 25% | 11.25% |
| **Technical Implementation** | 60% | 20% | 12.00% |
| **UX Flow** | 35% | 15% | 5.25% |
| **AI Readiness** | 25% | 25% | 6.25% |
| **Privacy Compliance** | 50% | 15% | 7.50% |
| **TOTAL** | — | 100% | **42.25%** |

### Detailed Scoring

#### Product Logic (45%)
- ✅ Basic user registration & authentication
- ✅ Style preferences (single dimension)
- ✅ Body attributes (optional, unstructured)
- ✅ Budget range
- ✅ Preferred brands
- ✅ Occasion preferences
- ✅ Privacy consent flags
- ❌ No style evolution tracking
- ❌ No behavioral personalization
- ❌ No contextual preferences (weather, culture, lifestyle)
- ❌ No adaptive onboarding
- ❌ No confidence scoring methodology

#### Technical Implementation (60%)
- ✅ JWT-based authentication
- ✅ bcrypt password hashing
- ✅ SQLAlchemy ORM models
- ✅ Pydantic validation
- ✅ Role-based access (admin, brand_manager, stylist, user)
- ✅ Gamification integration
- ⚠️ Basic JSON fields (not queryable)
- ❌ No versioned profile schema
- ❌ No profile change audit trail
- ❌ No feature vector storage for AI

#### UX Flow (35%)
- ✅ Login/Register endpoints
- ✅ Profile update endpoint
- ❌ No style quiz / onboarding flow
- ❌ No progressive profiling
- ❌ No profile completeness indicator
- ❌ No style visualization

#### AI Readiness (25%)
- ✅ Basic preference data collection
- ❌ No embedding storage
- ❌ No feature signals
- ❌ No preference confidence weights
- ❌ No behavioral event tracking
- ❌ No wardrobe intelligence signals

#### Privacy Compliance (50%)
- ✅ Marketing consent flag
- ✅ Data sharing consent flag
- ❌ No GDPR data export
- ❌ No right to erasure implementation
- ❌ No consent versioning
- ❌ No data retention policies
- ❌ No privacy dashboard

---

# 2. MISSING FEATURES

## Critical Gaps (Must-Have for Launch)

### 2.1 Adaptive Onboarding System
```
MISSING:
- Style Personality Quiz (5-7 questions)
- Visual Style Preference Selection (image-based)
- Progressive Profile Building
- Profile Completeness Score & Nudges
- Skip/Continue Later functionality
```

### 2.2 Enhanced Style Profile
```
MISSING:
- Multi-dimensional style vectors (not single string)
- Style archetype classification (8-12 archetypes)
- Style confidence per dimension
- Seasonal style variations
- Color palette analysis (skin undertone + preferences)
- Pattern & print preferences
- Fabric & material preferences
- Fit preferences by category
```

### 2.3 Advanced Body Profile
```
MISSING:
- Structured measurements (not free-form JSON)
- Size profile by brand (brand-specific sizing)
- Fit issues history
- Body shape classification
- Proportion analysis
- Comfort zones
```

### 2.4 Behavioral Intelligence
```
MISSING:
- Browse behavior signals
- Purchase pattern analysis
- Wishlist behavior
- Try-on engagement metrics
- Style feedback loop
- Abandonment signals
```

### 2.5 Contextual Preferences
```
MISSING:
- Weather/climate preferences
- Cultural/regional style context
- Lifestyle segments (work, leisure, active)
- Social context preferences
- Event-specific styling history
```

### 2.6 Wardrobe Intelligence
```
MISSING:
- Wardrobe utilization metrics
- Gap analysis (what's missing)
- Item relationship mapping
- Cost-per-wear tracking
- Style versatility scores
```

### 2.7 AI Signal Infrastructure
```
MISSING:
- Feature vector storage
- Preference embedding space
- Real-time signal collection
- ML training data pipeline
- A/B testing infrastructure
```

### 2.8 Privacy & Compliance
```
MISSING:
- GDPR data export API
- Right to erasure
- Consent versioning & history
- Data retention automation
- Privacy dashboard UI
- Third-party data sharing logs
```

---

# 3. NEWLY ADDED GLOBAL-LEVEL IDEAS

## 3.1 Dynamic Style Evolution Tracking

### Concept
Track how user style evolves over time, enabling:
- Seasonal adaptation
- Trend adoption patterns
- Style maturity progression
- Confidence growth visualization

### Implementation
```python
class StyleEvolutionEvent:
    user_id: UUID
    event_type: str  # preference_change, purchase, feedback, seasonal
    previous_value: dict
    new_value: dict
    trigger: str  # explicit, implicit, ai_suggested
    confidence_delta: float
    created_at: datetime
```

### Business Value
- Personalized "Your Style Journey" insights
- Predictive trend recommendations
- Churn prevention (detect style drift)
- Brand partnership insights

---

## 3.2 Behavior-Based Personalization Engine

### Concept
Implicit signals > explicit preferences. Track micro-behaviors:
- Dwell time on products
- Scroll patterns
- Filter usage
- Search queries
- Try-on attempts
- Share/save actions

### Signal Types
| Signal | Weight | Decay | Storage |
|--------|--------|-------|---------|
| Product View | 0.1 | 30 days | Event log |
| Wishlist Add | 0.3 | 90 days | Event log |
| Try-On Complete | 0.5 | 60 days | Event log |
| Purchase | 1.0 | Never | Permanent |
| Return | -0.5 | Never | Permanent |
| Share | 0.4 | 60 days | Event log |
| Negative Feedback | -0.3 | Never | Permanent |

### Implementation
```python
class BehaviorSignal:
    user_id: UUID
    signal_type: str
    entity_type: str  # product, brand, category, style
    entity_id: str
    weight: float
    context: dict  # occasion, price_range, etc.
    created_at: datetime
    expires_at: datetime  # for decay
```

---

## 3.3 Wardrobe Intelligence Signals

### Concept
Transform wardrobe from storage to intelligence:
- What they own → What they need
- What they wear → What they love
- What they ignore → What to sell/donate

### Intelligence Metrics
```python
class WardrobeIntelligence:
    user_id: UUID
    
    # Utilization
    total_items: int
    active_items: int  # worn in last 90 days
    dormant_items: int  # not worn in 180+ days
    utilization_rate: float  # active / total
    
    # Gap Analysis
    missing_categories: list[str]
    missing_occasions: list[str]
    style_gaps: list[dict]
    
    # Value
    total_wardrobe_value: float
    cost_per_wear_average: float
    investment_pieces: int
    
    # Versatility
    most_versatile_items: list[dict]
    orphan_items: list[dict]  # items with no outfit matches
```

---

## 3.4 Multi-Dimensional Confidence Scoring

### Concept
Replace single confidence_score with dimensional scoring:

```python
class ConfidenceProfile:
    user_id: UUID
    overall_confidence: float  # 0-100
    
    dimensions: dict[str, float] = {
        "style_identity": 0.0,      # Knows their style
        "fit_knowledge": 0.0,        # Knows their fit
        "brand_affinity": 0.0,       # Has brand preferences
        "occasion_readiness": 0.0,   # Ready for occasions
        "budget_management": 0.0,    # Budget awareness
        "wardrobe_utilization": 0.0, # Uses what they own
        "trend_adoption": 0.0,       # Adopts trends appropriately
        "sustainability": 0.0,       # Sustainable choices
    }
    
    # Growth tracking
    confidence_history: list[dict]  # [{date, score, delta}]
    
    # Badges earned through confidence
    earned_badges: list[str]
```

### Scoring Algorithm
```
overall_confidence = weighted_average(dimensions) + 
                     profile_completeness_bonus + 
                     engagement_bonus - 
                     inactivity_penalty
```

---

## 3.5 Contextual Fashion Preferences

### Concept
Style isn't static — it's contextual:

```python
class ContextualPreferences:
    user_id: UUID
    
    # Environmental
    climate_zone: str  # tropical, temperate, cold, etc.
    weather_preferences: dict  # temp ranges, layering
    
    # Cultural
    cultural_style_influences: list[str]
    regional_modesty_preferences: dict
    
    # Lifestyle
    work_dress_code: str  # formal, business_casual, casual, remote
    activity_levels: dict  # active, sedentary, mixed
    social_lifestyle: str  # introvert, extrovert, mixed
    
    # Temporal
    morning_style: str
    evening_style: str
    weekend_style: str
    
    # Social
    instagram_influenced: bool
    pinterest_connected: bool
    style_icons: list[str]
```

---

## 3.6 Adaptive Onboarding Flow

### Concept
Progressive, personality-driven onboarding:

```
┌─────────────────────────────────────────────────────────────┐
│                    ONBOARDING JOURNEY                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: QUICK START (30 seconds)                          │
│  ├── Name & Email (pre-filled from auth)                    │
│  ├── Gender Identity Selection                              │
│  └── "What brings you to CONFIT?" (goal selection)         │
│                                                              │
│  Phase 2: STYLE DISCOVERY (2-3 minutes)                     │
│  ├── Visual Style Quiz (pick outfits you love)             │
│  ├── Style Archetype Result (with confidence)              │
│  └── "How accurate is this?" (feedback loop)               │
│                                                              │
│  Phase 3: PRACTICAL PREFERENCES (1-2 minutes)               │
│  ├── Budget Slider                                          │
│  ├── Body Profile (optional, can skip)                      │
│  └── Brand Favorites (multi-select)                         │
│                                                              │
│  Phase 4: LIFESTYLE CONTEXT (1 minute)                       │
│  ├── Work Environment                                       │
│  ├── Climate/Weather                                        │
│  └── Primary Occasions                                      │
│                                                              │
│  Phase 5: FIRST OUTFIT (optional, 2 minutes)                │
│  ├── AI generates 3 outfit suggestions                      │
│  ├── User picks favorite                                    │
│  └── Confidence Score initialized                           │
│                                                              │
│  ── Continue Anytime ──                                      │
│  Profile Completeness: 40% → 60% → 80% → 95% → 100%        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Style Archetypes
```python
STYLE_ARCHETYPES = {
    "classic_chic": {
        "name": "Classic Chic",
        "description": "Timeless elegance, quality over quantity",
        "traits": ["minimalist", "sophisticated", "investment_pieces"],
        "colors": ["neutral", "navy", "black", "white"],
        "brands": ["Ralph Lauren", "Max Mara", "Brooks Brothers"],
    },
    "urban_edge": {
        "name": "Urban Edge",
        "description": "Street-smart style with attitude",
        "traits": ["trendy", "bold", "experimental"],
        "colors": ["black", "neon", "denim"],
        "brands": ["Off-White", "Supreme", "Nike"],
    },
    "bohemian_spirit": {
        "name": "Bohemian Spirit",
        "description": "Free-spirited, artistic, eclectic",
        "traits": ["artistic", "layered", "natural"],
        "colors": ["earth_tones", "jewel_tones", "prints"],
        "brands": ["Free People", "Anthropologie", "Spell"],
    },
    "modern_minimalist": {
        "name": "Modern Minimalist",
        "description": "Clean lines, neutral palette, curated",
        "traits": ["streamlined", "quality_focused", "versatile"],
        "colors": ["white", "beige", "grey", "black"],
        "brands": ["COS", "Arket", "Everlane"],
    },
    "romantic_feminine": {
        "name": "Romantic Feminine",
        "description": "Soft, graceful, detail-oriented",
        "traits": ["delicate", "floral", "elegant"],
        "colors": ["pastels", "blush", "cream", "florals"],
        "brands": ["Reformation", "Sézane", "Love Shack Fancy"],
    },
    "sport_luxe": {
        "name": "Sport Luxe",
        "description": "Athletic meets elevated",
        "traits": ["active", "comfortable", "performance"],
        "colors": ["black", "white", "neon_accents"],
        "brands": ["Lululemon", "Nike", "Adidas", "Varley"],
    },
    "avant_garde": {
        "name": "Avant-Garde",
        "description": "Bold, experimental, statement-making",
        "traits": ["artistic", "unconventional", "dramatic"],
        "colors": ["monochrome", "bold_contrasts", "unexpected"],
        "brands": ["Comme des Garçons", "Rick Owens", "Margiela"],
    },
    "preppy_polished": {
        "name": "Preppy Polished",
        "description": "Refined, traditional, put-together",
        "traits": ["classic", "structured", "polished"],
        "colors": ["navy", "white", "pastels", "patterns"],
        "brands": ["J.Crew", "Vineyard Vines", "Lacoste"],
    },
}
```

---

# 4. FINAL USP ARCHITECTURE

## User Style Profile (USP) v2.0

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     USER STYLE PROFILE (USP)                              │
│                     The Identity Engine for CONFIT                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    CORE IDENTITY                                     │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  user_id: UUID                                                       │ │
│  │  email: string                                                       │ │
│  │  name: string                                                        │ │
│  │  avatar_url: string                                                  │ │
│  │  created_at: timestamp                                               │ │
│  │  profile_version: int (schema versioning)                           │ │
│  │  profile_completeness: float (0-100)                                │ │
│  │  onboarding_completed: bool                                         │ │
│  │  onboarding_phase: int (1-5)                                        │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    STYLE IDENTITY                                    │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  primary_archetype: string                                          │ │
│  │  secondary_archetypes: list[string]                                 │ │
│  │  archetype_confidence: float                                        │ │
│  │                                                                      │ │
│  │  style_dimensions: {                                                │ │
│  │    classic: float,          # 0-1                                   │ │
│  │    trendy: float,                                                   │ │
│  │    minimalist: float,                                               │ │
│  │    maximalist: float,                                               │ │
│  │    feminine: float,                                                 │ │
│  │    masculine: float,                                                │ │
│  │    edgy: float,                                                     │ │
│  │    romantic: float,                                                 │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  color_palette: {                                                   │ │
│  │    skin_undertone: string,  # warm, cool, neutral                   │ │
│  │    preferred_colors: list[string],                                  │ │
│  │    avoided_colors: list[string],                                    │ │
│  │    color_confidence: float,                                         │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  pattern_preferences: {                                             │ │
│  │    solid: float,                                                    │ │
│  │    stripes: float,                                                  │ │
│  │    floral: float,                                                   │ │
│  │    geometric: float,                                                │ │
│  │    animal_print: float,                                             │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  fabric_preferences: list[string]                                   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    BODY PROFILE                                      │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  body_profile_status: string  # not_set, partial, complete          │ │
│  │                                                                      │ │
│  │  measurements: {                                                    │ │
│  │    height_cm: int,                                                  │ │
│  │    weight_kg: int,                                                  │ │
│  │    chest_cm: int,                                                   │ │
│  │    waist_cm: int,                                                   │ │
│  │    hips_cm: int,                                                    │ │
│  │    inseam_cm: int,                                                  │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  body_shape: string  # hourglass, pear, apple, rectangle, inverted  │ │
│  │  fit_preference: string  # tight, regular, relaxed, oversized       │ │
│  │                                                                      │ │
│  │  size_profile: {                                                    │ │
│  │    tops: string,           # XS, S, M, L, XL                        │ │
│  │    bottoms: string,                                                 │ │
│  │    dresses: string,                                                 │ │
│  │    shoes: string,                                                   │ │
│  │    brand_overrides: {brand_id: size},                               │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  fit_issues: list[string]  # "shoulders_tight", "length_too_short"  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    PRACTICAL PREFERENCES                             │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  budget: {                                                           │ │
│  │    per_item_min: float,                                             │ │
│  │    per_item_max: float,                                             │ │
│  │    monthly_max: float,                                              │ │
│  │    currency: string,                                                │ │
│  │    investment_pieces: bool,  # willing to splurge                   │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  brand_affinities: [                                                │ │
│  │    {brand_id: string, affinity: float, reason: string}              │ │
│  │  ]                                                                  │ │
│  │                                                                      │ │
│  │  brand_avoids: list[string]                                         │ │
│  │                                                                      │ │
│  │  sustainability_preferences: {                                     │ │
│  │    eco_friendly: bool,                                              │ │
│  │    sustainable_materials: bool,                                     │ │
│  │    ethical_production: bool,                                         │ │
│  │    secondhand_acceptable: bool,                                     │ │
│  │  }                                                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    CONTEXTUAL PREFERENCES                            │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  occasion_preferences: {                                            │ │
│  │    work: {frequency: string, formality: string},                    │ │
│  │    casual: {frequency: string, style: string},                      │ │
│  │    date_night: {frequency: string, style: string},                  │ │
│  │    formal_events: {frequency: string, style: string},               │ │
│  │    active: {frequency: string, style: string},                      │ │
│  │    travel: {frequency: string, style: string},                      │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  lifestyle_context: {                                               │ │
│  │    work_environment: string,  # office, hybrid, remote, field       │ │
│  │    climate_zone: string,                                            │ │
│  │    activity_level: string,  # sedentary, moderate, active           │ │
│  │    has_children: bool,                                              │ │
│  │    pet_friendly: bool,                                              │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  weather_preferences: {                                             │ │
│  │    hot: {fabrics: [], styles: []},                                  │ │
│  │    cold: {fabrics: [], styles: []},                                 │ │
│  │    rainy: {preferences: []},                                        │ │
│  │  }                                                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    CONFIDENCE PROFILE                                │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  overall_confidence: float  # 0-100                                 │ │
│  │                                                                      │ │
│  │  confidence_dimensions: {                                           │ │
│  │    style_identity: float,                                           │ │
│  │    fit_knowledge: float,                                            │ │
│  │    brand_affinity: float,                                           │ │
│  │    occasion_readiness: float,                                       │ │
│  │    budget_management: float,                                        │ │
│  │    wardrobe_utilization: float,                                     │ │
│  │    trend_adoption: float,                                           │ │
│  │    sustainability: float,                                           │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  confidence_badges: list[string]                                    │ │
│  │  confidence_growth_rate: float  # weekly change                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    BEHAVIORAL SIGNALS                                │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  implicit_preferences: {                                            │ │
│  │    most_viewed_categories: list[string],                            │ │
│  │    most_viewed_brands: list[string],                                │ │
│  │    most_viewed_styles: list[string],                                │ │
│  │    price_range_behavior: {min: float, max: float},                  │ │
│  │    color_engagement: dict[string, float],                           │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  engagement_metrics: {                                              │ │
│  │    try_on_count: int,                                               │ │
│  │    outfit_saves: int,                                               │ │
│  │    purchases: int,                                                  │ │
│  │    returns: int,                                                    │ │
│  │    shares: int,                                                     │ │
│  │    last_active: timestamp,                                          │ │
│  │    session_frequency: float,  # sessions per week                   │ │
│  │  }                                                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    WARDROBE INTELLIGENCE                             │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  wardrobe_summary: {                                                │ │
│  │    total_items: int,                                                │ │
│  │    total_value: float,                                              │ │
│  │    utilization_rate: float,                                         │ │
│  │    category_distribution: dict,                                     │ │
│  │    color_distribution: dict,                                        │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  wardrobe_gaps: list[string]  # missing essentials                  │ │
│  │  wardrobe_strengths: list[string]  # well-stocked categories        │ │
│  │                                                                      │ │
│  │  outfit_history: {                                                  │ │
│  │    total_outfits_created: int,                                      │ │
│  │    favorite_occasions: list[string],                                │ │
│  │    most_used_items: list[string],                                   │ │
│  │  }                                                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    PRIVACY & CONSENT                                 │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  consent_version: int                                               │ │
│  │  consents: {                                                        │ │
│  │    marketing_email: {granted: bool, timestamp: datetime},           │ │
│  │    marketing_sms: {granted: bool, timestamp: datetime},             │ │
│  │    data_sharing_partners: {granted: bool, timestamp: datetime},     │ │
│  │    ai_training: {granted: bool, timestamp: datetime},               │ │
│  │    personalization: {granted: bool, timestamp: datetime},           │ │
│  │    analytics: {granted: bool, timestamp: datetime},                 │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  data_retention: {                                                  │ │
│  │    preference: string,  # standard, minimal, aggressive             │ │
│  │    delete_after: datetime,  # if set                                │ │
│  │  }                                                                  │ │
│  │                                                                      │ │
│  │  privacy_settings: {                                                │ │
│  │    profile_visibility: string,  # private, friends, public          │ │
│  │    show_style_profile: bool,                                        │ │
│  │    show_wardrobe: bool,                                             │ │
│  │    allow_style_matching: bool,                                      │ │
│  │  }                                                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    AI SIGNALS (ML-Ready)                             │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  style_embedding: vector[128]  # dense embedding                    │ │
│  │  preference_vector: vector[64]  # sparse features                   │ │
│  │  behavior_vector: vector[32]  # recent behavior summary            │ │
│  │                                                                      │ │
│  │  last_embedding_update: timestamp                                   │ │
│  │  embedding_model_version: string                                    │ │
│  │                                                                      │ │
│  │  recommendation_context: {                                          │ │
│  │    recent_searches: list[string],                                   │ │
│  │    recent_views: list[string],                                      │ │
│  │    current_season: string,                                          │ │
│  │    trending_styles: list[string],                                   │ │
│  │  }                                                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    AUDIT & EVOLUTION                                 │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  profile_changes: list[{                                            │ │
│  │    field: string,                                                   │ │
│  │    old_value: any,                                                  │ │
│  │    new_value: any,                                                  │ │
│  │    source: string,  # explicit, implicit, ai_suggested              │ │
│  │    timestamp: datetime,                                             │ │
│  │  }]                                                                 │ │
│  │                                                                      │ │
│  │  style_evolution: list[{                                            │ │
│  │    date: datetime,                                                  │ │
│  │    archetype: string,                                               │ │
│  │    confidence: float,                                               │ │
│  │  }]                                                                 │ │
│  │                                                                      │ │
│  │  last_updated: timestamp                                            │ │
│  │  version: int                                                       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

# 5. BACKEND DESIGN

## 5.1 New Database Tables

### user_style_profiles
```sql
CREATE TABLE user_style_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Style Identity
    primary_archetype       VARCHAR(50),
    secondary_archetypes    JSONB DEFAULT '[]',
    archetype_confidence    DECIMAL(3,2) DEFAULT 0.0,
    style_dimensions        JSONB DEFAULT '{}',
    
    -- Color & Pattern
    skin_undertone          VARCHAR(20),
    preferred_colors        JSONB DEFAULT '[]',
    avoided_colors          JSONB DEFAULT '[]',
    pattern_preferences     JSONB DEFAULT '{}',
    fabric_preferences      JSONB DEFAULT '[]',
    
    -- Profile Status
    profile_completeness    DECIMAL(5,2) DEFAULT 0.0,
    onboarding_completed    BOOLEAN DEFAULT FALSE,
    onboarding_phase        INTEGER DEFAULT 0,
    profile_version         INTEGER DEFAULT 1,
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id)
);

CREATE INDEX idx_style_profiles_archetype ON user_style_profiles(primary_archetype);
CREATE INDEX idx_style_profiles_completeness ON user_style_profiles(profile_completeness);
```

### user_body_profiles
```sql
CREATE TABLE user_body_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Status
    profile_status      VARCHAR(20) DEFAULT 'not_set',  -- not_set, partial, complete
    
    -- Measurements (cm)
    height_cm           INTEGER,
    weight_kg           INTEGER,
    chest_cm            INTEGER,
    waist_cm            INTEGER,
    hips_cm             INTEGER,
    inseam_cm           INTEGER,
    
    -- Classification
    body_shape          VARCHAR(50),  -- hourglass, pear, apple, rectangle, inverted_triangle
    fit_preference      VARCHAR(30) DEFAULT 'regular',  -- tight, regular, relaxed, oversized
    
    -- Sizes
    size_tops           VARCHAR(10),
    size_bottoms        VARCHAR(10),
    size_dresses        VARCHAR(10),
    size_shoes          VARCHAR(10),
    
    -- Brand-specific overrides
    brand_size_overrides    JSONB DEFAULT '{}',
    
    -- Issues
    fit_issues          JSONB DEFAULT '[]',
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id)
);
```

### user_budget_profiles
```sql
CREATE TABLE user_budget_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    per_item_min        DECIMAL(10,2),
    per_item_max        DECIMAL(10,2),
    monthly_max         DECIMAL(10,2),
    currency            VARCHAR(3) DEFAULT 'USD',
    investment_pieces   BOOLEAN DEFAULT FALSE,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id)
);
```

### user_brand_affinities
```sql
CREATE TABLE user_brand_affinities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    brand_id        VARCHAR(64) NOT NULL REFERENCES brands(id),
    
    affinity        DECIMAL(3,2) DEFAULT 0.5,  -- 0.0 to 1.0
    affinity_source VARCHAR(30) DEFAULT 'explicit',  -- explicit, implicit, purchase
    reason          TEXT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, brand_id)
);

CREATE INDEX idx_brand_affinities_user ON user_brand_affinities(user_id);
CREATE INDEX idx_brand_affinities_brand ON user_brand_affinities(brand_id);
```

### user_contextual_preferences
```sql
CREATE TABLE user_contextual_preferences (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Occasion Preferences
    occasion_preferences    JSONB DEFAULT '{}',
    
    -- Lifestyle
    work_environment        VARCHAR(30),  -- office, hybrid, remote, field
    climate_zone            VARCHAR(30),
    activity_level          VARCHAR(20),  -- sedentary, moderate, active
    has_children            BOOLEAN,
    pet_friendly            BOOLEAN,
    
    -- Weather
    weather_preferences     JSONB DEFAULT '{}',
    
    -- Social
    style_icons             JSONB DEFAULT '[]',
    social_influences       JSONB DEFAULT '[]',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id)
);
```

### user_confidence_profiles
```sql
CREATE TABLE user_confidence_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    overall_confidence      DECIMAL(5,2) DEFAULT 0.0,
    
    -- Dimensions
    style_identity          DECIMAL(5,2) DEFAULT 0.0,
    fit_knowledge           DECIMAL(5,2) DEFAULT 0.0,
    brand_affinity          DECIMAL(5,2) DEFAULT 0.0,
    occasion_readiness      DECIMAL(5,2) DEFAULT 0.0,
    budget_management       DECIMAL(5,2) DEFAULT 0.0,
    wardrobe_utilization    DECIMAL(5,2) DEFAULT 0.0,
    trend_adoption          DECIMAL(5,2) DEFAULT 0.0,
    sustainability          DECIMAL(5,2) DEFAULT 0.0,
    
    -- Badges
    confidence_badges       JSONB DEFAULT '[]',
    
    -- Growth
    confidence_growth_rate  DECIMAL(5,4) DEFAULT 0.0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id)
);

CREATE INDEX idx_confidence_profiles_score ON user_confidence_profiles(overall_confidence DESC);
```

### user_confidence_history
```sql
CREATE TABLE user_confidence_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    overall_score   DECIMAL(5,2) NOT NULL,
    dimensions      JSONB NOT NULL,
    delta           DECIMAL(5,2),
    trigger         VARCHAR(50),  -- profile_update, purchase, feedback, etc.
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_confidence_history_user ON user_confidence_history(user_id, created_at DESC);
```

### user_behavior_signals
```sql
CREATE TABLE user_behavior_signals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    signal_type     VARCHAR(30) NOT NULL,  -- view, wishlist, try_on, purchase, return, share, feedback
    entity_type     VARCHAR(30) NOT NULL,  -- product, brand, category, style
    entity_id       VARCHAR(100) NOT NULL,
    
    weight          DECIMAL(4,3) NOT NULL,
    context         JSONB DEFAULT '{}',
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,  -- for signal decay
    
    -- Auto-expire old signals
    CHECK (expires_at IS NULL OR expires_at > created_at)
);

CREATE INDEX idx_behavior_signals_user ON user_behavior_signals(user_id, created_at DESC);
CREATE INDEX idx_behavior_signals_entity ON user_behavior_signals(entity_type, entity_id);
CREATE INDEX idx_behavior_signals_type ON user_behavior_signals(signal_type);
```

### user_style_evolution
```sql
CREATE TABLE user_style_evolution (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    event_type      VARCHAR(50) NOT NULL,  -- archetype_change, preference_shift, confidence_milestone
    previous_value  JSONB,
    new_value       JSONB NOT NULL,
    trigger         VARCHAR(30) NOT NULL,  -- explicit, implicit, ai_suggested, seasonal
    
    confidence_delta DECIMAL(5,2),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_style_evolution_user ON user_style_evolution(user_id, created_at DESC);
```

### user_consent_history
```sql
CREATE TABLE user_consent_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    consent_type    VARCHAR(50) NOT NULL,  -- marketing_email, data_sharing, ai_training, etc.
    granted         BOOLEAN NOT NULL,
    consent_version INTEGER NOT NULL,
    
    ip_address      INET,
    user_agent      TEXT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_consent_history_user ON user_consent_history(user_id, created_at DESC);
```

### user_ai_embeddings
```sql
CREATE TABLE user_ai_embeddings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Style embedding (128 dimensions)
    style_embedding         VECTOR(128),
    
    -- Preference vector (sparse, stored as JSON)
    preference_vector       JSONB DEFAULT '{}',
    
    -- Behavior summary vector
    behavior_vector         JSONB DEFAULT '{}',
    
    -- Metadata
    model_version           VARCHAR(50) NOT NULL,
    last_updated            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Note: Requires pgvector extension for VECTOR type
-- CREATE EXTENSION IF NOT EXISTS vector;
```

### user_profile_audit_log
```sql
CREATE TABLE user_profile_audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    field_name      VARCHAR(100) NOT NULL,
    old_value       JSONB,
    new_value       JSONB NOT NULL,
    change_source   VARCHAR(30) NOT NULL,  -- explicit, implicit, ai_suggested, system
    
    ip_address      INET,
    user_agent      TEXT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_profile_audit_user ON user_profile_audit_log(user_id, created_at DESC);
```

---

## 5.2 Backend API Endpoints

### Authentication & Registration (Enhanced)

```
POST   /api/auth/register                    # Existing (enhanced with USP creation)
POST   /api/auth/login                       # Existing
POST   /api/auth/logout                      # NEW: Invalidate token
POST   /api/auth/refresh                     # NEW: Refresh JWT
POST   /api/auth/oauth/{provider}            # NEW: OAuth (Google, Apple)
GET    /api/auth/me                          # Existing (enhanced response)
PATCH  /api/auth/me                          # Existing (enhanced)
DELETE /api/auth/me                          # NEW: Account deletion (GDPR)
GET    /api/auth/exists                      # Existing
```

### Onboarding Flow (NEW)

```
GET    /api/onboarding/status                # Get onboarding progress
POST   /api/onboarding/start                 # Begin onboarding
POST   /api/onboarding/phase/{phase}         # Complete a phase
POST   /api/onboarding/style-quiz            # Submit style quiz answers
GET    /api/onboarding/style-quiz/questions  # Get quiz questions
POST   /api/onboarding/skip                  # Skip onboarding
POST   /api/onboarding/complete              # Mark complete
```

### Style Profile (NEW)

```
GET    /api/profile/style                    # Get style profile
PATCH  /api/profile/style                    # Update style profile
POST   /api/profile/style/archetype          # Recalculate archetype
GET    /api/profile/style/dimensions         # Get style dimensions
PATCH  /api/profile/style/dimensions         # Update dimensions
POST   /api/profile/style/colors/analyze     # Analyze color preferences
GET    /api/profile/style/evolution          # Get style evolution history
```

### Body Profile (NEW)

```
GET    /api/profile/body                     # Get body profile
PATCH  /api/profile/body                     # Update body profile
POST   /api/profile/body/measurements        # Submit measurements
GET    /api/profile/body/size-recommendation  # Get size recommendations
POST   /api/profile/body/fit-feedback        # Submit fit feedback
```

### Budget Profile (NEW)

```
GET    /api/profile/budget                   # Get budget profile
PATCH  /api/profile/budget                   # Update budget profile
```

### Brand Affinities (NEW)

```
GET    /api/profile/brands                   # Get brand affinities
POST   /api/profile/brands                   # Add brand affinity
DELETE /api/profile/brands/{brand_id}        # Remove brand affinity
PATCH  /api/profile/brands/{brand_id}        # Update affinity score
```

### Contextual Preferences (NEW)

```
GET    /api/profile/context                  # Get contextual preferences
PATCH  /api/profile/context                  # Update contextual preferences
POST   /api/profile/context/occasions         # Add occasion preference
DELETE /api/profile/context/occasions/{id}   # Remove occasion preference
```

### Confidence Profile (NEW)

```
GET    /api/profile/confidence               # Get confidence profile
GET    /api/profile/confidence/history        # Get confidence history
POST   /api/profile/confidence/recalculate    # Trigger recalculation
GET    /api/profile/confidence/badges         # Get available & earned badges
```

### Behavior Signals (NEW)

```
POST   /api/signals/track                    # Track behavior signal
GET    /api/signals/summary                   # Get signal summary
DELETE /api/signals/clear                     # Clear all signals (privacy)
```

### Privacy & Consent (NEW)

```
GET    /api/privacy/consents                 # Get all consents
POST   /api/privacy/consents                 # Update consent
GET    /api/privacy/consents/history          # Get consent history
POST   /api/privacy/export                    # Request data export (GDPR)
GET    /api/privacy/export/{id}/status        # Check export status
GET    /api/privacy/export/{id}/download      # Download exported data
POST   /api/privacy/delete                    # Request account deletion
DELETE /api/privacy/delete/{id}/confirm      # Confirm deletion
GET    /api/privacy/settings                  # Get privacy settings
PATCH  /api/privacy/settings                  # Update privacy settings
```

### Profile Completeness (NEW)

```
GET    /api/profile/completeness              # Get completeness score & missing fields
GET    /api/profile/completeness/suggestions  # Get suggestions to improve
```

### AI Signals (NEW)

```
GET    /api/ai/embeddings                     # Get user embeddings (internal)
POST   /api/ai/embeddings/regenerate          # Regenerate embeddings
GET    /api/ai/recommendation-context          # Get recommendation context
```

---

## 5.3 API Request/Response Models

### Enhanced RegisterRequest

```python
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    
    # Optional initial profile
    gender_identity: Optional[str] = None
    goals: Optional[list[str]] = None  # ["build_wardrobe", "find_style", "save_money", "sustainable"]
    
    # OAuth info (if applicable)
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None
```

### StyleQuizSubmission

```python
class StyleQuizAnswer(BaseModel):
    question_id: str
    answer_type: str  # "image", "text", "multiple"
    selected_options: list[str]
    confidence: Optional[float] = None

class StyleQuizSubmission(BaseModel):
    answers: list[StyleQuizAnswer]
    skipped: bool = False
```

### StyleProfileResponse

```python
class StyleProfileResponse(BaseModel):
    user_id: str
    
    # Archetype
    primary_archetype: Optional[str]
    secondary_archetypes: list[str]
    archetype_confidence: float
    
    # Dimensions
    style_dimensions: dict[str, float]
    
    # Colors
    skin_undertone: Optional[str]
    preferred_colors: list[str]
    avoided_colors: list[str]
    
    # Patterns & Fabrics
    pattern_preferences: dict[str, float]
    fabric_preferences: list[str]
    
    # Status
    profile_completeness: float
    onboarding_completed: bool
    onboarding_phase: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### ConfidenceProfileResponse

```python
class ConfidenceProfileResponse(BaseModel):
    user_id: str
    overall_confidence: float
    
    dimensions: dict[str, float]
    confidence_badges: list[str]
    confidence_growth_rate: float
    
    # Percentile vs other users
    percentile: Optional[float]
    
    # Next milestone
    next_badge: Optional[dict]
    progress_to_next: float
```

### BehaviorSignalRequest

```python
class BehaviorSignalRequest(BaseModel):
    signal_type: str  # view, wishlist_add, try_on, purchase, return, share, feedback
    entity_type: str  # product, brand, category, style
    entity_id: str
    
    # Optional context
    context: Optional[dict] = None
    duration_ms: Optional[int] = None  # for view signals
    sentiment: Optional[str] = None  # for feedback signals
```

---

# 6. FRONTEND FLOW

## 6.1 Onboarding Flow Components

```
src/components/onboarding/
├── OnboardingFlow.tsx          # Main flow controller
├── phases/
│   ├── Phase1QuickStart.tsx    # Name, gender, goals
│   ├── Phase2StyleQuiz.tsx     # Visual style discovery
│   ├── Phase3Practical.tsx     # Budget, body, brands
│   ├── Phase4Lifestyle.tsx     # Work, climate, occasions
│   └── Phase5FirstOutfit.tsx   # AI-generated suggestions
├── components/
│   ├── StyleQuizQuestion.tsx   # Individual quiz question
│   ├── ImageGridSelector.tsx   # Visual preference selection
│   ├── BudgetSlider.tsx        # Interactive budget range
│   ├── BodyProfileForm.tsx     # Measurements form
│   ├── BrandMultiSelect.tsx    # Brand selection
│   ├── ArchetypeResult.tsx     # Style archetype display
│   ├── ProfileCompleteness.tsx # Progress indicator
│   └── SkipButton.tsx          # Continue later option
└── hooks/
    ├── useOnboarding.ts        # Onboarding state management
    └── useStyleQuiz.ts         # Quiz logic
```

## 6.2 Profile Management Components

```
src/components/profile/
├── ProfilePage.tsx             # Main profile page
├── sections/
│   ├── StyleIdentity.tsx       # Archetype & dimensions
│   ├── ColorPalette.tsx        # Color preferences
│   ├── BodyProfile.tsx         # Measurements & sizes
│   ├── BudgetSettings.tsx     # Budget configuration
│   ├── BrandAffinities.tsx     # Brand preferences
│   ├── OccasionPrefs.tsx       # Occasion settings
│   ├── LifestyleContext.tsx    # Work, climate, etc.
│   ├── ConfidenceScore.tsx     # Confidence dashboard
│   └── PrivacySettings.tsx     # Consent management
├── components/
│   ├── StyleDimensionRadar.tsx # Radar chart for dimensions
│   ├── ConfidenceMeter.tsx      # Animated confidence display
│   ├── ConfidenceBadges.tsx     # Badge collection
│   ├── StyleEvolutionChart.tsx # Evolution timeline
│   ├── ProfileEditModal.tsx     # Edit modal wrapper
│   └── ProfileCompletenessBar.tsx
└── hooks/
    ├── useProfile.ts           # Profile data fetching
    ├── useConfidence.ts        # Confidence calculations
    └── useBehaviorSignals.ts   # Signal tracking
```

## 6.3 User Journey Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER JOURNEY MAP                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  LANDING │───>│  REGISTER    │───>│  ONBOARDING  │───>│  DASHBOARD │ │
│  │  PAGE    │    │  (Email/Pwd) │    │  (5 phases)  │    │  (Home)    │ │
│  └──────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│        │                                     │                  │       │
│        │                                     ▼                  ▼       │
│        │                            ┌──────────────┐    ┌────────────┐  │
│        │                            │  SKIP FOR    │    │  PROFILE   │  │
│        │                            │  NOW (40%)   │    │  PAGE      │  │
│        │                            └──────────────┘    └────────────┘  │
│        │                                     │                  │       │
│        │                                     ▼                  ▼       │
│        ▼                            ┌──────────────┐    ┌────────────┐│
│  ┌──────────┐                       │  REMINDER    │    │  EDIT      ││
│  │  LOGIN   │                       │  BANNER      │    │  SECTIONS  ││
│  │  (Auth)  │                       │  "Complete   │    │  (Modal)   ││
│  └──────────┘                       │   profile"   │    └────────────┘│
│        │                             └──────────────┘           │      │
│        │                                     │                   │      │
│        ▼                                     ▼                   ▼      │
│  ┌──────────┐                       ┌──────────────┐    ┌────────────┐│
│  │  ME      │                       │  CONTINUE    │───>│  IMPROVED  ││
│  │  PAGE    │                       │  ONBOARDING  │    │  USP       ││
│  └──────────┘                       └──────────────┘    └────────────┘│
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 6.4 Profile Completeness Logic

```typescript
interface CompletenessField {
  field: string;
  weight: number;
  filled: boolean;
  category: string;
}

const COMPLETENESS_FIELDS: CompletenessField[] = [
  // Core (40%)
  { field: 'name', weight: 5, category: 'core' },
  { field: 'email', weight: 5, category: 'core' },
  { field: 'gender_identity', weight: 5, category: 'core' },
  { field: 'goals', weight: 5, category: 'core' },
  
  // Style Identity (25%)
  { field: 'primary_archetype', weight: 10, category: 'style' },
  { field: 'style_dimensions', weight: 10, category: 'style' },
  { field: 'preferred_colors', weight: 5, category: 'style' },
  
  // Practical (20%)
  { field: 'budget_range', weight: 10, category: 'practical' },
  { field: 'brand_affinities', weight: 5, category: 'practical' },
  { field: 'occasion_preferences', weight: 5, category: 'practical' },
  
  // Body (10% - optional but valuable)
  { field: 'body_measurements', weight: 5, category: 'body' },
  { field: 'size_profile', weight: 5, category: 'body' },
  
  // Context (5% - bonus)
  { field: 'lifestyle_context', weight: 5, category: 'context' },
];

function calculateCompleteness(profile: UserProfile): number {
  let score = 0;
  for (const field of COMPLETENESS_FIELDS) {
    if (isFieldFilled(profile, field.field)) {
      score += field.weight;
    }
  }
  return Math.min(100, score);
}
```

---

# 7. DATABASE MODEL

## 7.1 SQLAlchemy Models (Enhanced)

```python
# backend/database/models.py (additions)

class UserStyleProfile(Base):
    __tablename__ = "user_style_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Style Identity
    primary_archetype = Column(String(50), nullable=True)
    secondary_archetypes = Column(JSON, default=list)
    archetype_confidence = Column(Numeric(3, 2), default=0.0)
    style_dimensions = Column(JSON, default=dict)
    
    # Color & Pattern
    skin_undertone = Column(String(20), nullable=True)
    preferred_colors = Column(JSON, default=list)
    avoided_colors = Column(JSON, default=list)
    pattern_preferences = Column(JSON, default=dict)
    fabric_preferences = Column(JSON, default=list)
    
    # Profile Status
    profile_completeness = Column(Numeric(5, 2), default=0.0)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_phase = Column(Integer, default=0)
    profile_version = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="style_profile")


class UserBodyProfile(Base):
    __tablename__ = "user_body_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False)
    
    profile_status = Column(String(20), default="not_set")
    
    # Measurements
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Integer, nullable=True)
    chest_cm = Column(Integer, nullable=True)
    waist_cm = Column(Integer, nullable=True)
    hips_cm = Column(Integer, nullable=True)
    inseam_cm = Column(Integer, nullable=True)
    
    # Classification
    body_shape = Column(String(50), nullable=True)
    fit_preference = Column(String(30), default="regular")
    
    # Sizes
    size_tops = Column(String(10), nullable=True)
    size_bottoms = Column(String(10), nullable=True)
    size_dresses = Column(String(10), nullable=True)
    size_shoes = Column(String(10), nullable=True)
    brand_size_overrides = Column(JSON, default=dict)
    
    # Issues
    fit_issues = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="body_profile")


class UserBudgetProfile(Base):
    __tablename__ = "user_budget_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False)
    
    per_item_min = Column(Numeric(10, 2), nullable=True)
    per_item_max = Column(Numeric(10, 2), nullable=True)
    monthly_max = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="USD")
    investment_pieces = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="budget_profile")


class UserBrandAffinity(Base):
    __tablename__ = "user_brand_affinities"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    brand_id = Column(String(64), ForeignKey("brands.id"), nullable=False)
    
    affinity = Column(Numeric(3, 2), default=0.5)
    affinity_source = Column(String(30), default="explicit")
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="brand_affinities")
    brand = relationship("Brand")
    
    __table_args__ = (UniqueConstraint("user_id", "brand_id"),)


class UserContextualPreference(Base):
    __tablename__ = "user_contextual_preferences"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False)
    
    occasion_preferences = Column(JSON, default=dict)
    work_environment = Column(String(30), nullable=True)
    climate_zone = Column(String(30), nullable=True)
    activity_level = Column(String(20), nullable=True)
    has_children = Column(Boolean, nullable=True)
    pet_friendly = Column(Boolean, nullable=True)
    weather_preferences = Column(JSON, default=dict)
    style_icons = Column(JSON, default=list)
    social_influences = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="contextual_preferences")


class UserConfidenceProfile(Base):
    __tablename__ = "user_confidence_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False)
    
    overall_confidence = Column(Numeric(5, 2), default=0.0)
    
    # Dimensions
    style_identity = Column(Numeric(5, 2), default=0.0)
    fit_knowledge = Column(Numeric(5, 2), default=0.0)
    brand_affinity = Column(Numeric(5, 2), default=0.0)
    occasion_readiness = Column(Numeric(5, 2), default=0.0)
    budget_management = Column(Numeric(5, 2), default=0.0)
    wardrobe_utilization = Column(Numeric(5, 2), default=0.0)
    trend_adoption = Column(Numeric(5, 2), default=0.0)
    sustainability = Column(Numeric(5, 2), default=0.0)
    
    confidence_badges = Column(JSON, default=list)
    confidence_growth_rate = Column(Numeric(5, 4), default=0.0)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="confidence_profile")


class UserConfidenceHistory(Base):
    __tablename__ = "user_confidence_history"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    overall_score = Column(Numeric(5, 2), nullable=False)
    dimensions = Column(JSON, nullable=False)
    delta = Column(Numeric(5, 2), nullable=True)
    trigger = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="confidence_history")


class UserBehaviorSignal(Base):
    __tablename__ = "user_behavior_signals"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    signal_type = Column(String(30), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(String(100), nullable=False)
    
    weight = Column(Numeric(4, 3), nullable=False)
    context = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", backref="behavior_signals")


class UserStyleEvolution(Base):
    __tablename__ = "user_style_evolution"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    event_type = Column(String(50), nullable=False)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=False)
    trigger = Column(String(30), nullable=False)
    confidence_delta = Column(Numeric(5, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="style_evolution")


class UserConsentHistory(Base):
    __tablename__ = "user_consent_history"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    consent_type = Column(String(50), nullable=False)
    granted = Column(Boolean, nullable=False)
    consent_version = Column(Integer, nullable=False)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="consent_history")


class UserProfileAuditLog(Base):
    __tablename__ = "user_profile_audit_log"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    field_name = Column(String(100), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=False)
    change_source = Column(String(30), nullable=False)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="profile_audit_log")
```

---

# 8. AI SIGNALS GENERATED

## 8.1 Signal Categories

### Explicit Signals (User-Provided)
| Signal | Source | Weight | Persistence |
|--------|--------|--------|-------------|
| Style archetype selection | Onboarding | 1.0 | Permanent |
| Color preferences | Profile edit | 0.8 | Permanent |
| Brand favorites | Profile edit | 0.9 | Permanent |
| Budget range | Profile edit | 0.7 | Permanent |
| Occasion preferences | Profile edit | 0.6 | Permanent |
| Body measurements | Profile edit | 1.0 | Permanent |
| Fit feedback | Post-purchase | 0.8 | 2 years |

### Implicit Signals (Behavior-Tracked)
| Signal | Source | Weight | Decay |
|--------|--------|--------|-------|
| Product view (5s+) | Browse | 0.1 | 30 days |
| Product view (30s+) | Browse | 0.3 | 60 days |
| Wishlist add | Action | 0.5 | 90 days |
| Try-on complete | Action | 0.6 | 60 days |
| Try-on save | Action | 0.7 | 90 days |
| Outfit create | Action | 0.5 | Permanent |
| Outfit save | Action | 0.6 | Permanent |
| Purchase | Transaction | 1.0 | Permanent |
| Return | Transaction | -0.5 | Permanent |
| Share | Action | 0.4 | 60 days |
| Negative feedback | Action | -0.3 | Permanent |
| Search query | Browse | 0.2 | 7 days |

### Composite Signals (Derived)
| Signal | Calculation | Purpose |
|--------|-------------|---------|
| Style confidence | Weighted dimensions | Personalization strength |
| Brand affinity score | Explicit + implicit | Brand recommendations |
| Category preference | Views + purchases | Category ranking |
| Price sensitivity | Budget + behavior | Price filtering |
| Trend adoption rate | Recent vs classic | Trend recommendations |
| Sustainability score | Preferences + behavior | Eco recommendations |

## 8.2 Signal Collection Events

```python
# backend/services/signal_service.py

class SignalService:
    """Collects and processes user behavior signals."""
    
    SIGNAL_CONFIG = {
        "view": {"weight": 0.1, "decay_days": 30},
        "view_long": {"weight": 0.3, "decay_days": 60},
        "wishlist_add": {"weight": 0.5, "decay_days": 90},
        "try_on": {"weight": 0.6, "decay_days": 60},
        "try_on_save": {"weight": 0.7, "decay_days": 90},
        "outfit_create": {"weight": 0.5, "decay_days": None},
        "outfit_save": {"weight": 0.6, "decay_days": None},
        "purchase": {"weight": 1.0, "decay_days": None},
        "return": {"weight": -0.5, "decay_days": None},
        "share": {"weight": 0.4, "decay_days": 60},
        "negative_feedback": {"weight": -0.3, "decay_days": None},
        "search": {"weight": 0.2, "decay_days": 7},
    }
    
    def track_signal(
        self,
        user_id: str,
        signal_type: str,
        entity_type: str,
        entity_id: str,
        context: dict = None,
    ) -> None:
        """Track a behavior signal."""
        config = self.SIGNAL_CONFIG.get(signal_type)
        if not config:
            return
        
        expires_at = None
        if config["decay_days"]:
            expires_at = datetime.now(timezone.utc) + timedelta(days=config["decay_days"])
        
        signal = UserBehaviorSignal(
            user_id=user_id,
            signal_type=signal_type,
            entity_type=entity_type,
            entity_id=entity_id,
            weight=config["weight"],
            context=context or {},
            expires_at=expires_at,
        )
        
        self._db.add(signal)
        self._db.commit()
        
        # Trigger embedding update if significant
        if config["weight"] >= 0.5:
            self._schedule_embedding_update(user_id)
    
    def get_user_signals(
        self,
        user_id: str,
        entity_type: str = None,
        signal_types: list = None,
    ) -> list[dict]:
        """Get aggregated signals for a user."""
        query = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.expires_at == None,  # Non-expired
        )
        
        if entity_type:
            query = query.filter(UserBehaviorSignal.entity_type == entity_type)
        if signal_types:
            query = query.filter(UserBehaviorSignal.signal_type.in_(signal_types))
        
        return query.all()
    
    def aggregate_signals(self, user_id: str) -> dict:
        """Aggregate signals into preference summary."""
        signals = self.get_user_signals(user_id)
        
        aggregated = defaultdict(lambda: defaultdict(float))
        
        for signal in signals:
            aggregated[signal.entity_type][signal.entity_id] += signal.weight
        
        return dict(aggregated)
```

## 8.3 Embedding Generation

```python
# backend/services/embedding_service.py

class EmbeddingService:
    """Generates and manages user style embeddings."""
    
    MODEL_VERSION = "confit-style-v2.1"
    EMBEDDING_DIM = 128
    
    def generate_style_embedding(self, user_id: str) -> np.ndarray:
        """Generate style embedding from profile + signals."""
        profile = self._get_full_profile(user_id)
        signals = self._signal_service.aggregate_signals(user_id)
        
        # Feature extraction
        features = self._extract_features(profile, signals)
        
        # Generate embedding (placeholder - would use trained model)
        embedding = self._model.encode(features)
        
        return embedding
    
    def _extract_features(self, profile: dict, signals: dict) -> dict:
        """Extract ML-ready features from profile and signals."""
        return {
            # Style dimensions (8 features)
            "style_dimensions": profile.get("style_dimensions", {}),
            
            # Archetype one-hot (8 features)
            "archetype": self._one_hot_archetype(profile.get("primary_archetype")),
            
            # Color preferences (10 features)
            "color_preferences": self._encode_colors(profile.get("preferred_colors", [])),
            
            # Brand affinities (20 features - top brands)
            "brand_affinities": self._encode_brands(signals.get("brand", {})),
            
            # Category preferences (15 features)
            "category_preferences": self._encode_categories(signals.get("category", {})),
            
            # Budget normalized (2 features)
            "budget": self._normalize_budget(profile.get("budget", {})),
            
            # Occasion preferences (10 features)
            "occasions": self._encode_occasions(profile.get("occasion_preferences", {})),
            
            # Body profile (5 features)
            "body": self._encode_body(profile.get("body_profile", {})),
            
            # Confidence dimensions (8 features)
            "confidence": profile.get("confidence_dimensions", {}),
            
            # Temporal features (2 features)
            "temporal": {
                "season": self._current_season(),
                "trendiness": self._calculate_trendiness(signals),
            },
        }
    
    def update_user_embedding(self, user_id: str) -> None:
        """Update stored embedding for user."""
        embedding = self.generate_style_embedding(user_id)
        
        stored = self._db.query(UserAIEembedding).filter(
            UserAIEembedding.user_id == user_id
        ).first()
        
        if stored:
            stored.style_embedding = embedding.tolist()
            stored.model_version = self.MODEL_VERSION
            stored.last_updated = datetime.now(timezone.utc)
        else:
            stored = UserAIEembedding(
                user_id=user_id,
                style_embedding=embedding.tolist(),
                model_version=self.MODEL_VERSION,
            )
            self._db.add(stored)
        
        self._db.commit()
```

---

# 9. PRIVACY ENHANCEMENTS

## 9.1 GDPR Compliance Features

### Right to Access (Data Export)
```python
class PrivacyService:
    def export_user_data(self, user_id: str) -> dict:
        """Export all user data for GDPR compliance."""
        return {
            "profile": self._export_profile(user_id),
            "style_profile": self._export_style_profile(user_id),
            "body_profile": self._export_body_profile(user_id),
            "budget_profile": self._export_budget_profile(user_id),
            "brand_affinities": self._export_brand_affinities(user_id),
            "contextual_preferences": self._export_contextual(user_id),
            "confidence_profile": self._export_confidence(user_id),
            "behavior_signals": self._export_signals(user_id),
            "wardrobe": self._export_wardrobe(user_id),
            "outfits": self._export_outfits(user_id),
            "orders": self._export_orders(user_id),
            "digital_twins": self._export_digital_twins(user_id),
            "consent_history": self._export_consents(user_id),
            "audit_log": self._export_audit_log(user_id),
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "2.0",
                "jurisdiction": "GDPR",
            }
        }
```

### Right to Erasure
```python
class PrivacyService:
    def request_deletion(self, user_id: str, reason: str = None) -> str:
        """Request account deletion with 30-day grace period."""
        request = DeletionRequest(
            user_id=user_id,
            reason=reason,
            status="pending",
            scheduled_deletion_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self._db.add(request)
        self._db.commit()
        
        # Send confirmation email
        self._email_service.send_deletion_request(user_id)
        
        return request.id
    
    def confirm_deletion(self, request_id: str, confirmation_code: str) -> bool:
        """Confirm and execute deletion."""
        request = self._db.query(DeletionRequest).get(request_id)
        
        if not request or request.confirmation_code != confirmation_code:
            return False
        
        self._execute_deletion(request.user_id)
        request.status = "completed"
        self._db.commit()
        
        return True
    
    def _execute_deletion(self, user_id: str) -> None:
        """Execute complete data deletion."""
        # Anonymize instead of delete for referential integrity
        user = self._db.query(User).get(user_id)
        user.email = f"deleted_{user_id}@confit.anonymized"
        user.name = "Deleted User"
        user.password_hash = ""
        
        # Delete all related data
        self._db.query(UserStyleProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserBodyProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserBudgetProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserBrandAffinity).filter_by(user_id=user_id).delete()
        self._db.query(UserContextualPreference).filter_by(user_id=user_id).delete()
        self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserBehaviorSignal).filter_by(user_id=user_id).delete()
        self._db.query(UserStyleEvolution).filter_by(user_id=user_id).delete()
        self._db.query(UserConsentHistory).filter_by(user_id=user_id).delete()
        self._db.query(UserProfileAuditLog).filter_by(user_id=user_id).delete()
        
        # Keep anonymized order history for business analytics
        self._anonymize_orders(user_id)
```

### Consent Management
```python
CONSENT_TYPES = {
    "marketing_email": {
        "required": False,
        "default": False,
        "description": "Receive marketing emails about new styles and offers",
    },
    "marketing_sms": {
        "required": False,
        "default": False,
        "description": "Receive SMS notifications about sales and events",
    },
    "data_sharing_partners": {
        "required": False,
        "default": False,
        "description": "Share data with partner brands for personalized offers",
    },
    "ai_training": {
        "required": False,
        "default": False,
        "description": "Allow your data to improve our AI styling recommendations",
    },
    "personalization": {
        "required": False,
        "default": True,
        "description": "Enable personalized recommendations based on your style",
    },
    "analytics": {
        "required": False,
        "default": True,
        "description": "Help us improve by allowing anonymous usage analytics",
    },
    "third_party_integrations": {
        "required": False,
        "default": False,
        "description": "Connect with Instagram, Pinterest for style inspiration",
    },
}

class ConsentService:
    def update_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: str,
        user_agent: str,
    ) -> None:
        """Update consent with versioning."""
        current_version = self._get_current_consent_version()
        
        history = UserConsentHistory(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            consent_version=current_version,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self._db.add(history)
        self._db.commit()
        
        # Update user's current consent state
        self._update_user_consent_state(user_id, consent_type, granted)
```

## 9.2 Data Retention Policies

```python
DATA_RETENTION_POLICIES = {
    "behavior_signals": {
        "default": 365,  # days
        "minimal": 90,
        "aggressive": 30,
    },
    "style_evolution": {
        "default": 730,  # 2 years
        "minimal": 365,
        "aggressive": 180,
    },
    "audit_logs": {
        "default": 365,
        "minimal": 90,
        "aggressive": 30,
    },
    "digital_twins": {
        "default": 365,
        "minimal": 180,
        "aggressive": 90,
    },
    "try_on_sessions": {
        "default": 180,
        "minimal": 30,
        "aggressive": 7,
    },
}

class RetentionService:
    def apply_retention_policy(self, user_id: str, policy: str) -> None:
        """Apply data retention policy for user."""
        retention_days = DATA_RETENTION_POLICIES[policy]
        
        for data_type, days in retention_days.items():
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            self._purge_old_data(user_id, data_type, cutoff)
```

## 9.3 Privacy Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRIVACY DASHBOARD                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  YOUR DATA                                                          │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  ├─ Profile Data          [View] [Edit] [Export]                   │ │
│  │  ├─ Style Preferences     [View] [Edit] [Export]                   │ │
│  │  ├─ Body Measurements     [View] [Edit] [Export]                   │ │
│  │  ├─ Behavior History      [View] [Clear] [Export]                  │ │
│  │  ├─ Wardrobe Data         [View] [Export]                          │ │
│  │  └─ Order History         [View] [Export]                          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  CONSENTS                                                           │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  ☑ Personalization (On)     [Toggle]                              │ │
│  │  ☐ Marketing Emails (Off)   [Toggle]                              │ │
│  │  ☐ Marketing SMS (Off)       [Toggle]                              │ │
│  │  ☐ Partner Data Sharing (Off) [Toggle]                            │ │
│  │  ☑ Analytics (On)           [Toggle]                              │ │
│  │  ☐ AI Training (Off)         [Toggle]                              │ │
│  │                                                                     │ │
│  │  [View Consent History]                                             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  DATA RETENTION                                                     │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  Current Policy: Standard (1 year)                                 │ │
│  │                                                                     │ │
│  │  ○ Standard - Keep data for 1 year                                │ │
│  │  ○ Minimal - Keep data for 90 days                                │ │
│  │  ○ Aggressive - Keep data for 30 days                             │ │
│  │                                                                     │ │
│  │  [Apply Changes]                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ACCOUNT ACTIONS                                                    │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  [Export All My Data]  (GDPR Right to Access)                      │ │
│  │  [Delete My Account]   (GDPR Right to Erasure)                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 10. FINAL PRODUCTION-READY VERSION OF GROUP 1

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create new database tables (migrations)
- [ ] Implement SQLAlchemy models
- [ ] Create profile service layer
- [ ] Enhance auth service with profile creation

### Phase 2: Onboarding (Weeks 3-4)
- [ ] Build onboarding flow components
- [ ] Implement style quiz
- [ ] Create archetype calculation
- [ ] Add profile completeness tracking

### Phase 3: Profile Management (Weeks 5-6)
- [ ] Build profile page sections
- [ ] Implement edit modals
- [ ] Add confidence scoring
- [ ] Create evolution tracking

### Phase 4: Behavioral Intelligence (Weeks 7-8)
- [ ] Implement signal collection
- [ ] Build aggregation service
- [ ] Create embedding generation
- [ ] Add decay management

### Phase 5: Privacy & Compliance (Weeks 9-10)
- [ ] Implement data export
- [ ] Add deletion workflow
- [ ] Create consent management
- [ ] Build privacy dashboard

### Phase 6: AI Integration (Weeks 11-12)
- [ ] Connect signals to recommendation engine
- [ ] Implement embedding updates
- [ ] Add A/B testing infrastructure
- [ ] Create analytics events

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Profile Completeness | 35% | 75% | Average score |
| Onboarding Completion | 20% | 80% | Funnel analysis |
| Style Quiz Accuracy | N/A | 85% | User feedback |
| Confidence Score Growth | N/A | +5/week | Average delta |
| Signal Collection Rate | 0 | 50/day/user | Event count |
| GDPR Compliance | 50% | 100% | Audit score |
| AI Recommendation CTR | 2% | 8% | Click tracking |

---

## Final Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONFIT USER IDENTITY SYSTEM                          │
│                              GROUP 1 - COMPLETE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐            │
│  │   FRONTEND     │    │   BACKEND      │    │   DATABASE     │            │
│  ├────────────────┤    ├────────────────┤    ├────────────────┤            │
│  │                │    │                │    │                │            │
│  │  Onboarding    │───>│  Auth Service  │───>│  users         │            │
│  │  Flow          │    │                │    │                │            │
│  │                │    │  Profile Svc   │───>│  user_style_   │            │
│  │  Profile       │───>│                │    │  profiles     │            │
│  │  Pages         │    │  Signal Svc    │───>│  user_body_    │            │
│  │                │    │                │    │  profiles     │            │
│  │  Privacy       │───>│  Embedding Svc │───>│  user_budget_  │            │
│  │  Dashboard     │    │                │    │  profiles     │            │
│  │                │    │  Privacy Svc   │───>│  user_brand_   │            │
│  │  Confidence    │───>│                │    │  affinities   │            │
│  │  Dashboard     │    │  Confidence Svc│───>│  user_context_ │            │
│  │                │    │                │    │  preferences  │            │
│  └────────────────┘    └────────────────┘    │  user_confidence│            │
│           │                    │            │  _profiles    │            │
│           │                    │            │  user_behavior │            │
│           │                    │            │  _signals     │            │
│           │                    │            │  user_style_   │            │
│           │                    │            │  evolution    │            │
│           │                    │            │  user_consent_ │            │
│           │                    │            │  history      │            │
│           │                    │            │  user_ai_      │            │
│           │                    │            │  embeddings   │            │
│           │                    │            └────────────────┘            │
│           │                    │                    │                     │
│           │                    ▼                    │                     │
│           │            ┌────────────────┐          │                     │
│           │            │   AI SIGNALS   │          │                     │
│           │            ├────────────────┤          │                     │
│           │            │                │          │                     │
│           └───────────>│ Style Embed    │<─────────┘                     │
│                        │ Preference Vec │                                │
│                        │ Behavior Vec   │                                │
│                        │                │                                │
│                        │    OUTPUT TO:  │                                │
│                        │ ├─ AI Stylist  │                                │
│                        │ ├─ Virtual Try │                                │
│                        │ ├─ Outfit Rec  │                                │
│                        │ ├─ Budget Intel│                                │
│                        │ └─ Cross-Brand │                                │
│                        └────────────────┘                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

This audit transforms GROUP 1 from a **42% complete** basic user system to a **95%+ production-ready** identity engine capable of:

1. **Deep User Understanding**
   - 8 style archetypes with dimensional scoring
   - Multi-dimensional confidence tracking
   - Behavioral signal collection

2. **Adaptive Personalization**
   - Progressive onboarding with style quiz
   - Implicit preference learning
   - Contextual preference support

3. **AI-Ready Infrastructure**
   - Feature vector storage
   - Embedding generation pipeline
   - Signal decay management

4. **Privacy Compliance**
   - GDPR data export
   - Right to erasure
   - Consent versioning

5. **Scalable Architecture**
   - Versioned profile schema
   - Audit trail for all changes
   - Embedding model versioning

The system now provides the foundation for all downstream AI modules without requiring redesign, supporting CONFIT's vision of "Understand the user once, personalize forever."

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Author:** CONFIT Architecture Team
