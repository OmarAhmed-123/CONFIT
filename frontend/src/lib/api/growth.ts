/**
 * CONFIT Autonomous Growth Engine — API client
 */

import { apiFetch } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';

export interface ViralFeedPost {
  id: string;
  outfit_image_url: string;
  try_on_preview_url?: string | null;
  style_tags: string[];
  caption?: string | null;
  creator: {
    user_id: string;
    display_name: string;
    avatar_url?: string | null;
    is_influencer?: boolean;
    influencer_id?: string | null;
  };
  shop_product_id?: string | null;
  shop_url?: string | null;
  rank_score: number;
  engagement_probability: number;
  style_similarity: number;
  trend_momentum: number;
  created_at: string;
}

export interface ViralFeedResponse {
  posts: ViralFeedPost[];
  next_offset: number;
  has_more: boolean;
  personalization?: string;
}

export async function fetchViralFeed(offset = 0, limit = 12): Promise<ViralFeedResponse> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  const res = await apiFetch(`/api/growth/feed?${params}`, { token: getAuthToken() });
  if (!res.ok) throw new Error('Failed to load growth feed');
  return res.json();
}

export async function shareOutfit(outfitId?: string | null, postId?: string | null) {
  const res = await apiFetch('/api/growth/share', {
    method: 'POST',
    token: getAuthToken(),
    body: JSON.stringify({ outfit_id: outfitId ?? null, post_id: postId ?? null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? 'Share failed');
  }
  return res.json() as Promise<{ share_url: string; referral_code: string; rate_limit_remaining: number }>;
}

export async function fetchGrowthCreators(limit = 8) {
  const res = await apiFetch(`/api/growth/creators?limit=${limit}`, { token: getAuthToken() });
  if (!res.ok) throw new Error('Failed to load creators');
  return res.json() as Promise<{ creators: Array<Record<string, unknown>> }>;
}

export async function fetchGrowthAnalytics() {
  const res = await apiFetch('/api/growth/analytics', { token: getAuthToken() });
  if (!res.ok) throw new Error('Failed to load analytics');
  return res.json();
}

export async function fetchGrowthPredict() {
  const res = await apiFetch('/api/growth/predict', { token: getAuthToken() });
  if (!res.ok) throw new Error('Failed to load predictions');
  return res.json();
}
