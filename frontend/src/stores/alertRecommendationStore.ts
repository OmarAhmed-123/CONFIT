/**
 * CONFIT — Alert Recommendation Store
 * =====================================
 * Zustand store for managing predictive alert recommendations state.
 * Handles recommendations, pattern analysis, and A/B test assignments.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  AlertRecommendation,
  StorePatternAnalysis,
  ABTestAssignment,
  RecommendationFilterState,
  RecommendationType,
  RecommendationStatus,
  ConfidenceLevel,
} from '@/types/alertRecommendationTypes';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface RecommendationState {
  // Recommendations by store
  recommendationsByStore: Record<string, AlertRecommendation[]>;

  // Pattern analyses by store
  patternAnalysesByStore: Record<string, StorePatternAnalysis>;

  // A/B test assignments by store
  abAssignmentsByStore: Record<string, ABTestAssignment>;

  // Loading states
  isLoading: boolean;
  isGenerating: boolean;
  isApplying: boolean;
  loadingStoreId: string | null;

  // Error states
  error: string | null;

  // Filters
  filters: RecommendationFilterState;

  // Last fetch timestamps
  lastFetchByStore: Record<string, string>;

  // ─── Actions ───

  // Recommendations
  setRecommendations: (storeId: string, recommendations: AlertRecommendation[]) => void;
  addRecommendation: (storeId: string, recommendation: AlertRecommendation) => void;
  updateRecommendation: (storeId: string, recommendationId: string, updates: Partial<AlertRecommendation>) => void;
  removeRecommendation: (storeId: string, recommendationId: string) => void;
  clearRecommendations: (storeId: string) => void;

  // Getters
  getRecommendations: (storeId: string) => AlertRecommendation[];
  getPendingRecommendations: (storeId: string) => AlertRecommendation[];
  getFilteredRecommendations: (storeId: string) => AlertRecommendation[];

  // Pattern Analysis
  setPatternAnalysis: (storeId: string, analysis: StorePatternAnalysis) => void;
  getPatternAnalysis: (storeId: string) => StorePatternAnalysis | null;

  // A/B Test
  setABAssignment: (storeId: string, assignment: ABTestAssignment) => void;
  getABAssignment: (storeId: string) => ABTestAssignment | null;

  // Loading
  setLoading: (isLoading: boolean, storeId?: string) => void;
  setGenerating: (isGenerating: boolean) => void;
  setApplying: (isApplying: boolean) => void;
  setError: (error: string | null) => void;

  // Filters
  setFilters: (filters: Partial<RecommendationFilterState>) => void;
  resetFilters: () => void;

  // Cache management
  markStale: (storeId: string) => void;
  isStale: (storeId: string, maxAgeMs?: number) => boolean;
}

// ─── Default Filters ───────────────────────────────────────────────────────────

const DEFAULT_FILTERS: RecommendationFilterState = {
  types: [],
  status: [],
  confidence: 'all',
  sortBy: 'rank',
  sortDirection: 'desc',
};

// ─── Store Implementation ─────────────────────────────────────────────────────

export const useAlertRecommendationStore = create<RecommendationState>()(
  persist(
    (set, get) => ({
      // Initial state
      recommendationsByStore: {},
      patternAnalysesByStore: {},
      abAssignmentsByStore: {},
      isLoading: false,
      isGenerating: false,
      isApplying: false,
      loadingStoreId: null,
      error: null,
      filters: { ...DEFAULT_FILTERS },
      lastFetchByStore: {},

      // ─── Recommendation Actions ─────────────────────────────────────────────

      setRecommendations: (storeId, recommendations) =>
        set((state) => ({
          recommendationsByStore: {
            ...state.recommendationsByStore,
            [storeId]: recommendations,
          },
          lastFetchByStore: {
            ...state.lastFetchByStore,
            [storeId]: new Date().toISOString(),
          },
        })),

      addRecommendation: (storeId, recommendation) =>
        set((state) => {
          const existing = state.recommendationsByStore[storeId] || [];
          return {
            recommendationsByStore: {
              ...state.recommendationsByStore,
              [storeId]: [...existing, recommendation],
            },
          };
        }),

      updateRecommendation: (storeId, recommendationId, updates) =>
        set((state) => {
          const existing = state.recommendationsByStore[storeId] || [];
          const updated = existing.map((r) =>
            r.id === recommendationId ? { ...r, ...updates } : r
          );
          return {
            recommendationsByStore: {
              ...state.recommendationsByStore,
              [storeId]: updated,
            },
          };
        }),

      removeRecommendation: (storeId, recommendationId) =>
        set((state) => {
          const existing = state.recommendationsByStore[storeId] || [];
          return {
            recommendationsByStore: {
              ...state.recommendationsByStore,
              [storeId]: existing.filter((r) => r.id !== recommendationId),
            },
          };
        }),

      clearRecommendations: (storeId) =>
        set((state) => {
          const { [storeId]: _, ...rest } = state.recommendationsByStore;
          return {
            recommendationsByStore: rest,
          };
        }),

      // ─── Getters ─────────────────────────────────────────────────────────────

      getRecommendations: (storeId) => {
        return get().recommendationsByStore[storeId] || [];
      },

      getPendingRecommendations: (storeId) => {
        const recommendations = get().recommendationsByStore[storeId] || [];
        return recommendations.filter(
          (r) => r.status === 'pending' || r.status === 'shown'
        );
      },

      getFilteredRecommendations: (storeId) => {
        const recommendations = get().recommendationsByStore[storeId] || [];
        const { filters } = get();

        let filtered = [...recommendations];

        // Filter by types
        if (filters.types.length > 0) {
          filtered = filtered.filter((r) => filters.types.includes(r.type));
        }

        // Filter by status
        if (filters.status.length > 0) {
          filtered = filtered.filter((r) => filters.status.includes(r.status));
        }

        // Filter by confidence
        if (filters.confidence !== 'all') {
          filtered = filtered.filter((r) => r.confidence === filters.confidence);
        }

        // Sort
        filtered.sort((a, b) => {
          let comparison = 0;

          switch (filters.sortBy) {
            case 'rank':
              comparison = a.rank_score - b.rank_score;
              break;
            case 'generated':
              comparison = new Date(a.generated_at).getTime() - new Date(b.generated_at).getTime();
              break;
            case 'impact':
              const impactOrder = { low: 0, medium: 1, high: 2, critical: 3 };
              comparison = (impactOrder[a.impact_estimate] || 0) - (impactOrder[b.impact_estimate] || 0);
              break;
          }

          return filters.sortDirection === 'desc' ? -comparison : comparison;
        });

        return filtered;
      },

      // ─── Pattern Analysis ────────────────────────────────────────────────────

      setPatternAnalysis: (storeId, analysis) =>
        set((state) => ({
          patternAnalysesByStore: {
            ...state.patternAnalysesByStore,
            [storeId]: analysis,
          },
        })),

      getPatternAnalysis: (storeId) => {
        return get().patternAnalysesByStore[storeId] || null;
      },

      // ─── A/B Test ────────────────────────────────────────────────────────────

      setABAssignment: (storeId, assignment) =>
        set((state) => ({
          abAssignmentsByStore: {
            ...state.abAssignmentsByStore,
            [storeId]: assignment,
          },
        })),

      getABAssignment: (storeId) => {
        return get().abAssignmentsByStore[storeId] || null;
      },

      // ─── Loading States ──────────────────────────────────────────────────────

      setLoading: (isLoading, storeId) =>
        set({
          isLoading,
          loadingStoreId: storeId || null,
        }),

      setGenerating: (isGenerating) =>
        set({ isGenerating }),

      setApplying: (isApplying) =>
        set({ isApplying }),

      setError: (error) =>
        set({ error }),

      // ─── Filters ─────────────────────────────────────────────────────────────

      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
        })),

      resetFilters: () =>
        set({ filters: { ...DEFAULT_FILTERS } }),

      // ─── Cache Management ────────────────────────────────────────────────────

      markStale: (storeId) =>
        set((state) => {
          const { [storeId]: _, ...rest } = state.lastFetchByStore;
          return {
            lastFetchByStore: rest,
          };
        }),

      isStale: (storeId, maxAgeMs = 10 * 60 * 1000) => {
        const lastFetch = get().lastFetchByStore[storeId];
        if (!lastFetch) return true;

        const lastFetchTime = new Date(lastFetch).getTime();
        const now = Date.now();

        return now - lastFetchTime > maxAgeMs;
      },
    }),
    {
      name: 'confit-alert-recommendations',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist recommendations and last fetch times
        recommendationsByStore: state.recommendationsByStore,
        lastFetchByStore: state.lastFetchByStore,
        filters: state.filters,
        abAssignmentsByStore: state.abAssignmentsByStore,
      }),
    }
  )
);

// ─── Selector Hooks ────────────────────────────────────────────────────────────

export const useRecommendations = (storeId: string) =>
  useAlertRecommendationStore((state) => state.getRecommendations(storeId));

export const usePendingRecommendations = (storeId: string) =>
  useAlertRecommendationStore((state) => state.getPendingRecommendations(storeId));

export const useFilteredRecommendations = (storeId: string) =>
  useAlertRecommendationStore((state) => state.getFilteredRecommendations(storeId));

export const usePatternAnalysis = (storeId: string) =>
  useAlertRecommendationStore((state) => state.getPatternAnalysis(storeId));

export const useABAssignment = (storeId: string) =>
  useAlertRecommendationStore((state) => state.getABAssignment(storeId));

export const useRecommendationLoading = () =>
  useAlertRecommendationStore((state) => ({
    isLoading: state.isLoading,
    isGenerating: state.isGenerating,
    isApplying: state.isApplying,
    loadingStoreId: state.loadingStoreId,
    error: state.error,
  }));

export const useRecommendationFilters = () =>
  useAlertRecommendationStore((state) => state.filters);

// ─── Action Hooks ──────────────────────────────────────────────────────────────

export const useRecommendationActions = () =>
  useAlertRecommendationStore((state) => ({
    setRecommendations: state.setRecommendations,
    updateRecommendation: state.updateRecommendation,
    removeRecommendation: state.removeRecommendation,
    clearRecommendations: state.clearRecommendations,
    setPatternAnalysis: state.setPatternAnalysis,
    setABAssignment: state.setABAssignment,
    setLoading: state.setLoading,
    setGenerating: state.setGenerating,
    setApplying: state.setApplying,
    setError: state.setError,
    setFilters: state.setFilters,
    resetFilters: state.resetFilters,
    markStale: state.markStale,
    isStale: state.isStale,
  }));

export default useAlertRecommendationStore;
