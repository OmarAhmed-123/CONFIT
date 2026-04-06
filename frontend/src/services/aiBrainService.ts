/**
 * CONFIT Frontend — AI Central Brain Service
 * ==========================================
 * Client-side integration with the AI personalization engine.
 * 
 * Handles:
 * - Signal collection and tracking
 * - Recommendation fetching
 * - Fashion rule validation
 * - Trend adaptation
 */

import { api } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';

// ── Types ───────────────────────────────────────────────────────────

export interface StyleVector {
  archetype: string | null;
  archetype_confidence: number;
  dimensions: {
    classic: number;
    trendy: number;
    minimalist: number;
    maximalist: number;
    feminine: number;
    masculine: number;
    edgy: number;
    romantic: number;
  };
  colors: {
    preferred: Record<string, number>;
    avoided: string[];
  };
  brands: Record<string, number>;
  categories: Record<string, number>;
  price_behavior: {
    min: number | null;
    max: number | null;
    avg: number | null;
  };
  signal_strength: number;
  confidence_level: 'low' | 'medium' | 'high';
}

export interface WardrobeContext {
  categories: Record<string, string[]>;
  available_colors: string[];
  available_brands: string[];
  total_items: number;
}

export interface ContextualFactors {
  climate_zone: string | null;
  work_environment: string | null;
  activity_level: string | null;
  weather_preferences: Record<string, any>;
  occasion_weights: Record<string, any>;
  cultural_influences: string[];
  modesty_preference: string | null;
}

export interface OutfitRecommendation {
  id: string;
  items: any[];
  scores: {
    style_alignment: number;
    color_harmony: number;
    occasion_fit: number;
    trend_alignment: number;
    wardrobe_compatibility: number;
    budget_fit: number;
  };
  explanation: string;
  confidence: number;
}

export interface ColorValidation {
  valid: boolean;
  harmony?: string;
  description?: string;
  confidence: number;
  reason?: string;
  warning?: string;
}

export interface PatternValidation {
  valid: boolean;
  confidence: number;
  reason?: string;
}

export interface TrendData {
  colors: string[];
  patterns: string[];
  silhouettes: string[];
  items: string[];
  avoid: string[];
}

// ── Signal Tracking ─────────────────────────────────────────────────

/**
 * Track a user interaction for implicit preference learning.
 */
export async function trackInteraction(
  interactionType: string,
  entityType: string,
  entityId: string,
  context?: Record<string, any>,
  durationMs?: number
): Promise<void> {
  try {
    await api.post(API_ENDPOINTS.BRAIN.TRACK_INTERACTION, {
      interaction_type: interactionType,
      entity_type: entityType,
      entity_id: entityId,
      context,
      duration_ms: durationMs,
    });
  } catch (error) {
    console.warn('Failed to track interaction:', error);
  }
}

/**
 * Track outfit feedback (accepted/rejected) for learning.
 */
export async function trackOutfitFeedback(
  outfitId: string,
  accepted: boolean,
  feedbackType: 'explicit' | 'implicit' = 'explicit',
  reason?: string,
  context?: Record<string, any>
): Promise<void> {
  try {
    await api.post(API_ENDPOINTS.BRAIN.TRACK_OUTFIT_FEEDBACK, {
      outfit_id: outfitId,
      accepted,
      feedback_type: feedbackType,
      reason,
      context,
    });
  } catch (error) {
    console.warn('Failed to track outfit feedback:', error);
  }
}

/**
 * Track occasion-based outfit patterns.
 */
export async function trackOccasionPattern(
  occasion: string,
  outfitId: string,
  context?: Record<string, any>
): Promise<void> {
  try {
    await api.post(API_ENDPOINTS.BRAIN.TRACK_OCCASION, {
      occasion,
      outfit_id: outfitId,
      context,
    });
  } catch (error) {
    console.warn('Failed to track occasion pattern:', error);
  }
}

/**
 * Track budget-related behaviors.
 */
export async function trackBudgetBehavior(
  action: string,
  amount: number,
  context?: Record<string, any>
): Promise<void> {
  try {
    await api.post(API_ENDPOINTS.BRAIN.TRACK_BUDGET, {
      action,
      amount,
      context,
    });
  } catch (error) {
    console.warn('Failed to track budget behavior:', error);
  }
}

// ── Preference Aggregation ──────────────────────────────────────────

/**
 * Get user's aggregated style vector.
 */
export async function getStyleVector(): Promise<StyleVector | null> {
  try {
    return await api.get<StyleVector>(API_ENDPOINTS.BRAIN.STYLE_VECTOR);
  } catch (error) {
    console.warn('Failed to get style vector:', error);
    return null;
  }
}

/**
 * Get wardrobe-aware context for styling.
 */
export async function getWardrobeContext(): Promise<WardrobeContext | null> {
  try {
    return await api.get<WardrobeContext>(API_ENDPOINTS.BRAIN.WARDROBE_CONTEXT);
  } catch (error) {
    console.warn('Failed to get wardrobe context:', error);
    return null;
  }
}

/**
 * Get contextual factors (location, weather, lifestyle).
 */
export async function getContextualFactors(): Promise<ContextualFactors | null> {
  try {
    return await api.get<ContextualFactors>(API_ENDPOINTS.BRAIN.CONTEXTUAL_FACTORS);
  } catch (error) {
    console.warn('Failed to get contextual factors:', error);
    return null;
  }
}

// ── Recommendations ────────────────────────────────────────────────

/**
 * Generate personalized outfit recommendations.
 */
export async function getOutfitRecommendations(
  occasion?: string,
  budget?: number,
  itemConstraints?: Record<string, string>,
  useWardrobe: boolean = true,
  limit: number = 5
): Promise<OutfitRecommendation[]> {
  try {
    const response = await api.post<{ recommendations: OutfitRecommendation[] }>(
      API_ENDPOINTS.BRAIN.RECOMMENDATIONS,
      {
        occasion,
        budget,
        item_constraints: itemConstraints,
        use_wardrobe: useWardrobe,
        limit,
      }
    );
    return response.recommendations || [];
  } catch (error) {
    console.warn('Failed to get outfit recommendations:', error);
    return [];
  }
}

// ── Fashion Rule Validation ─────────────────────────────────────────

/**
 * Validate color combination against fashion rules.
 */
export async function validateColors(colors: string[]): Promise<ColorValidation> {
  try {
    return await api.post<ColorValidation>(API_ENDPOINTS.BRAIN.VALIDATE_COLORS, { colors });
  } catch (error) {
    console.warn('Failed to validate colors:', error);
    return { valid: true, confidence: 0.5 };
  }
}

/**
 * Validate pattern combination against fashion rules.
 */
export async function validatePatterns(patterns: string[]): Promise<PatternValidation> {
  try {
    return await api.post<PatternValidation>(API_ENDPOINTS.BRAIN.VALIDATE_PATTERNS, { patterns });
  } catch (error) {
    console.warn('Failed to validate patterns:', error);
    return { valid: true, confidence: 0.5 };
  }
}

/**
 * Validate silhouette balance for proportion.
 */
export async function validateSilhouette(silhouettes: string[]): Promise<PatternValidation> {
  try {
    return await api.post<PatternValidation>(API_ENDPOINTS.BRAIN.VALIDATE_SILHOUETTE, { silhouettes });
  } catch (error) {
    console.warn('Failed to validate silhouette:', error);
    return { valid: true, confidence: 0.5 };
  }
}

/**
 * Check if outfit meets occasion dress code requirements.
 */
export async function checkOccasionAppropriateness(
  outfitData: Record<string, any>,
  occasion: string
): Promise<{ appropriate: boolean; issues: string[]; score: number }> {
  try {
    return await api.post<{ appropriate: boolean; issues: string[]; score: number }>(
      API_ENDPOINTS.BRAIN.VALIDATE_OCCASION,
      { outfit_data: outfitData, occasion }
    );
  } catch (error) {
    console.warn('Failed to check occasion appropriateness:', error);
    return { appropriate: true, issues: [], score: 0.5 };
  }
}

// ── Trends ──────────────────────────────────────────────────────────

/**
 * Get current trending elements.
 */
export async function getTrends(): Promise<TrendData | null> {
  try {
    return await api.get<TrendData>(API_ENDPOINTS.BRAIN.TRENDS);
  } catch (error) {
    console.warn('Failed to get trends:', error);
    return null;
  }
}

/**
 * Adapt recommendations to current trends based on user's sensitivity.
 */
export async function adaptToTrends(trendSensitivity: number = 0.5): Promise<TrendData | null> {
  try {
    return await api.get<TrendData>(API_ENDPOINTS.BRAIN.TRENDS_ADAPT, { trend_sensitivity: trendSensitivity });
  } catch (error) {
    console.warn('Failed to adapt to trends:', error);
    return null;
  }
}

// ── Confidence ──────────────────────────────────────────────────────

/**
 * Recalculate user's confidence scores.
 */
export async function recalculateConfidence(triggerEvent?: string): Promise<any> {
  try {
    return await api.post(API_ENDPOINTS.BRAIN.CONFIDENCE_RECALCULATE, { trigger_event: triggerEvent });
  } catch (error) {
    console.warn('Failed to recalculate confidence:', error);
    return null;
  }
}

/**
 * Get detailed breakdown of user's confidence dimensions.
 */
export async function getConfidenceBreakdown(): Promise<any> {
  try {
    return await api.get(API_ENDPOINTS.BRAIN.CONFIDENCE_BREAKDOWN);
  } catch (error) {
    console.warn('Failed to get confidence breakdown:', error);
    return null;
  }
}

// ── Utility Hooks ───────────────────────────────────────────────────

/**
 * Debounced signal tracker for performance optimization.
 */
let interactionTimeout: NodeJS.Timeout | null = null;
const pendingInteractions: Array<{
  type: string;
  entityType: string;
  entityId: string;
  context?: Record<string, any>;
  durationMs?: number;
}> = [];

export function queueInteraction(
  type: string,
  entityType: string,
  entityId: string,
  context?: Record<string, any>,
  durationMs?: number
): void {
  pendingInteractions.push({ type, entityType, entityId, context, durationMs });
  
  if (interactionTimeout) {
    clearTimeout(interactionTimeout);
  }
  
  interactionTimeout = setTimeout(() => {
    // Batch send interactions
    const batch = [...pendingInteractions];
    pendingInteractions.length = 0;
    
    batch.forEach((interaction) => {
      trackInteraction(
        interaction.type,
        interaction.entityType,
        interaction.entityId,
        interaction.context,
        interaction.durationMs
      );
    });
  }, 1000);
}

/**
 * Calculate style score for an outfit based on multiple dimensions.
 */
export function calculateStyleScore(
  styleVector: StyleVector,
  occasion: string,
  items: any[]
): number {
  let score = 50; // Base score
  
  // Boost for archetype match
  if (styleVector.archetype_confidence > 0.7) {
    score += 15;
  }
  
  // Boost for high signal strength
  if (styleVector.signal_strength > 20) {
    score += 10;
  }
  
  // Boost for color preferences match
  const preferredColors = Object.keys(styleVector.colors.preferred);
  if (preferredColors.length > 0) {
    score += 10;
  }
  
  // Cap at 100
  return Math.min(score, 100);
}

// Export all functions as named exports
export const aiBrainService = {
  trackInteraction,
  trackOutfitFeedback,
  trackOccasionPattern,
  trackBudgetBehavior,
  getStyleVector,
  getWardrobeContext,
  getContextualFactors,
  getOutfitRecommendations,
  validateColors,
  validatePatterns,
  validateSilhouette,
  checkOccasionAppropriateness,
  getTrends,
  adaptToTrends,
  recalculateConfidence,
  getConfidenceBreakdown,
  queueInteraction,
  calculateStyleScore,
};
