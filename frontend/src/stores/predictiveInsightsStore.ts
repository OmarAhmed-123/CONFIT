/**
 * CONFIT — Predictive Insights Store
 * ====================================
 * Zustand store for managing predictive analytics state including anomalies,
 * forecasts, and opportunities. Integrates with the sales filter store for
 * drill-down functionality.
 *
 * Features:
 * - Anomaly state management with acknowledgment
 * - Forecast caching by horizon
 * - Opportunity tracking
 * - Sensitivity configuration
 * - Drill-down filter integration
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  DetectedAnomaly,
  RevenueForecast,
  EmergingOpportunity,
  BaselineMetrics,
  CategoryBaseline,
  ProductBaseline,
  MetricTrend,
  AnomalyDetectionConfig,
  ForecastHorizon,
  AnomalySeverity,
  AnomalyDrillDownFilters,
  DEFAULT_ANOMALY_CONFIG,
} from '@/types/predictiveInsightsTypes';

// ─── Store State Interface ─────────────────────────────────────────────

interface PredictiveInsightsState {
  // ─── Anomaly State ───
  anomalies: DetectedAnomaly[];
  acknowledgedAnomalies: Set<string>;
  dismissedAnomalies: Set<string>;

  // ─── Forecast State ───
  forecasts: Record<ForecastHorizon, RevenueForecast | null>;
  lastForecastUpdate: string | null;

  // ─── Opportunity State ───
  opportunities: EmergingOpportunity[];
  acknowledgedOpportunities: Set<string>;

  // ─── Baseline State ───
  overallBaseline: BaselineMetrics | null;
  categoryBaselines: Record<string, CategoryBaseline>;
  productBaselines: Record<string, ProductBaseline>;

  // ─── Trend State ───
  trends: MetricTrend[];
  trendDirection: 'up' | 'down' | 'stable';

  // ─── Configuration ───
  config: AnomalyDetectionConfig;
  sensitivity: 'high' | 'medium' | 'low';

  // ─── UI State ───
  isComputing: boolean;
  isPanelOpen: boolean;
  lastComputed: string | null;

  // ─── Anomaly Actions ───
  setAnomalies: (anomalies: DetectedAnomaly[]) => void;
  acknowledgeAnomaly: (id: string) => void;
  dismissAnomaly: (id: string) => void;
  restoreAnomaly: (id: string) => void;
  clearDismissedAnomalies: () => void;
  getActiveAnomalies: () => DetectedAnomaly[];
  getAnomaliesBySeverity: (severity: AnomalySeverity) => DetectedAnomaly[];
  getUnacknowledgedCount: () => number;

  // ─── Forecast Actions ───
  setForecasts: (forecasts: Record<ForecastHorizon, RevenueForecast | null>) => void;
  getForecast: (horizon: ForecastHorizon) => RevenueForecast | null;

  // ─── Opportunity Actions ───
  setOpportunities: (opportunities: EmergingOpportunity[]) => void;
  acknowledgeOpportunity: (id: string) => void;
  getActiveOpportunities: () => EmergingOpportunity[];

  // ─── Baseline Actions ───
  setOverallBaseline: (baseline: BaselineMetrics | null) => void;
  setCategoryBaselines: (baselines: Record<string, CategoryBaseline>) => void;
  setProductBaselines: (baselines: Record<string, ProductBaseline>) => void;

  // ─── Trend Actions ───
  setTrends: (trends: MetricTrend[]) => void;
  setTrendDirection: (direction: 'up' | 'down' | 'stable') => void;

  // ─── Configuration Actions ───
  setSensitivity: (sensitivity: 'high' | 'medium' | 'low') => void;
  updateConfig: (config: Partial<AnomalyDetectionConfig>) => void;

  // ─── UI Actions ───
  setComputing: (computing: boolean) => void;
  setPanelOpen: (open: boolean) => void;
  setLastComputed: (timestamp: string) => void;

  // ─── Drill-Down Actions ───
  getDrillDownFilters: (anomalyId: string) => AnomalyDrillDownFilters | null;

  // ─── Reset ───
  reset: () => void;
}

// ─── Default State ──────────────────────────────────────────────────────

const DEFAULT_CONFIG: AnomalyDetectionConfig = {
  criticalZScoreThreshold: 2.5,
  warningZScoreThreshold: 2.0,
  minPercentDeviation: 15,
  baselineWindowDays: 30,
  minDataPoints: 10,
  enableOpportunities: true,
  enableForecasting: true,
  forecastHorizons: ['7d', '14d', '30d'],
};

const initialState = {
  anomalies: [],
  acknowledgedAnomalies: new Set<string>(),
  dismissedAnomalies: new Set<string>(),
  forecasts: {
    '7d': null,
    '14d': null,
    '30d': null,
  } as Record<ForecastHorizon, RevenueForecast | null>,
  lastForecastUpdate: null,
  opportunities: [],
  acknowledgedOpportunities: new Set<string>(),
  overallBaseline: null,
  categoryBaselines: {},
  productBaselines: {},
  trends: [],
  trendDirection: 'stable' as const,
  config: DEFAULT_CONFIG,
  sensitivity: 'medium' as const,
  isComputing: false,
  isPanelOpen: false,
  lastComputed: null,
};

// ─── Store Implementation ──────────────────────────────────────────────

export const usePredictiveInsightsStore = create<PredictiveInsightsState>()(
  persist(
    (set, get) => ({
      ...initialState,

      // ─── Anomaly Actions ───

      setAnomalies: (anomalies) => {
        set((state) => ({
          // Preserve acknowledgment and dismissal state
          anomalies: anomalies.map((a) => ({
            ...a,
            acknowledged: state.acknowledgedAnomalies.has(a.id),
            dismissed: state.dismissedAnomalies.has(a.id),
          })),
        }));
      },

      acknowledgeAnomaly: (id) => {
        set((state) => ({
          acknowledgedAnomalies: new Set([...state.acknowledgedAnomalies, id]),
          anomalies: state.anomalies.map((a) =>
            a.id === id ? { ...a, acknowledged: true } : a
          ),
        }));
      },

      dismissAnomaly: (id) => {
        set((state) => ({
          dismissedAnomalies: new Set([...state.dismissedAnomalies, id]),
          anomalies: state.anomalies.map((a) =>
            a.id === id ? { ...a, dismissed: true, isActive: false } : a
          ),
        }));
      },

      restoreAnomaly: (id) => {
        set((state) => {
          const newDismissed = new Set(state.dismissedAnomalies);
          newDismissed.delete(id);
          return {
            dismissedAnomalies: newDismissed,
            anomalies: state.anomalies.map((a) =>
              a.id === id ? { ...a, dismissed: false, isActive: true } : a
            ),
          };
        });
      },

      clearDismissedAnomalies: () => {
        set((state) => ({
          dismissedAnomalies: new Set(),
          anomalies: state.anomalies.map((a) => ({ ...a, dismissed: false })),
        }));
      },

      getActiveAnomalies: () => {
        const { anomalies, dismissedAnomalies } = get();
        return anomalies.filter((a) => !dismissedAnomalies.has(a.id));
      },

      getAnomaliesBySeverity: (severity) => {
        const { anomalies, dismissedAnomalies } = get();
        return anomalies.filter(
          (a) => a.severity === severity && !dismissedAnomalies.has(a.id)
        );
      },

      getUnacknowledgedCount: () => {
        const { anomalies, acknowledgedAnomalies, dismissedAnomalies } = get();
        return anomalies.filter(
          (a) =>
            !acknowledgedAnomalies.has(a.id) && !dismissedAnomalies.has(a.id)
        ).length;
      },

      // ─── Forecast Actions ───

      setForecasts: (forecasts) => {
        set({
          forecasts,
          lastForecastUpdate: new Date().toISOString(),
        });
      },

      getForecast: (horizon) => {
        return get().forecasts[horizon];
      },

      // ─── Opportunity Actions ───

      setOpportunities: (opportunities) => {
        set((state) => ({
          opportunities: opportunities.map((o) => ({
            ...o,
            acknowledged: state.acknowledgedOpportunities.has(o.id),
          })),
        }));
      },

      acknowledgeOpportunity: (id) => {
        set((state) => ({
          acknowledgedOpportunities: new Set([...state.acknowledgedOpportunities, id]),
          opportunities: state.opportunities.map((o) =>
            o.id === id ? { ...o, acknowledged: true } : o
          ),
        }));
      },

      getActiveOpportunities: () => {
        const { opportunities, acknowledgedOpportunities } = get();
        return opportunities.filter((o) => !acknowledgedOpportunities.has(o.id));
      },

      // ─── Baseline Actions ───

      setOverallBaseline: (baseline) => {
        set({ overallBaseline: baseline });
      },

      setCategoryBaselines: (baselines) => {
        set({ categoryBaselines: baselines });
      },

      setProductBaselines: (baselines) => {
        set({ productBaselines: baselines });
      },

      // ─── Trend Actions ───

      setTrends: (trends) => {
        set({ trends });
      },

      setTrendDirection: (direction) => {
        set({ trendDirection: direction });
      },

      // ─── Configuration Actions ───

      setSensitivity: (sensitivity) => {
        const sensitivityThresholds = {
          high: { criticalZScore: 2.0, warningZScore: 1.5, minPercentDev: 10 },
          medium: { criticalZScore: 2.5, warningZScore: 2.0, minPercentDev: 15 },
          low: { criticalZScore: 3.0, warningZScore: 2.5, minPercentDev: 25 },
        };

        const thresholds = sensitivityThresholds[sensitivity];

        set((state) => ({
          sensitivity,
          config: {
            ...state.config,
            criticalZScoreThreshold: thresholds.criticalZScore,
            warningZScoreThreshold: thresholds.warningZScore,
            minPercentDeviation: thresholds.minPercentDev,
          },
        }));
      },

      updateConfig: (config) => {
        set((state) => ({
          config: { ...state.config, ...config },
        }));
      },

      // ─── UI Actions ───

      setComputing: (computing) => {
        set({ isComputing: computing });
      },

      setPanelOpen: (open) => {
        set({ isPanelOpen: open });
      },

      setLastComputed: (timestamp) => {
        set({ lastComputed: timestamp });
      },

      // ─── Drill-Down Actions ───

      getDrillDownFilters: (anomalyId) => {
        const anomaly = get().anomalies.find((a) => a.id === anomalyId);
        return anomaly?.drillDownFilters || null;
      },

      // ─── Reset ───

      reset: () => {
        set({
          ...initialState,
          // Preserve user preferences
          sensitivity: get().sensitivity,
          config: get().config,
        });
      },
    }),
    {
      name: 'confit-predictive-insights',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Persist user preferences and acknowledgment state
        sensitivity: state.sensitivity,
        config: state.config,
        acknowledgedAnomalies: Array.from(state.acknowledgedAnomalies),
        dismissedAnomalies: Array.from(state.dismissedAnomalies),
        acknowledgedOpportunities: Array.from(state.acknowledgedOpportunities),
      }),
      merge: (persisted, current) => {
        // Merge persisted state with current state
        const persistedState = persisted as Partial<PredictiveInsightsState>;
        return {
          ...current,
          sensitivity: persistedState.sensitivity ?? current.sensitivity,
          config: persistedState.config ?? current.config,
          acknowledgedAnomalies: new Set(persistedState.acknowledgedAnomalies ?? []),
          dismissedAnomalies: new Set(persistedState.dismissedAnomalies ?? []),
          acknowledgedOpportunities: new Set(persistedState.acknowledgedOpportunities ?? []),
        };
      },
    }
  )
);

// ─── Convenience Hooks ────────────────────────────────────────────────

/**
 * Hook for accessing anomaly state and actions
 */
export function usePredictiveAnomalies() {
  const anomalies = usePredictiveInsightsStore((s) => s.anomalies);
  const acknowledgedAnomalies = usePredictiveInsightsStore((s) => s.acknowledgedAnomalies);
  const dismissedAnomalies = usePredictiveInsightsStore((s) => s.dismissedAnomalies);
  const setAnomalies = usePredictiveInsightsStore((s) => s.setAnomalies);
  const acknowledgeAnomaly = usePredictiveInsightsStore((s) => s.acknowledgeAnomaly);
  const dismissAnomaly = usePredictiveInsightsStore((s) => s.dismissAnomaly);
  const restoreAnomaly = usePredictiveInsightsStore((s) => s.restoreAnomaly);
  const getActiveAnomalies = usePredictiveInsightsStore((s) => s.getActiveAnomalies);
  const getAnomaliesBySeverity = usePredictiveInsightsStore((s) => s.getAnomaliesBySeverity);
  const getUnacknowledgedCount = usePredictiveInsightsStore((s) => s.getUnacknowledgedCount);

  return {
    anomalies,
    acknowledgedAnomalies,
    dismissedAnomalies,
    setAnomalies,
    acknowledgeAnomaly,
    dismissAnomaly,
    restoreAnomaly,
    getActiveAnomalies,
    getAnomaliesBySeverity,
    getUnacknowledgedCount,
  };
}

/**
 * Hook for accessing forecast state and actions
 */
export function usePredictiveForecasts() {
  const forecasts = usePredictiveInsightsStore((s) => s.forecasts);
  const lastForecastUpdate = usePredictiveInsightsStore((s) => s.lastForecastUpdate);
  const setForecasts = usePredictiveInsightsStore((s) => s.setForecasts);
  const getForecast = usePredictiveInsightsStore((s) => s.getForecast);

  return {
    forecasts,
    lastForecastUpdate,
    setForecasts,
    getForecast,
  };
}

/**
 * Hook for accessing trend state
 */
export function usePredictiveTrends() {
  const trends = usePredictiveInsightsStore((s) => s.trends);
  const trendDirection = usePredictiveInsightsStore((s) => s.trendDirection);
  const setTrends = usePredictiveInsightsStore((s) => s.setTrends);
  const setTrendDirection = usePredictiveInsightsStore((s) => s.setTrendDirection);

  return {
    trends,
    trendDirection,
    setTrends,
    setTrendDirection,
  };
}

/**
 * Hook for accessing configuration
 */
export function usePredictiveConfig() {
  const config = usePredictiveInsightsStore((s) => s.config);
  const sensitivity = usePredictiveInsightsStore((s) => s.sensitivity);
  const setSensitivity = usePredictiveInsightsStore((s) => s.setSensitivity);
  const updateConfig = usePredictiveInsightsStore((s) => s.updateConfig);

  return {
    config,
    sensitivity,
    setSensitivity,
    updateConfig,
  };
}

/**
 * Hook for panel state
 */
export function usePredictivePanel() {
  const isPanelOpen = usePredictiveInsightsStore((s) => s.isPanelOpen);
  const isComputing = usePredictiveInsightsStore((s) => s.isComputing);
  const lastComputed = usePredictiveInsightsStore((s) => s.lastComputed);
  const setPanelOpen = usePredictiveInsightsStore((s) => s.setPanelOpen);
  const setComputing = usePredictiveInsightsStore((s) => s.setComputing);
  const setLastComputed = usePredictiveInsightsStore((s) => s.setLastComputed);

  return {
    isPanelOpen,
    isComputing,
    lastComputed,
    setPanelOpen,
    setComputing,
    setLastComputed,
  };
}

export default usePredictiveInsightsStore;
