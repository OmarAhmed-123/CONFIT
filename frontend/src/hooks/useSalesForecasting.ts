/**
 * CONFIT — Sales Forecasting Hook
 * =================================
 * Revenue and performance trend forecasting using time-series methods.
 * Provides short-term projections (7/14/30 days) with confidence intervals.
 *
 * Features:
 * - Exponential smoothing for trend forecasting
 * - Linear regression for trend direction
 * - Moving average for baseline smoothing
 * - Confidence interval calculation
 * - Trend detection and momentum analysis
 */

import { useMemo, useCallback } from 'react';
import { format, parseISO, addDays, eachDayOfInterval, startOfDay, endOfDay, differenceInDays } from 'date-fns';
import type { SaleRecord } from '@/types/dashboard';
import type {
  RevenueForecast,
  ForecastPoint,
  ForecastHorizon,
  TrendDirection,
  MetricTrend,
  AnomalyMetric,
} from '@/types/predictiveInsightsTypes';

// ─── Statistical Functions ─────────────────────────────────────────────

/**
 * Calculate mean of a numeric array
 */
function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/**
 * Calculate linear regression coefficients
 * Returns slope and intercept for y = mx + b
 */
function linearRegression(x: number[], y: number[]): { slope: number; intercept: number; r2: number } {
  const n = x.length;
  if (n < 2) return { slope: 0, intercept: 0, r2: 0 };

  const sumX = x.reduce((s, v) => s + v, 0);
  const sumY = y.reduce((s, v) => s + v, 0);
  const sumXY = x.reduce((s, v, i) => s + v * y[i], 0);
  const sumX2 = x.reduce((s, v) => s + v * v, 0);

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  // Calculate R-squared
  const yMean = sumY / n;
  const ssTotal = y.reduce((s, v) => s + Math.pow(v - yMean, 2), 0);
  const ssResidual = y.reduce((s, v, i) => s + Math.pow(v - (slope * x[i] + intercept), 2), 0);
  const r2 = ssTotal > 0 ? 1 - ssResidual / ssTotal : 0;

  return { slope, intercept, r2 };
}

/**
 * Exponential smoothing forecast
 * Uses Holt-Winters simple exponential smoothing
 */
function exponentialSmoothing(
  values: number[],
  horizon: number,
  alpha: number = 0.3
): { forecast: number[]; level: number } {
  if (values.length === 0) return { forecast: [], level: 0 };

  // Calculate initial level
  let level = values[0];

  // Smooth through historical data
  for (let i = 1; i < values.length; i++) {
    level = alpha * values[i] + (1 - alpha) * level;
  }

  // Forecast future values (flat forecast for simple exponential smoothing)
  const forecast = Array(horizon).fill(level);

  return { forecast, level };
}

/**
 * Double exponential smoothing (Holt method) for trend
 */
function doubleExponentialSmoothing(
  values: number[],
  horizon: number,
  alpha: number = 0.3,
  beta: number = 0.1
): { forecast: number[]; level: number; trend: number } {
  if (values.length < 2) return { forecast: Array(horizon).fill(values[0] || 0), level: values[0] || 0, trend: 0 };

  // Initialize
  let level = values[0];
  let trend = values[1] - values[0];

  // Smooth through historical data
  for (let i = 1; i < values.length; i++) {
    const prevLevel = level;
    level = alpha * values[i] + (1 - alpha) * (level + trend);
    trend = beta * (level - prevLevel) + (1 - beta) * trend;
  }

  // Forecast future values
  const forecast: number[] = [];
  for (let i = 0; i < horizon; i++) {
    forecast.push(level + (i + 1) * trend);
  }

  return { forecast, level, trend };
}

/**
 * Calculate confidence interval based on historical variance
 */
function calculateConfidenceInterval(
  forecast: number,
  historicalValues: number[],
  confidence: number = 0.95
): { lower: number; upper: number } {
  if (historicalValues.length < 2) {
    return { lower: forecast * 0.8, upper: forecast * 1.2 };
  }

  // Calculate standard deviation
  const avg = mean(historicalValues);
  const variance = historicalValues.reduce((s, v) => s + Math.pow(v - avg, 2), 0) / (historicalValues.length - 1);
  const stdDev = Math.sqrt(variance);

  // Z-score for confidence level (1.96 for 95%)
  const zScore = confidence === 0.95 ? 1.96 : confidence === 0.90 ? 1.645 : 1.15;

  // Widen interval for forecast horizon
  const margin = zScore * stdDev;

  return {
    lower: Math.max(0, forecast - margin),
    upper: forecast + margin,
  };
}

/**
 * Determine trend direction from slope
 */
function determineTrendDirection(slope: number, avgValue: number): TrendDirection {
  if (avgValue === 0) return 'stable';

  const percentSlope = (slope / avgValue) * 100;

  if (Math.abs(percentSlope) < 2) return 'stable';
  return slope > 0 ? 'up' : 'down';
}

/**
 * Calculate moving average
 */
function movingAverage(values: number[], window: number): number[] {
  if (values.length < window) return values;

  const result: number[] = [];
  for (let i = window - 1; i < values.length; i++) {
    const windowValues = values.slice(i - window + 1, i + 1);
    result.push(mean(windowValues));
  }

  return result;
}

// ─── Revenue Calculation Helpers ───────────────────────────────────────

/**
 * Calculate daily revenue from sales data
 */
function calculateDailyRevenue(data: SaleRecord[]): Map<string, number> {
  const revenueByDate = new Map<string, number>();

  data.forEach(record => {
    const dateKey = record.saleDate.split('T')[0];
    const current = revenueByDate.get(dateKey) || 0;
    revenueByDate.set(dateKey, current + record.price * record.quantity);
  });

  return revenueByDate;
}

/**
 * Fill missing dates with zero revenue
 */
function fillMissingDates(
  revenueByDate: Map<string, number>,
  startDate: Date,
  endDate: Date
): { date: string; revenue: number }[] {
  const days = eachDayOfInterval({ start: startDate, end: endDate });

  return days.map(day => ({
    date: format(day, 'yyyy-MM-dd'),
    revenue: revenueByDate.get(format(day, 'yyyy-MM-dd')) || 0,
  }));
}

// ─── Hook Options ──────────────────────────────────────────────────────

export interface UseSalesForecastingOptions {
  /** Filtered sales data to analyze */
  data: SaleRecord[];
  /** Forecast horizons to compute */
  horizons?: ForecastHorizon[];
  /** Enable/disable forecasting */
  enabled?: boolean;
  /** Smoothing factor (0-1) */
  alpha?: number;
  /** Trend smoothing factor (0-1) */
  beta?: number;
  /** Moving average window size */
  movingAverageWindow?: number;
}

export interface UseSalesForecastingReturn {
  /** Revenue forecasts by horizon */
  forecasts: Record<ForecastHorizon, RevenueForecast | null>;
  /** Current trend direction */
  trendDirection: TrendDirection;
  /** Trend metrics */
  trends: MetricTrend[];
  /** Whether forecasting is in progress */
  isForecasting: boolean;
  /** Get forecast for specific horizon */
  getForecast: (horizon: ForecastHorizon) => RevenueForecast | null;
}

// ─── Horizon Configuration ─────────────────────────────────────────────

const HORIZON_DAYS: Record<ForecastHorizon, number> = {
  '7d': 7,
  '14d': 14,
  '30d': 30,
};

// ─── Main Hook Implementation ──────────────────────────────────────────

export function useSalesForecasting(
  options: UseSalesForecastingOptions
): UseSalesForecastingReturn {
  const {
    data,
    horizons = ['7d', '14d', '30d'],
    enabled = true,
    alpha = 0.3,
    beta = 0.1,
    movingAverageWindow = 7,
  } = options;

  // ─── Historical Data Preparation ─────────────────────────────────────

  const historicalData = useMemo(() => {
    if (!enabled || data.length === 0) return null;

    // Get date range
    const dates = data.map(d => parseISO(d.saleDate));
    const minDate = startOfDay(new Date(Math.min(...dates.map(d => d.getTime()))));
    const maxDate = endOfDay(new Date(Math.max(...dates.map(d => d.getTime()))));

    // Calculate daily revenue
    const revenueByDate = calculateDailyRevenue(data);

    // Fill missing dates
    const dailyRevenue = fillMissingDates(revenueByDate, minDate, maxDate);

    // Calculate moving average for smoothing
    const revenues = dailyRevenue.map(d => d.revenue);
    const smoothedRevenues = movingAverage(revenues, movingAverageWindow);

    return {
      dailyRevenue,
      revenues,
      smoothedRevenues,
      minDate,
      maxDate,
      totalDays: differenceInDays(maxDate, minDate) + 1,
    };
  }, [data, enabled, movingAverageWindow]);

  // ─── Forecast Calculation ─────────────────────────────────────────────

  const forecasts = useMemo<Record<ForecastHorizon, RevenueForecast | null>>(() => {
    const result: Record<ForecastHorizon, RevenueForecast | null> = {
      '7d': null,
      '14d': null,
      '30d': null,
    };

    if (!enabled || !historicalData || historicalData.revenues.length < 7) {
      return result;
    }

    const { revenues, smoothedRevenues, maxDate } = historicalData;
    const now = new Date().toISOString();

    // Use smoothed revenues for forecasting
    const valuesToUse = smoothedRevenues.length > 0 ? smoothedRevenues : revenues;

    horizons.forEach(horizon => {
      const days = HORIZON_DAYS[horizon];

      // Calculate double exponential smoothing forecast
      const { forecast, level, trend } = doubleExponentialSmoothing(
        valuesToUse,
        days,
        alpha,
        beta
      );

      // Calculate linear regression for trend analysis
      const x = valuesToUse.map((_, i) => i);
      const { slope, intercept, r2 } = linearRegression(x, valuesToUse);

      // Generate forecast points with confidence intervals
      const points: ForecastPoint[] = forecast.map((value, i) => {
        const date = format(addDays(maxDate, i + 1), 'yyyy-MM-dd');
        const ci = calculateConfidenceInterval(value, valuesToUse);

        // Confidence decreases with distance
        const horizonConfidence = Math.max(0.5, r2 * (1 - (i / (days * 2))));

        return {
          date,
          predicted: Math.max(0, value),
          lowerBound: Math.max(0, ci.lower),
          upperBound: ci.upper,
          confidence: horizonConfidence,
        };
      });

      // Calculate total predicted revenue
      const totalPredicted = forecast.reduce((sum, v) => sum + Math.max(0, v), 0);

      // Determine trend direction
      const trendDirection = determineTrendDirection(trend, level);

      result[horizon] = {
        horizon,
        points,
        totalPredicted,
        trend: trendDirection,
        confidence: r2,
        method: 'exponential_smoothing',
        computedAt: now,
      };
    });

    return result;
  }, [enabled, historicalData, horizons, alpha, beta]);

  // ─── Trend Analysis ───────────────────────────────────────────────────

  const trends = useMemo<MetricTrend[]>(() => {
    if (!enabled || !historicalData || historicalData.revenues.length < 7) {
      return [];
    }

    const { revenues, smoothedRevenues } = historicalData;
    const valuesToUse = smoothedRevenues.length > 0 ? smoothedRevenues : revenues;

    // Revenue trend
    const x = valuesToUse.map((_, i) => i);
    const { slope, r2 } = linearRegression(x, valuesToUse);
    const avgRevenue = mean(valuesToUse);

    const revenueTrend: MetricTrend = {
      metric: 'revenue',
      direction: determineTrendDirection(slope, avgRevenue),
      rateOfChange: avgRevenue > 0 ? (slope / avgRevenue) * 100 : 0,
      confidence: r2,
      sampleSize: valuesToUse.length,
    };

    // Margin trend
    const margins = data.map(r => r.profitMargin);
    const avgMargin = mean(margins);
    const { slope: marginSlope, r2: marginR2 } = linearRegression(
      margins.slice(-Math.min(30, margins.length)).map((_, i) => i),
      margins.slice(-Math.min(30, margins.length))
    );

    const marginTrend: MetricTrend = {
      metric: 'profit_margin',
      direction: determineTrendDirection(marginSlope, avgMargin),
      rateOfChange: avgMargin > 0 ? (marginSlope / avgMargin) * 100 : 0,
      confidence: marginR2,
      sampleSize: margins.length,
    };

    // Velocity trend
    const dailyQuantities = new Map<string, number>();
    data.forEach(record => {
      const dateKey = record.saleDate.split('T')[0];
      const current = dailyQuantities.get(dateKey) || 0;
      dailyQuantities.set(dateKey, current + record.quantity);
    });
    const quantities = Array.from(dailyQuantities.values());
    const avgQuantity = mean(quantities);
    const { slope: quantitySlope, r2: quantityR2 } = linearRegression(
      quantities.map((_, i) => i),
      quantities
    );

    const velocityTrend: MetricTrend = {
      metric: 'sales_velocity',
      direction: determineTrendDirection(quantitySlope, avgQuantity),
      rateOfChange: avgQuantity > 0 ? (quantitySlope / avgQuantity) * 100 : 0,
      confidence: quantityR2,
      sampleSize: quantities.length,
    };

    return [revenueTrend, marginTrend, velocityTrend];
  }, [enabled, historicalData, data]);

  // ─── Overall Trend Direction ─────────────────────────────────────────

  const trendDirection = useMemo<TrendDirection>(() => {
    const revenueTrend = trends.find(t => t.metric === 'revenue');
    if (!revenueTrend) return 'stable';

    // Weight by confidence
    const weightedTrends = trends.filter(t => t.metric === 'revenue' || t.metric === 'sales_velocity');

    if (weightedTrends.length === 0) return 'stable';

    const avgRate = mean(weightedTrends.map(t => t.rateOfChange * t.confidence));

    if (Math.abs(avgRate) < 2) return 'stable';
    return avgRate > 0 ? 'up' : 'down';
  }, [trends]);

  // ─── Helper Functions ────────────────────────────────────────────────

  const getForecast = useCallback((horizon: ForecastHorizon): RevenueForecast | null => {
    return forecasts[horizon];
  }, [forecasts]);

  return {
    forecasts,
    trendDirection,
    trends,
    isForecasting: false, // Always synchronous for now
    getForecast,
  };
}

export default useSalesForecasting;
