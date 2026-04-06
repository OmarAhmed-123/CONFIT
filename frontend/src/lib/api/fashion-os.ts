/**
 * CONFIT Fashion OS — intelligence API (identity layer)
 */

import { api } from '@/lib/api/client';

export interface IdentityDNA {
  elegance_score: number;
  minimalism_score: number;
  boldness_score: number;
  color_affinity: Record<string, number>;
  fit_preference: string;
  budget_behavior: Record<string, number>;
  seasonal_patterns: Record<string, number>;
}

export async function fashionOsDailyOutfit() {
  return api.get<{
    date: string;
    season: string;
    season_weight: number;
    today_outfit: Record<string, unknown> | null;
    identity_dna: IdentityDNA;
  }>('/fashion-os/daily-outfit');
}

export async function fashionOsRecommend(limit = 12) {
  return api.post<{
    items: Array<{
      id: string;
      name: string;
      category: string;
      color: string | null;
      price: number;
      image_url: string | null;
      score: number;
      score_breakdown: Record<string, number>;
    }>;
    latency_ms: number;
    identity_dna: IdentityDNA;
  }>('/fashion-os/style/recommend', { limit });
}

export async function fashionOsClosetInsights() {
  return api.get<{
    overused_items: Array<{ id: string; name: string; wear_count_proxy: number }>;
    unused_items: Array<{ id: string; name: string; category: string }>;
    missing_essentials: string[];
    sustainability_note: string;
  }>('/fashion-os/closet/insights');
}

export async function fashionOsStylistChat(body: {
  message: string;
  conversationHistory?: Array<{ role: string; content: string }>;
  occasion?: string;
  budget?: string;
  stylePreference?: string;
}) {
  return api.post<{
    content: string;
    outfitSuggestions?: Array<{
      id: string;
      name: string;
      price: number;
      styleScore: number;
      image: string;
    }>;
    detectedOccasion?: string;
  }>('/fashion-os/stylist/chat', body);
}

export async function fashionOsBehaviorLog(payload: Record<string, unknown>) {
  return api.post<{ ok: boolean; interest_score?: number | null }>('/fashion-os/behavior/log', payload);
}
