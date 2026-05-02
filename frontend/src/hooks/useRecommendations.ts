/**
 * CONFIT — useRecommendations Hook
 * ==================================
 * React hook for fetching and managing alert recommendations.
 * Provides a clean API for components to interact with recommendations.
 */

import { useCallback, useEffect, useState } from 'react';
import { useAlertRecommendationStore } from '@/stores/alertRecommendationStore';
import type {
  AlertRecommendation,
  GenerateRecommendationsResponse,
  ApplyRecommendationResponse,
  StorePatternAnalysis,
  ABTestAssignment,
} from '@/types/alertRecommendationTypes';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface UseRecommendationsOptions {
  storeId: string;
  autoFetch?: boolean;
  dataWindowDays?: number;
  staleThresholdMs?: number;
}

interface UseRecommendationsReturn {
  // Data
  recommendations: AlertRecommendation[];
  pendingRecommendations: AlertRecommendation[];
  patternAnalysis: StorePatternAnalysis | null;
  abAssignment: ABTestAssignment | null;

  // Loading states
  isLoading: boolean;
  isGenerating: boolean;
  isApplying: boolean;
  error: string | null;

  // Actions
  fetchRecommendations: (forceRefresh?: boolean) => Promise<void>;
  applyRecommendation: (
    recommendationId: string,
    customThresholds?: Record<string, number>
  ) => Promise<ApplyRecommendationResponse | null>;
  dismissRecommendation: (recommendationId: string, reason?: string) => Promise<boolean>;
  markAsShown: (recommendationId: string) => Promise<boolean>;
  submitFeedback: (
    recommendationId: string,
    rating: number,
    feedbackText?: string,
    wasValuable?: boolean
  ) => Promise<boolean>;

  // Utilities
  refresh: () => Promise<void>;
  clearError: () => void;
  isStale: boolean;
}

// ─── API Helper Functions ──────────────────────────────────────────────────────

async function fetchApi<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ─── Main Hook ────────────────────────────────────────────────────────────────

export function useRecommendations({
  storeId,
  autoFetch = true,
  dataWindowDays = 60,
  staleThresholdMs = 10 * 60 * 1000, // 10 minutes
}: UseRecommendationsOptions): UseRecommendationsReturn {
  const {
    getRecommendations,
    getPendingRecommendations,
    getPatternAnalysis,
    getABAssignment,
    setRecommendations,
    updateRecommendation,
    setPatternAnalysis,
    setABAssignment,
    setLoading,
    setGenerating,
    setApplying,
    setError,
    isStale: checkIsStale,
    loadingStoreId,
    error,
    isLoading: storeIsLoading,
    isGenerating: storeIsGenerating,
    isApplying: storeIsApplying,
  } = useAlertRecommendationStore();

  const [localLoading, setLocalLoading] = useState(false);

  // Derived state
  const recommendations = getRecommendations(storeId);
  const pendingRecommendations = getPendingRecommendations(storeId);
  const patternAnalysis = getPatternAnalysis(storeId);
  const abAssignment = getABAssignment(storeId);

  const isLoading = storeIsLoading && loadingStoreId === storeId;
  const isGenerating = storeIsGenerating;
  const isApplying = storeIsApplying;
  const isStale = checkIsStale(storeId, staleThresholdMs);

  // ─── Fetch Recommendations ────────────────────────────────────────────────

  const fetchRecommendations = useCallback(
    async (forceRefresh = false) => {
      if (!storeId) return;

      setLoading(true, storeId);
      setError(null);

      try {
        const data: GenerateRecommendationsResponse = await fetchApi(
          '/api/v1/alert-recommendations/generate',
          {
            method: 'POST',
            body: JSON.stringify({
              store_id: storeId,
              data_window_days: dataWindowDays,
              force_refresh: forceRefresh,
            }),
          }
        );

        setRecommendations(storeId, data.recommendations);

        if (data.pattern_analysis && 'store_id' in data.pattern_analysis) {
          setPatternAnalysis(storeId, data.pattern_analysis as StorePatternAnalysis);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch recommendations';
        setError(message);
        console.error('[useRecommendations] Fetch error:', err);
      } finally {
        setLoading(false);
      }
    },
    [storeId, dataWindowDays, setRecommendations, setPatternAnalysis, setLoading, setError]
  );

  // ─── Apply Recommendation ──────────────────────────────────────────────────

  const applyRecommendation = useCallback(
    async (
      recommendationId: string,
      customThresholds?: Record<string, number>
    ): Promise<ApplyRecommendationResponse | null> => {
      if (!storeId) return null;

      setApplying(true);
      setError(null);

      try {
        const response: ApplyRecommendationResponse = await fetchApi(
          '/api/v1/alert-recommendations/apply',
          {
            method: 'POST',
            body: JSON.stringify({
              recommendation_id: recommendationId,
              store_id: storeId,
              custom_thresholds: customThresholds,
            }),
          }
        );

        if (response.success) {
          updateRecommendation(storeId, recommendationId, {
            status: 'applied',
            applied_at: new Date().toISOString(),
          });
        }

        return response;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to apply recommendation';
        setError(message);
        console.error('[useRecommendations] Apply error:', err);
        return null;
      } finally {
        setApplying(false);
      }
    },
    [storeId, updateRecommendation, setApplying, setError]
  );

  // ─── Dismiss Recommendation ────────────────────────────────────────────────

  const dismissRecommendation = useCallback(
    async (recommendationId: string, reason?: string): Promise<boolean> => {
      if (!storeId) return false;

      setError(null);

      try {
        await fetchApi('/api/v1/alert-recommendations/dismiss', {
          method: 'POST',
          body: JSON.stringify({
            recommendation_id: recommendationId,
            store_id: storeId,
            reason,
          }),
        });

        updateRecommendation(storeId, recommendationId, {
          status: 'dismissed',
          dismissed_at: new Date().toISOString(),
          user_feedback: reason,
        });

        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to dismiss recommendation';
        setError(message);
        console.error('[useRecommendations] Dismiss error:', err);
        return false;
      }
    },
    [storeId, updateRecommendation, setError]
  );

  // ─── Mark as Shown ─────────────────────────────────────────────────────────

  const markAsShown = useCallback(
    async (recommendationId: string): Promise<boolean> => {
      if (!storeId) return false;

      try {
        await fetchApi(
          `/api/v1/alert-recommendations/shown/${recommendationId}?store_id=${storeId}`,
          { method: 'POST' }
        );

        updateRecommendation(storeId, recommendationId, {
          status: 'shown',
          shown_at: new Date().toISOString(),
        });

        return true;
      } catch (err) {
        console.error('[useRecommendations] Mark shown error:', err);
        return false;
      }
    },
    [storeId, updateRecommendation]
  );

  // ─── Submit Feedback ───────────────────────────────────────────────────────

  const submitFeedback = useCallback(
    async (
      recommendationId: string,
      rating: number,
      feedbackText?: string,
      wasValuable = true
    ): Promise<boolean> => {
      if (!storeId) return false;

      try {
        await fetchApi('/api/v1/alert-recommendations/feedback', {
          method: 'POST',
          body: JSON.stringify({
            recommendation_id: recommendationId,
            store_id: storeId,
            rating,
            feedback_text: feedbackText,
            was_valuable: wasValuable,
          }),
        });

        updateRecommendation(storeId, recommendationId, {
          user_rating: rating,
          user_feedback: feedbackText,
          was_valuable: wasValuable,
        });

        return true;
      } catch (err) {
        console.error('[useRecommendations] Feedback error:', err);
        return false;
      }
    },
    [storeId, updateRecommendation]
  );

  // ─── Refresh ───────────────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    await fetchRecommendations(true);
  }, [fetchRecommendations]);

  // ─── Clear Error ────────────────────────────────────────────────────────────

  const clearError = useCallback(() => {
    setError(null);
  }, [setError]);

  // ─── Auto-fetch on mount or when stale ──────────────────────────────────────

  useEffect(() => {
    if (autoFetch && storeId && isStale) {
      fetchRecommendations();
    }
  }, [autoFetch, storeId, isStale, fetchRecommendations]);

  // ─── Fetch A/B Assignment ───────────────────────────────────────────────────

  useEffect(() => {
    if (storeId && !abAssignment) {
      fetchApi(`/api/v1/alert-recommendations/ab-test/assignment/${storeId}`)
        .then((raw) => {
          const data = raw as { assigned: boolean; group?: string; experiment_id?: string };
          if (data.assigned && data.group && data.experiment_id) {
            setABAssignment(storeId, {
              id: '',
              experiment_id: data.experiment_id,
              store_id: storeId,
              group: data.group as 'control' | 'treatment',
              assigned_at: new Date().toISOString(),
              metrics: {},
            });
          }
        })
        .catch((err) => {
          console.error('[useRecommendations] A/B assignment error:', err);
        });
    }
  }, [storeId, abAssignment, setABAssignment]);

  return {
    // Data
    recommendations,
    pendingRecommendations,
    patternAnalysis,
    abAssignment,

    // Loading states
    isLoading,
    isGenerating,
    isApplying,
    error,

    // Actions
    fetchRecommendations,
    applyRecommendation,
    dismissRecommendation,
    markAsShown,
    submitFeedback,

    // Utilities
    refresh,
    clearError,
    isStale,
  };
}

// ─── Simplified Hook for Single Recommendation ────────────────────────────────

export function useRecommendation(
  storeId: string,
  recommendationId: string
) {
  const recommendation = useAlertRecommendationStore((state) =>
    state.recommendationsByStore[storeId]?.find((r) => r.id === recommendationId)
  );

  const { applyRecommendation, dismissRecommendation, isApplying, error } =
    useRecommendations({ storeId, autoFetch: false });

  return {
    recommendation,
    apply: (customThresholds?: Record<string, number>) =>
      applyRecommendation(recommendationId, customThresholds),
    dismiss: (reason?: string) => dismissRecommendation(recommendationId, reason),
    isApplying,
    error,
  };
}

// ─── Hook for A/B Test Info ───────────────────────────────────────────────────

export function useABTestInfo(storeId: string) {
  const abAssignment = useAlertRecommendationStore((state) =>
    state.getABAssignment(storeId)
  );

  const [experiment, setExperiment] = useState<{
    id: string;
    name: string;
    is_active: boolean;
  } | null>(null);

  useEffect(() => {
    if (abAssignment?.experiment_id) {
      fetchApi(`/api/v1/alert-recommendations/ab-test/experiment`)
        .then((raw) => {
          const data = raw as { active: boolean; experiment?: { id: string; name: string; is_active: boolean } };
          if (data.active && data.experiment) {
            setExperiment({
              id: data.experiment.id,
              name: data.experiment.name,
              is_active: data.experiment.is_active,
            });
          }
        })
        .catch((err) => {
          console.error('[useABTestInfo] Fetch error:', err);
        });
    }
  }, [abAssignment?.experiment_id]);

  return {
    group: abAssignment?.group ?? 'control',
    experiment,
    isTreatment: abAssignment?.group === 'treatment',
    isControl: abAssignment?.group === 'control',
  };
}

export default useRecommendations;
