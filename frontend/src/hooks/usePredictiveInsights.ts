/**
 * CONFIT — Use Predictive Insights Hook
 * =======================================
 * Master hook that orchestrates anomaly detection and forecasting,
 * syncing results with the predictive insights store.
 *
 * Features:
 * - Combines anomaly detection and forecasting
 * - Syncs with predictive insights store
 * - Debounced recalculations for performance
 * - Drill-down filter integration
 */

import { useEffect, useMemo, useCallback, useRef } from 'react';
import { useSalesAnomalyDetection } from './useSalesAnomalyDetection';
import { useSalesForecasting } from './useSalesForecasting';
import { usePredictiveInsightsStore } from '@/stores/predictiveInsightsStore';
import { useSalesFilterStore } from '@/stores/salesFilterStore';
import type { SaleRecord } from '@/types/dashboard';
import type {
  DetectedAnomaly,
  RevenueForecast,
  ForecastHorizon,
  TrendDirection,
  AnomalyDrillDownFilters,
} from '@/types/predictiveInsightsTypes';

// ─── Hook Options ──────────────────────────────────────────────────────

export interface UsePredictiveInsightsOptions {
  /** Filtered sales data to analyze */
  data: SaleRecord[];
  /** Enable/disable predictive insights */
  enabled?: boolean;
  /** Sensitivity level */
  sensitivity?: 'high' | 'medium' | 'low';
  /** Debounce delay for recalculations (ms) */
  debounceMs?: number;
  /** Callback when anomalies are detected */
  onAnomaliesDetected?: (anomalies: DetectedAnomaly[]) => void;
  /** Callback when drill-down is triggered */
  onDrillDown?: (filters: AnomalyDrillDownFilters) => void;
}

export interface UsePredictiveInsightsReturn {
  // ─── Anomaly State ───
  anomalies: DetectedAnomaly[];
  unacknowledgedCount: number;
  criticalCount: number;
  warningCount: number;
  opportunityCount: number;

  // ─── Forecast State ───
  forecasts: Record<ForecastHorizon, RevenueForecast | null>;
  trendDirection: TrendDirection;

  // ─── Computation State ───
  isComputing: boolean;
  lastComputed: string | null;

  // ─── Actions ───
  acknowledgeAnomaly: (id: string) => void;
  dismissAnomaly: (id: string) => void;
  applyDrillDown: (filters: AnomalyDrillDownFilters) => void;
  setSensitivity: (sensitivity: 'high' | 'medium' | 'low') => void;
  recalculate: () => void;
}

// ─── Main Hook Implementation ──────────────────────────────────────────

export function usePredictiveInsights(
  options: UsePredictiveInsightsOptions
): UsePredictiveInsightsReturn {
  const {
    data,
    enabled = true,
    sensitivity = 'medium',
    debounceMs = 150,
    onAnomaliesDetected,
    onDrillDown,
  } = options;

  // ─── Store References ────────────────────────────────────────────────

  const store = usePredictiveInsightsStore((s) => ({
    setAnomalies: s.setAnomalies,
    acknowledgeAnomaly: s.acknowledgeAnomaly,
    dismissAnomaly: s.dismissAnomaly,
    setForecasts: s.setForecasts,
    setTrendDirection: s.setTrendDirection,
    setSensitivity: s.setSensitivity,
    setComputing: s.setComputing,
    setLastComputed: s.setLastComputed,
    sensitivity: s.sensitivity,
    lastComputed: s.lastComputed,
  }));

  // ─── Anomaly Detection ───────────────────────────────────────────────

  const anomalyDetection = useSalesAnomalyDetection({
    data,
    sensitivity: store.sensitivity,
    enabled,
    debounceMs,
    onAnomaliesDetected,
  });

  // ─── Forecasting ──────────────────────────────────────────────────────

  const forecasting = useSalesForecasting({
    data,
    enabled,
    horizons: ['7d', '14d', '30d'],
  });

  // ─── Sync to Store ────────────────────────────────────────────────────

  // Track previous values to avoid unnecessary updates
  const prevAnomaliesRef = useRef<DetectedAnomaly[]>([]);
  const prevForecastsRef = useRef<Record<ForecastHorizon, RevenueForecast | null>>({
    '7d': null,
    '14d': null,
    '30d': null,
  });

  // Sync anomalies to store
  useEffect(() => {
    if (!enabled) return;

    const currentIds = anomalyDetection.anomalies.map(a => a.id).join(',');
    const prevIds = prevAnomaliesRef.current.map(a => a.id).join(',');

    if (currentIds !== prevIds) {
      store.setAnomalies(anomalyDetection.anomalies);
      prevAnomaliesRef.current = anomalyDetection.anomalies;
    }
  }, [anomalyDetection.anomalies, enabled, store]);

  // Sync forecasts to store
  useEffect(() => {
    if (!enabled) return;

    const currentForecast = JSON.stringify(forecasting.forecasts);
    const prevForecast = JSON.stringify(prevForecastsRef.current);

    if (currentForecast !== prevForecast) {
      store.setForecasts(forecasting.forecasts);
      store.setTrendDirection(forecasting.trendDirection);
      prevForecastsRef.current = forecasting.forecasts;
    }
  }, [forecasting.forecasts, forecasting.trendDirection, enabled, store]);

  // Sync computing state
  useEffect(() => {
    store.setComputing(anomalyDetection.isDetecting);
  }, [anomalyDetection.isDetecting, store]);

  // Update last computed timestamp
  useEffect(() => {
    if (anomalyDetection.anomalies.length > 0 && !anomalyDetection.isDetecting) {
      store.setLastComputed(new Date().toISOString());
    }
  }, [anomalyDetection.anomalies, anomalyDetection.isDetecting, store]);

  // ─── Computed Stats ───────────────────────────────────────────────────

  const stats = useMemo(() => {
    const active = anomalyDetection.anomalies.filter(a => !a.dismissed);
    const unacknowledged = active.filter(a => !a.acknowledged);
    const critical = active.filter(a => a.severity === 'critical').length;
    const warning = active.filter(a => a.severity === 'warning').length;
    const opportunity = active.filter(a => a.severity === 'opportunity').length;

    return {
      total: active.length,
      unacknowledgedCount: unacknowledged.length,
      criticalCount: critical,
      warningCount: warning,
      opportunityCount: opportunity,
    };
  }, [anomalyDetection.anomalies]);

  // ─── Drill-Down Integration ───────────────────────────────────────────

  const applyDrillDown = useCallback(
    (filters: AnomalyDrillDownFilters) => {
      const salesStore = useSalesFilterStore.getState();

      // Apply filters to sales filter store
      if (filters.productName) {
        salesStore.setProductName(filters.productName);
      }
      if (filters.category) {
        salesStore.updateFilter('categories', [filters.category as any], 'widget');
      }
      if (filters.dateRange) {
        salesStore.updateFilter('dateRange', filters.dateRange, 'widget');
      }
      if (filters.marginRange) {
        salesStore.setMarginRange(filters.marginRange);
      }
      if (filters.returnStatuses && filters.returnStatuses.length > 0) {
        salesStore.setReturnStatuses(filters.returnStatuses as any);
      }

      // Call external handler
      onDrillDown?.(filters);
    },
    [onDrillDown]
  );

  // ─── Recalculate ──────────────────────────────────────────────────────

  const recalculate = useCallback(() => {
    anomalyDetection.recalculate();
  }, [anomalyDetection]);

  // ─── Set Sensitivity ──────────────────────────────────────────────────

  const handleSetSensitivity = useCallback(
    (newSensitivity: 'high' | 'medium' | 'low') => {
      store.setSensitivity(newSensitivity);
      // Recalculate will happen automatically due to sensitivity change
    },
    [store]
  );

  return {
    // Anomaly State
    anomalies: anomalyDetection.anomalies,
    unacknowledgedCount: stats.unacknowledgedCount,
    criticalCount: stats.criticalCount,
    warningCount: stats.warningCount,
    opportunityCount: stats.opportunityCount,

    // Forecast State
    forecasts: forecasting.forecasts,
    trendDirection: forecasting.trendDirection,

    // Computation State
    isComputing: anomalyDetection.isDetecting,
    lastComputed: store.lastComputed,

    // Actions
    acknowledgeAnomaly: store.acknowledgeAnomaly,
    dismissAnomaly: store.dismissAnomaly,
    applyDrillDown,
    setSensitivity: handleSetSensitivity,
    recalculate,
  };
}

export default usePredictiveInsights;
