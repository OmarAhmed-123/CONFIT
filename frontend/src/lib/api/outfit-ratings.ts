/**
 * CONFIT Outfit Ratings API
 * =========================
 * API hooks and types for outfit rating, like, save, share operations
 */

import { api } from './client';

// Types
export interface OutfitRating {
  id: string;
  outfit_id: string;
  user_id: string;
  rating: number;
  review?: string;
  created_at: string;
  updated_at: string;
}

export interface OutfitRatingCreate {
  rating: number;
  review?: string;
}

export interface OutfitLikeToggleResponse {
  outfit_id: string;
  is_liked?: boolean;
  is_disliked?: boolean;
  like_count: number;
  dislike_count: number;
}

export interface OutfitLike {
  id: string;
  outfit_id: string;
  user_id: string;
  is_like: boolean;
  created_at: string;
}

export interface OutfitSave {
  id: string;
  outfit_id: string;
  user_id: string;
  collection_name?: string;
  created_at: string;
}

export interface OutfitSaveCreate {
  collection_name?: string;
}

export interface OutfitShare {
  id: string;
  outfit_id: string;
  user_id: string;
  platform?: string;
  created_at: string;
}

export interface OutfitShareCreate {
  platform?: string;
}

export interface OutfitPopularity {
  outfit_id: string;
  total_ratings: number;
  avg_rating: number;
  like_count: number;
  dislike_count: number;
  save_count: number;
  share_count: number;
  view_count: number;
  trending_score: number;
  popularity_score: number;
  style_relevance_score: number;
  last_activity_at: string;
}

export interface TrendingOutfitItem {
  outfit_id: string;
  title: string;
  items: Array<{
    item_type: 'product' | 'wardrobe';
    reference_id: string;
    name: string;
    brand?: string;
    category?: string;
    color?: string;
    price?: number;
    currency?: string;
  }>;
  total_price?: number;
  currency: string;
  avg_rating: number;
  total_ratings: number;
  like_count: number;
  trending_score: number;
  popularity_score: number;
  rank: number;
}

export interface TrendingOutfitsResponse {
  outfits: TrendingOutfitItem[];
  time_window: string;
  total_count: number;
  page: number;
  page_size: number;
}

export interface TrendingFilters {
  time_window?: '24h' | '7d' | '30d' | 'all';
  min_rating?: number;
  min_ratings_count?: number;
  page?: number;
  page_size?: number;
}

export interface UserEngagementSummary {
  outfit_id: string;
  has_rated: boolean;
  user_rating?: number;
  has_liked: boolean;
  is_like?: boolean;
  has_saved: boolean;
  collection_name?: string;
  has_shared: boolean;
}

export interface OutfitWithRatings {
  id: string;
  owner_user_id: string;
  title: string;
  items: Array<Record<string, unknown>>;
  occasion?: string;
  notes?: string;
  budget_limit?: number;
  total_price?: number;
  currency: string;
  created_at: string;
  updated_at: string;
  share_slug?: string;
  popularity?: OutfitPopularity;
  user_rating?: number;
  user_liked?: boolean;
  user_saved: boolean;
}

// API Functions

/**
 * Rate an outfit (1-5 stars)
 */
export async function rateOutfit(outfitId: string, data: OutfitRatingCreate): Promise<OutfitRating> {
  return api.post<OutfitRating>(`/outfit-ratings/${outfitId}/rate`, data);
}

/**
 * Get user's rating for an outfit
 */
export async function getUserRating(outfitId: string): Promise<OutfitRating | null> {
  return api.get<OutfitRating | null>(`/outfit-ratings/${outfitId}/rating`);
}

/**
 * Get all ratings for an outfit
 */
export async function getOutfitRatings(
  outfitId: string,
  page: number = 1,
  pageSize: number = 20
): Promise<OutfitRating[]> {
  return api.get<OutfitRating[]>(`/outfit-ratings/${outfitId}/ratings`, { page, page_size: pageSize });
}

/**
 * Delete user's rating for an outfit
 */
export async function deleteRating(outfitId: string): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`/outfit-ratings/${outfitId}/rating`);
}

/**
 * Toggle like/dislike for an outfit
 */
export async function toggleOutfitLike(
  outfitId: string,
  isLike: boolean
): Promise<OutfitLikeToggleResponse> {
  return api.post<OutfitLikeToggleResponse>(`/outfit-ratings/${outfitId}/like`, { is_like: isLike });
}

/**
 * Get user's like status for an outfit
 */
export async function getUserLike(outfitId: string): Promise<OutfitLike | null> {
  return api.get<OutfitLike | null>(`/outfit-ratings/${outfitId}/like`);
}

/**
 * Save an outfit to user's collection
 */
export async function saveOutfit(outfitId: string, data?: OutfitSaveCreate): Promise<OutfitSave> {
  return api.post<OutfitSave>(`/outfit-ratings/${outfitId}/save`, data);
}

/**
 * Remove an outfit from user's saved collection
 */
export async function unsaveOutfit(outfitId: string): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`/outfit-ratings/${outfitId}/save`);
}

/**
 * Get user's saved outfits
 */
export async function getSavedOutfits(
  collectionName?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<OutfitSave[]> {
  return api.get<OutfitSave[]>('/outfit-ratings/saved', {
    collection_name: collectionName,
    page,
    page_size: pageSize,
  });
}

/**
 * Record an outfit share event
 */
export async function recordOutfitShare(
  outfitId: string,
  platform?: string
): Promise<OutfitShare> {
  return api.post<OutfitShare>(`/outfit-ratings/${outfitId}/share`, { platform });
}

/**
 * Record a view for an outfit
 */
export async function recordOutfitView(outfitId: string): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>(`/outfit-ratings/${outfitId}/view`);
}

/**
 * Get popularity metrics for an outfit
 */
export async function getOutfitPopularity(outfitId: string): Promise<OutfitPopularity> {
  return api.get<OutfitPopularity>(`/outfit-ratings/${outfitId}/popularity`);
}

/**
 * Get user's engagement summary for an outfit
 */
export async function getUserEngagement(outfitId: string): Promise<UserEngagementSummary> {
  return api.get<UserEngagementSummary>(`/outfit-ratings/${outfitId}/engagement`);
}

/**
 * Get outfit details with rating info
 */
export async function getOutfitWithRatings(outfitId: string): Promise<OutfitWithRatings> {
  return api.get<OutfitWithRatings>(`/outfit-ratings/${outfitId}/details`);
}

/**
 * Get trending outfits
 */
export async function getTrendingOutfits(filters?: TrendingFilters): Promise<TrendingOutfitsResponse> {
  return api.get<TrendingOutfitsResponse>('/outfit-ratings/trending', filters as Record<string, string | number | boolean | undefined>);
}

/**
 * Get popular outfits
 */
export async function getPopularOutfits(filters?: TrendingFilters): Promise<TrendingOutfitsResponse> {
  return api.get<TrendingOutfitsResponse>('/outfit-ratings/popular', filters as Record<string, string | number | boolean | undefined>);
}
