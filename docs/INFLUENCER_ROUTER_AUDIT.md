# Influencer Router Usage Audit (Finding A.12)

**Date:** 2026-04-25  
**Phase:** E — Cleanup  
**File:** `backend/routers/influencer.py`

## Summary

The Influencer Marketplace router exposes **25 routes**. Only **7 routes** are actively consumed by the frontend. The remaining **18 routes** are creator-dashboard endpoints with no matching frontend pages.

## Route Usage Mapping

### Public Marketplace — Used by Frontend

| # | Method | Route | Frontend Consumer | Status |
|---|--------|-------|-------------------|--------|
| 1 | `GET` | `/api/influencers` | `InfluencerMarketplace.tsx` (list + search) | Active |
| 2 | `GET` | `/api/influencers/discover` | `InfluencerMarketplace.tsx` | Active |
| 3 | `GET` | `/api/influencers/feed/outfits` | `InfluencerMarketplace.tsx` | Active |
| 4 | `GET` | `/api/influencers/{id}` | Public profile view | Active |
| 5 | `GET` | `/api/influencers/{id}/storefront` | `InfluencerStorefront.tsx` | Active |
| 6 | `POST` | `/api/influencers/follow` | `InfluencerStorefront.tsx` | Active |
| 7 | `DELETE` | `/api/influencers/follow/{id}` | `InfluencerStorefront.tsx` | Active |

### Creator Dashboard — No Frontend Pages (Hidden from Public Schema)

| # | Method | Route | Purpose | Action |
|---|--------|-------|---------|--------|
| 8 | `POST` | `/api/influencers/profile` | Create creator profile | `include_in_schema=False` |
| 9 | `GET` | `/api/influencers/profile` | Get my creator profile | `include_in_schema=False` |
| 10 | `PATCH` | `/api/influencers/profile` | Update creator profile | `include_in_schema=False` |
| 11 | `POST` | `/api/influencers/outfits` | Create outfit | `include_in_schema=False` |
| 12 | `POST` | `/api/influencers/outfits/{id}/publish` | Publish outfit | `include_in_schema=False` |
| 13 | `GET` | `/api/influencers/outfits` | List my outfits | `include_in_schema=False` |
| 14 | `GET` | `/api/influencers/outfits/{id}` | Get outfit detail | `include_in_schema=False` |
| 15 | `PATCH` | `/api/influencers/outfits/{id}` | Update outfit | `include_in_schema=False` |
| 16 | `DELETE` | `/api/influencers/outfits/{id}` | Delete outfit | `include_in_schema=False` |
| 17 | `GET` | `/api/influencers/featured` | Featured influencers | `include_in_schema=False` |
| 18 | `POST` | `/api/influencers/outfits/{id}/like` | Like outfit | `include_in_schema=False` |
| 19 | `POST` | `/api/influencers/outfits/{id}/save` | Save outfit | `include_in_schema=False` |
| 20 | `POST` | `/api/influencers/affiliate-links` | Create affiliate link | `include_in_schema=False` |
| 21 | `GET` | `/api/influencers/affiliate-links` | List affiliate links | `include_in_schema=False` |
| 22 | `POST` | `/api/influencers/track-click` | Track click | `include_in_schema=False` |
| 23 | `GET` | `/api/influencers/commissions` | Commission summary | `include_in_schema=False` |
| 24 | `POST` | `/api/influencers/recommendations` | Create recommendation | `include_in_schema=False` |
| 25 | `GET` | `/api/influencers/{id}/recommendations` | Get recommendations | `include_in_schema=False` |

## Recommended Next Steps

1. **Creator Dashboard Frontend**: Build `/creator` routes to expose these endpoints (E.4 follow-up).
2. **Split Router**: Consider splitting into `influencer_public.py` + `influencer_creator.py` for cleaner separation.
3. **Re-enable Schema**: When creator dashboard pages are built, remove `include_in_schema=False` from the corresponding routes.

---
*Last updated: Phase E Cleanup (2026-04-25)*
