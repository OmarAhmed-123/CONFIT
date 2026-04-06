/**
 * CONFIT — Wardrobe Analytics Service
 * GROUP 4: Personal Wardrobe & Smart Reuse
 * Frontend integration for wardrobe analytics and personalization.
 */

import { apiUrl, apiFetch } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';

// ═══════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════

export interface WearLogEntry {
  item_id: string;
  worn_at?: string;
  occasion?: string;
  outfit_id?: string;
  notes?: string;
}

export interface OutfitHistoryEntry {
  id: string;
  user_id: string;
  outfit_name?: string;
  item_ids: string[];
  item_details?: Array<{
    id: string;
    name: string;
    category: string;
    color: string;
    image_url: string;
  }>;
  occasion?: string;
  weather?: string;
  season?: string;
  worn_at: string;
  is_favorite: boolean;
  user_rating?: number;
  style_score?: number;
  created_at: string;
}

export interface WardrobeAnalytics {
  overview: {
    total_items: number;
    active_items: number;
    unused_items: number;
    total_wears: number;
  };
  wear_frequency: {
    avg_wears: number;
    total_wears: number;
    items_tracked: number;
    most_worn_item_id?: string;
    most_worn_count: number;
    least_worn_count: number;
  };
  color_distribution: Array<{
    color: string;
    count: number;
    percentage: number;
    harmony_group: string;
    is_dominant: boolean;
  }>;
  category_distribution: Array<{
    category: string;
    count: number;
    percentage: number;
    avg_wears: number;
    is_gap: boolean;
    gap_severity?: string;
  }>;
  seasonal_rotation: {
    current_season: string;
    active_items_count: number;
    stored_items_count: number;
    items_to_activate: Array<{
      id: string;
      name: string;
      category: string;
      color: string;
      image_url: string;
    }>;
    items_to_store: Array<{
      id: string;
      name: string;
      category: string;
      color: string;
      image_url: string;
    }>;
    weather_recommendations: Record<string, any>;
  };
  recent_outfits: OutfitHistoryEntry[];
  confidence: {
    overall: number;
    dimensions: {
      variety: number;
      versatility: number;
      utilization: number;
      cohesion: number;
    };
    improvements: string[];
  };
  sustainability: {
    score: number;
    co2_saved_kg: number;
    money_saved: number;
  };
  declutter_candidates: number;
}

export interface SustainabilityInsights {
  sustainability_score: number;
  wardrobe_utilization_score: number;
  total_co2_saved_kg: number;
  total_water_saved_l: number;
  purchases_prevented: number;
  money_saved: number;
  active_items: number;
  unused_items: number;
  sustainability_tips: string[];
}

export interface WardrobeConfidence {
  overall_confidence: number;
  dimensions: {
    variety: number;
    versatility: number;
    utilization: number;
    cohesion: number;
    seasonality: number;
    quality: number;
  };
  outfit_readiness: number;
  occasion_coverage: Record<string, number>;
  top_improvements: string[];
  quick_wins: string[];
}

export interface CapsuleWardrobe {
  id: string;
  name?: string;
  type: string;
  item_count: number;
  cohesion_score: number;
  versatility_score: number;
  outfit_combinations: number;
  dominant_colors: string[];
  is_ai_suggested: boolean;
}

export interface DeclutterSuggestion {
  id: string;
  item_id: string;
  item_name?: string;
  item_image?: string;
  suggestion_type: string;
  confidence: number;
  reason: string;
  estimated_resale_value?: number;
  days_since_last_wear?: number;
  wear_count: number;
  status: string;
}

export interface PurchaseAvoidanceResult {
  avoided: boolean;
  matched_item_id?: string;
  matched_item_name?: string;
  matched_item_image?: string;
  similarity: number;
  money_saved?: number;
  suggestion: string;
}

export interface UnusedItem {
  id: string;
  name: string;
  category: string;
  color: string;
  image_url: string;
  brand?: string;
  price?: number;
  wear_count: number;
  days_since_worn?: number;
  status: 'never_worn' | 'unused' | 'low_usage';
  alert_level: 'high' | 'medium' | 'low';
}

export interface OwnershipSignals {
  total_items: number;
  categories: Record<string, number>;
  top_brands: Record<string, number>;
  color_distribution: Record<string, number>;
  ownership_strength: number;
}

export interface ReusePatterns {
  total_wears: number;
  average_wears_per_item: number;
  most_worn_items: Array<{
    item_id: string;
    wear_count: number;
    occasions?: Record<string, number>;
  }>;
  reuse_rate: number;
}

export interface StyleSignals {
  dominant_colors: Array<{
    color: string;
    count: number;
    percentage: number;
    harmony_group: string;
    is_dominant: boolean;
  }>;
  color_harmony_groups: string[];
  category_distribution: Array<{
    category: string;
    count: number;
    percentage: number;
    avg_wears: number;
    is_gap: boolean;
    gap_severity?: string;
  }>;
  wardrobe_gaps: Array<{
    category: string;
    count: number;
    percentage: number;
    avg_wears: number;
    is_gap: boolean;
    gap_severity?: string;
  }>;
  style_balance_score: number;
}

// ═══════════════════════════════════════════════════════════════════
// Service Functions
// ═══════════════════════════════════════════════════════════════════

/**
 * Log a wear event for a wardrobe item
 */
export async function logWear(entry: WearLogEntry): Promise<{ status: string; data: any }> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/wear/log', {
    method: 'POST',
    token,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  });

  if (!res.ok) throw new Error('Failed to log wear');
  return res.json();
}

/**
 * Get wear frequency statistics
 */
export async function getWearStats(): Promise<{
  avg_wears: number;
  total_wears: number;
  items_tracked: number;
  most_worn_item_id?: string;
  most_worn_count: number;
  least_worn_count: number;
}> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/wear/stats', { token });

  if (!res.ok) throw new Error('Failed to get wear stats');
  return res.json();
}

/**
 * Get seasonal rotation status
 */
export async function getSeasonalRotation(): Promise<{
  current_season: string;
  active_items_count: number;
  stored_items_count: number;
  items_to_activate: any[];
  items_to_store: any[];
  weather_recommendations: Record<string, any>;
}> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/seasonal', { token });

  if (!res.ok) throw new Error('Failed to get seasonal rotation');
  return res.json();
}

/**
 * Set seasonal classification for an item
 */
export async function setItemSeason(data: {
  item_id: string;
  primary_season: string;
  secondary_seasons?: string[];
  temp_range?: { min?: number; max?: number };
}): Promise<{ status: string; item_id: string; season: string }> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/seasonal/set', {
    method: 'POST',
    token,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error('Failed to set item season');
  return res.json();
}

/**
 * Log an outfit worn
 */
export async function logOutfit(data: {
  item_ids: string[];
  outfit_name?: string;
  occasion?: string;
  weather?: string;
  temperature_c?: number;
  is_favorite?: boolean;
  ai_generated?: boolean;
}): Promise<{ status: string; outfit_id: string; item_count: number }> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/outfits/log', {
    method: 'POST',
    token,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error('Failed to log outfit');
  return res.json();
}

/**
 * Get outfit history
 */
export async function getOutfitHistory(options?: {
  limit?: number;
  occasion?: string;
  season?: string;
}): Promise<OutfitHistoryEntry[]> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const params = new URLSearchParams();
  if (options?.limit) params.append('limit', String(options.limit));
  if (options?.occasion) params.append('occasion', options.occasion);
  if (options?.season) params.append('season', options.season);

  const res = await apiFetch(`/api/wardrobe/analytics/outfits/history?${params}`, { token });

  if (!res.ok) throw new Error('Failed to get outfit history');
  return res.json();
}

/**
 * Rate an outfit
 */
export async function rateOutfit(outfitId: string, rating: number, notes?: string): Promise<{ status: string; rating: number }> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/outfits/rate', {
    method: 'POST',
    token,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ outfit_id: outfitId, rating, notes }),
  });

  if (!res.ok) throw new Error('Failed to rate outfit');
  return res.json();
}

/**
 * Toggle outfit favorite status
 */
export async function toggleOutfitFavorite(outfitId: string): Promise<{ status: string; is_favorite: boolean }> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch(`/api/wardrobe/analytics/outfits/${outfitId}/favorite`, {
    method: 'POST',
    token,
  });

  if (!res.ok) throw new Error('Failed to toggle favorite');
  return res.json();
}

/**
 * Get unused items
 */
export async function getUnusedItems(): Promise<UnusedItem[]> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/unused', { token });

  if (!res.ok) throw new Error('Failed to get unused items');
  return res.json();
}

/**
 * Get sustainability insights
 */
export async function getSustainabilityInsights(): Promise<SustainabilityInsights> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/sustainability', { token });

  if (!res.ok) throw new Error('Failed to get sustainability insights');
  return res.json();
}

/**
 * Recalculate sustainability metrics
 */
export async function recalculateSustainability(): Promise<{
  status: string;
  sustainability_score: number;
  utilization_score: number;
}> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/sustainability/recalculate', {
    method: 'POST',
    token,
  });

  if (!res.ok) throw new Error('Failed to recalculate sustainability');
  return res.json();
}

/**
 * Analyze color distribution
 */
export async function analyzeColors(): Promise<Array<{
  color: string;
  count: number;
  percentage: number;
  harmony_group: string;
  is_dominant: boolean;
}>> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/colors', { token });

  if (!res.ok) throw new Error('Failed to analyze colors');
  return res.json();
}

/**
 * Analyze category distribution
 */
export async function analyzeCategories(): Promise<Array<{
  category: string;
  count: number;
  percentage: number;
  avg_wears: number;
  is_gap: boolean;
  gap_severity?: string;
}>> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/categories', { token });

  if (!res.ok) throw new Error('Failed to analyze categories');
  return res.json();
}

/**
 * Get wardrobe confidence score
 */
export async function getWardrobeConfidence(): Promise<WardrobeConfidence> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/confidence', { token });

  if (!res.ok) throw new Error('Failed to get wardrobe confidence');
  return res.json();
}

/**
 * Get capsule wardrobes
 */
export async function getCapsuleWardrobes(): Promise<CapsuleWardrobe[]> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/capsules', { token });

  if (!res.ok) throw new Error('Failed to get capsule wardrobes');
  return res.json();
}

/**
 * Get declutter suggestions
 */
export async function getDeclutterSuggestions(): Promise<DeclutterSuggestion[]> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/declutter', { token });

  if (!res.ok) throw new Error('Failed to get declutter suggestions');
  return res.json();
}

/**
 * Dismiss a declutter suggestion
 */
export async function dismissDeclutterSuggestion(suggestionId: string): Promise<{ status: string }> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch(`/api/wardrobe/analytics/declutter/${suggestionId}/dismiss`, {
    method: 'POST',
    token,
  });

  if (!res.ok) throw new Error('Failed to dismiss suggestion');
  return res.json();
}

/**
 * Act on a declutter suggestion
 */
export async function actOnDeclutterSuggestion(
  suggestionId: string,
  action: 'resold' | 'donated' | 'recycled'
): Promise<{ status: string; action: string }> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch(`/api/wardrobe/analytics/declutter/${suggestionId}/act?action=${action}`, {
    method: 'POST',
    token,
  });

  if (!res.ok) throw new Error('Failed to act on suggestion');
  return res.json();
}

/**
 * Check purchase avoidance (duplicate check)
 */
export async function checkPurchaseAvoidance(data: {
  product_name: string;
  product_category: string;
  product_color: string;
  product_price?: number;
}): Promise<PurchaseAvoidanceResult> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/purchase-check', {
    method: 'POST',
    token,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error('Failed to check purchase avoidance');
  return res.json();
}

/**
 * Get full analytics dashboard
 */
export async function getFullAnalytics(): Promise<WardrobeAnalytics> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/dashboard', { token });

  if (!res.ok) throw new Error('Failed to get analytics dashboard');
  return res.json();
}

/**
 * Get ownership signals for AI Brain
 */
export async function getOwnershipSignals(): Promise<OwnershipSignals> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/ownership-signals', { token });

  if (!res.ok) throw new Error('Failed to get ownership signals');
  return res.json();
}

/**
 * Get reuse patterns for AI Brain
 */
export async function getReusePatterns(): Promise<ReusePatterns> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/reuse-patterns', { token });

  if (!res.ok) throw new Error('Failed to get reuse patterns');
  return res.json();
}

/**
 * Get style signals for AI Brain
 */
export async function getStyleSignals(): Promise<StyleSignals> {
  const token = getAuthToken();
  if (!token) throw new Error('Authentication required');

  const res = await apiFetch('/api/wardrobe/analytics/style-signals', { token });

  if (!res.ok) throw new Error('Failed to get style signals');
  return res.json();
}

// ═══════════════════════════════════════════════════════════════════
// Export default object
// ═══════════════════════════════════════════════════════════════════

export default {
  logWear,
  getWearStats,
  getSeasonalRotation,
  setItemSeason,
  logOutfit,
  getOutfitHistory,
  rateOutfit,
  toggleOutfitFavorite,
  getUnusedItems,
  getSustainabilityInsights,
  recalculateSustainability,
  analyzeColors,
  analyzeCategories,
  getWardrobeConfidence,
  getCapsuleWardrobes,
  getDeclutterSuggestions,
  dismissDeclutterSuggestion,
  actOnDeclutterSuggestion,
  checkPurchaseAvoidance,
  getFullAnalytics,
  getOwnershipSignals,
  getReusePatterns,
  getStyleSignals,
};
