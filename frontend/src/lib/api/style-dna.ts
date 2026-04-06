/**
 * Style DNA API Client
 * API functions for Style DNA feature
 */

import { api as apiClient } from '@/lib/api/client';

export interface StyleDNADashboardData {
  profile: StyleDNAProfile;
  style_map: StyleMapData;
  color_wheel: ColorWheelData;
  brand_universe: BrandUniverseData[];
  evolution_timeline: EvolutionEvent[];
  style_insights: StyleInsight[];
  completeness_breakdown: Record<string, number>;
  recommendations: StyleRecommendations;
}

export interface StyleDNAProfile {
  id: string;
  user_id: string;
  primary_style: string | null;
  secondary_styles: string[];
  style_confidence: number;
  color_preferences: ColorPreferences;
  fit_preference: string;
  fit_preferences: Record<string, string>;
  occasion_preferences: Record<string, number>;
  brand_affinity: BrandAffinity[];
  budget_level: string;
  budget_range: BudgetRange;
  pattern_preferences: PatternPreferences;
  fabric_preferences: FabricPreferences;
  silhouette_preferences: SilhouettePreferences;
  signal_summary: SignalSummary;
  profile_completeness: number;
  profile_version: number;
  created_at: string;
  updated_at: string;
}

export interface ColorPreferences {
  primary: string[];
  secondary: string[];
  avoided: string[];
  undertone: string | null;
  palette_type: string | null;
}

export interface BrandAffinity {
  brand_id: string;
  brand_name?: string;
  affinity_score: number;
  category?: string;
}

export interface BudgetRange {
  per_item_min: number | null;
  per_item_max: number | null;
  monthly_max: number | null;
  currency: string;
}

export interface PatternPreferences {
  preferred: string[];
  avoided: string[];
  neutral: string[];
}

export interface FabricPreferences {
  preferred: string[];
  avoided: string[];
  seasonal: Record<string, string[]>;
}

export interface SilhouettePreferences {
  tops: string[];
  bottoms: string[];
  dresses: string[];
}

export interface SignalSummary {
  wardrobe_items: number;
  liked_outfits: number;
  purchases: number;
  quiz_answers: number;
  browsing_events: number;
  last_analyzed: string | null;
}

export interface StyleMapData {
  dimensions: [string, string][];
  position: { x: number; y: number };
  primary_style: string | null;
  secondary_styles: string[];
  confidence: number;
}

export interface ColorWheelData {
  primary: string[];
  secondary: string[];
  avoided: string[];
  undertone: string | null;
  palette_type: string | null;
  recommended: string[];
}

export interface BrandUniverseData {
  brand_id: string;
  affinity_score: number;
  position: {
    angle: number;
    distance: number;
  };
}

export interface EvolutionEvent {
  id: string;
  user_id: string;
  change_type: string;
  previous_value: Record<string, unknown> | null;
  new_value: Record<string, unknown>;
  drift_magnitude: number | null;
  trigger_source: string;
  created_at: string;
}

export interface StyleInsight {
  type: string;
  title: string;
  message: string;
  icon: string;
}

export interface StyleRecommendations {
  missing_essentials: Array<{
    type: string;
    message: string;
    priority: string;
  }>;
  style_evolution: Array<{
    type: string;
    message: string;
    priority: string;
  }>;
  color_suggestions: Array<{
    colors: string[];
    reason: string;
  }>;
  brand_discoveries: Array<{
    message: string;
    priority: string;
  }>;
}

export interface StyleQuizQuestion {
  id: string;
  type: 'single_select' | 'multi_select' | 'image_select';
  question: string;
  options: Array<{
    id: string;
    label: string;
    image?: string;
    color?: string;
  }>;
}

export interface StyleQuizSubmission {
  quiz_type: string;
  answers: Array<{
    question_id: string;
    selected_options: string[];
    image_selections: string[];
    confidence?: number;
  }>;
  duration_seconds?: number;
}

export interface StyleQuizResult {
  computed_styles: Record<string, number>;
  computed_colors: Record<string, unknown>;
  computed_fit: Record<string, string>;
  confidence: number;
  profile_updated: boolean;
}

export const styleDNAApi = {
  /**
   * Get Style DNA dashboard data
   */
  async getDashboard(): Promise<StyleDNADashboardData> {
    return apiClient.get<StyleDNADashboardData>('/style-dna/dashboard');
  },

  /**
   * Get Style DNA profile
   */
  async getProfile(): Promise<StyleDNAProfile> {
    return apiClient.get<StyleDNAProfile>('/style-dna/profile');
  },

  /**
   * Update Style DNA profile
   */
  async updateProfile(data: Partial<StyleDNAProfile>): Promise<StyleDNAProfile> {
    return apiClient.patch<StyleDNAProfile>('/style-dna/profile', data);
  },

  /**
   * Analyze user's style
   */
  async analyzeStyle(forceRefresh = false): Promise<StyleDNADashboardData> {
    return apiClient.post<StyleDNADashboardData>('/style-dna/analyze', { force_refresh: forceRefresh });
  },

  /**
   * Get profile completeness
   */
  async getCompleteness(): Promise<{
    completeness: number;
    breakdown: Record<string, number>;
    version: number;
  }> {
    return apiClient.get<{ completeness: number; breakdown: Record<string, number>; version: number }>('/style-dna/completeness');
  },

  /**
   * Find similar users
   */
  async findSimilarUsers(
    limit = 10,
    minSimilarity = 0.7
  ): Promise<Array<{
    user_id: string;
    similarity: number;
    shared_styles: string[];
    shared_brands: string[];
    shared_colors: string[];
  }>> {
    return apiClient.get<Array<{
      user_id: string;
      similarity: number;
      shared_styles: string[];
      shared_brands: string[];
      shared_colors: string[];
    }>>('/style-dna/similar-users', { limit, min_similarity: minSimilarity });
  },

  /**
   * Get style cluster
   */
  async getCluster(): Promise<{
    cluster: {
      id: string;
      cluster_name: string;
      cluster_description: string | null;
      dominant_styles: string[];
      dominant_colors: string[];
      cluster_size: number;
    };
    distance_to_centroid: number;
    assignment_confidence: number;
    secondary_clusters: Array<Record<string, unknown>>;
  } | null> {
    return apiClient.get<{
      cluster: {
        id: string;
        cluster_name: string;
        cluster_description: string | null;
        dominant_styles: string[];
        dominant_colors: string[];
        cluster_size: number;
      };
      distance_to_centroid: number;
      assignment_confidence: number;
      secondary_clusters: Array<Record<string, unknown>>;
    } | null>('/style-dna/cluster');
  },

  /**
   * Get quiz questions
   */
  async getQuizQuestions(quizType = 'initial'): Promise<{
    quiz_type: string;
    questions: StyleQuizQuestion[];
    total_questions: number;
  }> {
    return apiClient.get<{ quiz_type: string; questions: StyleQuizQuestion[]; total_questions: number }>('/style-dna/quiz/questions', { quiz_type: quizType });
  },

  /**
   * Submit style quiz
   */
  async submitQuiz(submission: StyleQuizSubmission): Promise<StyleQuizResult> {
    return apiClient.post<StyleQuizResult>('/style-dna/quiz', submission);
  },

  /**
   * Get evolution history
   */
  async getEvolutionHistory(limit = 20): Promise<EvolutionEvent[]> {
    return apiClient.get<EvolutionEvent[]>('/style-dna/evolution', { limit });
  },

  /**
   * Get evolution timeline
   */
  async getEvolutionTimeline(): Promise<{
    timeline: Array<{
      month: string;
      events: EvolutionEvent[];
      change_count: number;
    }>;
    total_events: number;
  }> {
    return apiClient.get<{
      timeline: Array<{ month: string; events: EvolutionEvent[]; change_count: number }>;
      total_events: number;
    }>('/style-dna/evolution/timeline');
  },

  /**
   * Record style signal
   */
  async recordSignal(signal: {
    signal_type: string;
    signal_category: string;
    entity_type?: string;
    entity_id?: string;
    signal_data?: Record<string, unknown>;
    base_weight?: number;
    context?: Record<string, unknown>;
  }): Promise<{ id: string; recorded: boolean; created_at: string }> {
    return apiClient.post<{ id: string; recorded: boolean; created_at: string }>('/style-dna/signals', signal);
  },

  /**
   * Record multiple signals
   */
  async recordBatchSignals(signals: Array<{
    signal_type: string;
    signal_category: string;
    entity_type?: string;
    entity_id?: string;
    signal_data?: Record<string, unknown>;
    base_weight?: number;
    context?: Record<string, unknown>;
  }>): Promise<{ recorded_count: number; signal_ids: string[] }> {
    return apiClient.post<{ recorded_count: number; signal_ids: string[] }>('/style-dna/signals/batch', signals);
  },

  /**
   * Get color preferences
   */
  async getColorPreferences(): Promise<{
    primary: string[];
    secondary: string[];
    avoided: string[];
    undertone: string | null;
    palette_type: string | null;
    recommended: string[];
    color_harmony: { best_combinations: Array<{ base: string; matches: string[]; type: string }> };
  }> {
    return apiClient.get<{
      primary: string[];
      secondary: string[];
      avoided: string[];
      undertone: string | null;
      palette_type: string | null;
      recommended: string[];
      color_harmony: { best_combinations: Array<{ base: string; matches: string[]; type: string }> };
    }>('/style-dna/preferences/colors');
  },

  /**
   * Get occasion preferences
   */
  async getOccasionPreferences(): Promise<{
    occasions: Record<string, number>;
    top_occasions: string[];
    occasion_suggestions: Array<{ occasion: string; message: string; priority: string }>;
  }> {
    return apiClient.get<{
      occasions: Record<string, number>;
      top_occasions: string[];
      occasion_suggestions: Array<{ occasion: string; message: string; priority: string }>;
    }>('/style-dna/preferences/occasions');
  },

  /**
   * Get brand affinity
   */
  async getBrandAffinity(): Promise<{
    brands: BrandAffinity[];
    top_brands: BrandAffinity[];
    brand_count: number;
  }> {
    return apiClient.get<{
      brands: BrandAffinity[];
      top_brands: BrandAffinity[];
      brand_count: number;
    }>('/style-dna/preferences/brands');
  },

  /**
   * Get budget preferences
   */
  async getBudgetPreferences(): Promise<{
    budget_level: string;
    budget_range: BudgetRange;
    suggestions: Array<{ tip: string; brands: string[] }>;
  }> {
    return apiClient.get<{
      budget_level: string;
      budget_range: BudgetRange;
      suggestions: Array<{ tip: string; brands: string[] }>;
    }>('/style-dna/preferences/budget');
  },

  /**
   * Get style insights
   */
  async getInsights(): Promise<{
    insights: StyleInsight[];
    recommendations: StyleRecommendations;
    confidence: number;
    completeness: number;
  }> {
    return apiClient.get<{
      insights: StyleInsight[];
      recommendations: StyleRecommendations;
      confidence: number;
      completeness: number;
    }>('/style-dna/insights');
  },
};

export default styleDNAApi;
