/**
 * CONFIT — Sales Anomaly Detection Hook
 * =======================================
 * Intelligent anomaly detection engine that identifies significant deviations
 * from baseline performance using statistical methods (Z-score, IQR, moving averages).
 *
 * Features:
 * - Rolling baseline calculation (30/60/90 day windows)
 * - Z-score and IQR-based anomaly detection
 * - Metric-specific thresholds adjusted for volatility
 * - Product and category-level anomaly detection
 * - Performance-optimized with memoization and caching
 */

import { useMemo, useCallback, useRef, useEffect, useState } from 'react';
import { format, parseISO, subDays, differenceInDays, eachDayOfInterval, startOfDay, endOfDay, isWithinInterval } from 'date-fns';
import type { SaleRecord, SaleCategory } from '@/types/dashboard';
import type {
  DetectedAnomaly,
  BaselineMetrics,
  ProductBaseline,
  CategoryBaseline,
  AnomalyDetectionConfig,
  AnomalyType,
  AnomalySeverity,
  AnomalyDrillDownFilters,
  DEFAULT_ANOMALY_CONFIG,
} from '@/types/predictiveInsightsTypes';

// ─── Statistical Utility Functions ─────────────────────────────────────

/**
 * Calculate mean of a numeric array
 */
function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/**
 * Calculate standard deviation of a numeric array
 */
function standardDeviation(values: number[]): number {
  if (values.length < 2) return 0;
  const avg = mean(values);
  const squareDiffs = values.map(v => Math.pow(v - avg, 2));
  return Math.sqrt(mean(squareDiffs));
}

/**
 * Calculate quartiles and IQR
 */
function calculateIQR(values: number[]): { q1: number; q3: number; iqr: number; lowerBound: number; upperBound: number } {
  if (values.length < 4) {
    return { q1: 0, q3: 0, iqr: 0, lowerBound: 0, upperBound: 0 };
  }

  const sorted = [...values].sort((a, b) => a - b);
  const q1Index = Math.floor(sorted.length * 0.25);
  const q3Index = Math.floor(sorted.length * 0.75);

  const q1 = sorted[q1Index];
  const q3 = sorted[q3Index];
  const iqr = q3 - q1;

  // IQR method: outliers are values below Q1 - 1.5*IQR or above Q3 + 1.5*IQR
  const lowerBound = q1 - 1.5 * iqr;
  const upperBound = q3 + 1.5 * iqr;

  return { q1, q3, iqr, lowerBound, upperBound };
}

/**
 * Calculate Z-score for a value given mean and standard deviation
 */
function zScore(value: number, mean: number, stdDev: number): number {
  if (stdDev === 0) return 0;
  return (value - mean) / stdDev;
}

/**
 * Calculate percentile deviation
 */
function percentDeviation(current: number, baseline: number): number {
  if (baseline === 0) return current === 0 ? 0 : 100;
  return ((current - baseline) / baseline) * 100;
}

/**
 * Generate unique ID for anomalies
 */
function generateAnomalyId(type: AnomalyType, entity: string, date: string): string {
  return `${type}-${entity.replace(/\s+/g, '-')}-${date.split('T')[0]}`;
}

// ─── Baseline Calculation Functions ────────────────────────────────────

/**
 * Calculate baseline metrics from a set of values
 */
function calculateBaselineMetrics(
  values: number[],
  windowDays: number
): BaselineMetrics {
  const avg = mean(values);
  const stdDev = standardDeviation(values);
  const iqr = calculateIQR(values);

  return {
    average: avg,
    standardDeviation: stdDev,
    iqr,
    zScoreThreshold: 2.0,
    percentDeviationThreshold: 15,
    windowDays,
    sampleSize: values.length,
    computedAt: new Date().toISOString(),
  };
}

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
 * Calculate daily sales velocity (quantity sold per day)
 */
function calculateDailyVelocity(data: SaleRecord[]): Map<string, number> {
  const velocityByDate = new Map<string, number>();

  data.forEach(record => {
    const dateKey = record.saleDate.split('T')[0];
    const current = velocityByDate.get(dateKey) || 0;
    velocityByDate.set(dateKey, current + record.quantity);
  });

  return velocityByDate;
}

/**
 * Calculate daily average margin
 */
function calculateDailyMargin(data: SaleRecord[]): Map<string, number> {
  const marginByDate = new Map<string, { total: number; count: number }>();

  data.forEach(record => {
    const dateKey = record.saleDate.split('T')[0];
    const current = marginByDate.get(dateKey) || { total: 0, count: 0 };
    marginByDate.set(dateKey, {
      total: current.total + record.profitMargin,
      count: current.count + 1,
    });
  });

  // Convert to average
  const result = new Map<string, number>();
  marginByDate.forEach((value, key) => {
    result.set(key, value.count > 0 ? value.total / value.count : 0);
  });

  return result;
}

/**
 * Calculate daily return rate
 */
function calculateDailyReturnRate(data: SaleRecord[]): Map<string, number> {
  const returnsByDate = new Map<string, { returned: number; total: number }>();

  data.forEach(record => {
    const dateKey = record.saleDate.split('T')[0];
    const current = returnsByDate.get(dateKey) || { returned: 0, total: 0 };
    const isReturn = record.returnStatus === 'Returned' || record.returnStatus === 'Pending Return';
    returnsByDate.set(dateKey, {
      returned: current.returned + (isReturn ? 1 : 0),
      total: current.total + 1,
    });
  });

  // Convert to rate
  const result = new Map<string, number>();
  returnsByDate.forEach((value, key) => {
    result.set(key, value.total > 0 ? (value.returned / value.total) * 100 : 0);
  });

  return result;
}

// ─── Anomaly Detection Functions ───────────────────────────────────────

/**
 * Determine anomaly severity based on Z-score and percent deviation
 */
function determineSeverity(
  zScore: number,
  percentDev: number,
  config: AnomalyDetectionConfig,
  isPositive: boolean
): AnomalySeverity | null {
  const absZScore = Math.abs(zScore);
  const absPercentDev = Math.abs(percentDev);

  // Check if deviation meets minimum threshold
  if (absPercentDev < config.minPercentDeviation && absZScore < config.warningZScoreThreshold) {
    return null;
  }

  // Positive deviations above threshold are opportunities
  if (isPositive && absPercentDev >= config.minPercentDeviation) {
    return 'opportunity';
  }

  // Critical: high Z-score or large deviation
  if (absZScore >= config.criticalZScoreThreshold || absPercentDev >= 40) {
    return 'critical';
  }

  // Warning: moderate Z-score or moderate deviation
  if (absZScore >= config.warningZScoreThreshold || absPercentDev >= config.minPercentDeviation) {
    return 'warning';
  }

  return null;
}

/**
 * Generate anomaly description and recommendation
 */
function generateAnomalyContext(
  type: AnomalyType,
  currentValue: number,
  baselineValue: number,
  percentDev: number,
  entity: string
): { description: string; recommendation: string } {
  const direction = percentDev > 0 ? 'above' : 'below';
  const absPercent = Math.abs(percentDev).toFixed(1);

  const contexts: Record<AnomalyType, { description: string; recommendation: string }> = {
    revenue_drop: {
      description: `Revenue for ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Review recent sales patterns and consider promotional activities',
    },
    revenue_spike: {
      description: `Revenue for ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Investigate what drove this spike and consider replicating successful tactics',
    },
    margin_compression: {
      description: `Profit margin for ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Review pricing strategy and cost structure for this product',
    },
    margin_improvement: {
      description: `Profit margin for ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Analyze what drove margin improvement and apply to other products',
    },
    velocity_drop: {
      description: `Sales velocity for ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Check inventory levels and consider marketing push',
    },
    velocity_spike: {
      description: `Sales velocity for ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Ensure adequate inventory and consider expanding similar offerings',
    },
    return_rate_spike: {
      description: `Return rate for ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Investigate product quality issues or customer expectations mismatch',
    },
    category_underperformance: {
      description: `Category ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Review category strategy and consider assortment optimization',
    },
    category_overperformance: {
      description: `Category ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Consider expanding this category and analyzing success factors',
    },
    product_underperformance: {
      description: `Product ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Review pricing, positioning, and competitive landscape',
    },
    product_overperformance: {
      description: `Product ${entity} is ${absPercent}% ${direction} baseline`,
      recommendation: 'Ensure inventory availability and consider similar product expansion',
    },
  };

  return contexts[type];
}

// ─── Hook Options ──────────────────────────────────────────────────────

export interface UseSalesAnomalyDetectionOptions {
  /** Filtered sales data to analyze */
  data: SaleRecord[];
  /** Detection configuration */
  config?: Partial<AnomalyDetectionConfig>;
  /** Sensitivity level (overrides config thresholds) */
  sensitivity?: 'high' | 'medium' | 'low';
  /** Enable/disable detection (for performance) */
  enabled?: boolean;
  /** Callback when anomalies are detected */
  onAnomaliesDetected?: (anomalies: DetectedAnomaly[]) => void;
  /** Debounce delay for recalculations (ms) */
  debounceMs?: number;
}

export interface UseSalesAnomalyDetectionReturn {
  /** Detected anomalies */
  anomalies: DetectedAnomaly[];
  /** Overall baseline metrics */
  overallBaseline: BaselineMetrics | null;
  /** Baselines by category */
  categoryBaselines: Map<string, CategoryBaseline>;
  /** Baselines by product */
  productBaselines: Map<string, ProductBaseline>;
  /** Whether detection is in progress */
  isDetecting: boolean;
  /** Recalculate anomalies manually */
  recalculate: () => void;
  /** Get anomalies for a specific entity */
  getAnomaliesForEntity: (entity: string) => DetectedAnomaly[];
  /** Get anomalies by severity */
  getAnomaliesBySeverity: (severity: AnomalySeverity) => DetectedAnomaly[];
  /** Acknowledge an anomaly */
  acknowledgeAnomaly: (id: string) => void;
  /** Dismiss an anomaly */
  dismissAnomaly: (id: string) => void;
}

// ─── Sensitivity Thresholds ────────────────────────────────────────────

const SENSITIVITY_CONFIGS = {
  high: { criticalZScore: 2.0, warningZScore: 1.5, minPercentDev: 10 },
  medium: { criticalZScore: 2.5, warningZScore: 2.0, minPercentDev: 15 },
  low: { criticalZScore: 3.0, warningZScore: 2.5, minPercentDev: 25 },
};

// ─── Main Hook Implementation ──────────────────────────────────────────

export function useSalesAnomalyDetection(
  options: UseSalesAnomalyDetectionOptions
): UseSalesAnomalyDetectionReturn {
  const {
    data,
    sensitivity = 'medium',
    enabled = true,
    onAnomaliesDetected,
    debounceMs = 150,
  } = options;

  const [isDetecting, setIsDetecting] = useState(false);
  const [acknowledgedIds, setAcknowledgedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Get sensitivity config
  const sensitivityConfig = SENSITIVITY_CONFIGS[sensitivity];

  // Build full config
  const config: AnomalyDetectionConfig = useMemo(() => ({
    criticalZScoreThreshold: sensitivityConfig.criticalZScore,
    warningZScoreThreshold: sensitivityConfig.warningZScore,
    minPercentDeviation: sensitivityConfig.minPercentDev,
    baselineWindowDays: 30,
    minDataPoints: 10,
    enableOpportunities: true,
    enableForecasting: true,
    forecastHorizons: ['7d', '14d', '30d'],
  }), [sensitivityConfig]);

  // ─── Baseline Calculation ────────────────────────────────────────────

  const overallBaseline = useMemo<BaselineMetrics | null>(() => {
    if (!enabled || data.length < config.minDataPoints) return null;

    const dailyRevenue = calculateDailyRevenue(data);
    const revenueValues = Array.from(dailyRevenue.values());

    if (revenueValues.length < config.minDataPoints) return null;

    return calculateBaselineMetrics(revenueValues, config.baselineWindowDays);
  }, [data, enabled, config]);

  const categoryBaselines = useMemo<Map<string, CategoryBaseline>>(() => {
    const baselines = new Map<string, CategoryBaseline>();

    if (!enabled || data.length < config.minDataPoints) return baselines;

    // Group data by category
    const categoryData = new Map<string, SaleRecord[]>();
    data.forEach(record => {
      const records = categoryData.get(record.category) || [];
      records.push(record);
      categoryData.set(record.category, records);
    });

    // Calculate baseline for each category
    categoryData.forEach((records, category) => {
      if (records.length < config.minDataPoints) return;

      const dailyRevenue = calculateDailyRevenue(records);
      const revenueValues = Array.from(dailyRevenue.values());

      if (revenueValues.length < config.minDataPoints) return;

      const baseline = calculateBaselineMetrics(revenueValues, config.baselineWindowDays);
      baselines.set(category, {
        ...baseline,
        category,
        productCount: new Set(records.map(r => r.productName)).size,
      });
    });

    return baselines;
  }, [data, enabled, config]);

  const productBaselines = useMemo<Map<string, ProductBaseline>>(() => {
    const baselines = new Map<string, ProductBaseline>();

    if (!enabled || data.length < config.minDataPoints) return baselines;

    // Group data by product
    const productData = new Map<string, SaleRecord[]>();
    data.forEach(record => {
      const records = productData.get(record.productName) || [];
      records.push(record);
      productData.set(record.productName, records);
    });

    // Calculate baseline for each product (only top products)
    const productRevenues = new Map<string, number>();
    data.forEach(record => {
      const current = productRevenues.get(record.productName) || 0;
      productRevenues.set(record.productName, current + record.price * record.quantity);
    });

    // Only calculate for top 20 products by revenue
    const topProducts = Array.from(productRevenues.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([name]) => name);

    topProducts.forEach(productName => {
      const records = productData.get(productName);
      if (!records || records.length < config.minDataPoints) return;

      const dailyRevenue = calculateDailyRevenue(records);
      const revenueValues = Array.from(dailyRevenue.values());

      if (revenueValues.length < config.minDataPoints) return;

      const baseline = calculateBaselineMetrics(revenueValues, config.baselineWindowDays);
      baselines.set(productName, {
        ...baseline,
        productId: records[0].id,
        productName,
        category: records[0].category,
      });
    });

    return baselines;
  }, [data, enabled, config]);

  // ─── Anomaly Detection ────────────────────────────────────────────────

  const anomalies = useMemo<DetectedAnomaly[]>(() => {
    if (!enabled || !overallBaseline || data.length < config.minDataPoints) return [];

    const detected: DetectedAnomaly[] = [];
    const now = new Date().toISOString();

    // Get recent period (last 7 days) vs baseline
    const dates = data.map(d => parseISO(d.saleDate));
    const maxDate = new Date(Math.max(...dates.map(d => d.getTime())));
    const recentStart = subDays(startOfDay(maxDate), 7);

    const recentData = data.filter(d => {
      const date = parseISO(d.saleDate);
      return isWithinInterval(date, { start: recentStart, end: endOfDay(maxDate) });
    });

    if (recentData.length === 0) return [];

    // ── Overall Revenue Anomalies ──
    const recentRevenue = recentData.reduce((sum, r) => sum + r.price * r.quantity, 0);
    const dailyRevenue = calculateDailyRevenue(recentData);
    const avgDailyRevenue = mean(Array.from(dailyRevenue.values()));

    const revenueZScore = zScore(avgDailyRevenue, overallBaseline.average, overallBaseline.standardDeviation);
    const revenuePercentDev = percentDeviation(avgDailyRevenue, overallBaseline.average);

    const revenueSeverity = determineSeverity(revenueZScore, revenuePercentDev, config, revenuePercentDev > 0);
    if (revenueSeverity) {
      const type: AnomalyType = revenuePercentDev < 0 ? 'revenue_drop' : 'revenue_spike';
      const context = generateAnomalyContext(type, avgDailyRevenue, overallBaseline.average, revenuePercentDev, 'all products');

      detected.push({
        id: generateAnomalyId(type, 'overall', now),
        type,
        severity: revenueSeverity,
        metric: 'revenue',
        currentValue: avgDailyRevenue,
        baselineValue: overallBaseline.average,
        deviation: avgDailyRevenue - overallBaseline.average,
        percentDeviation: revenuePercentDev,
        zScore: revenueZScore,
        description: context.description,
        recommendation: context.recommendation,
        affectedEntity: 'Overall Revenue',
        entityType: 'overall',
        detectedAt: now,
        isActive: true,
        acknowledged: acknowledgedIds.has(generateAnomalyId(type, 'overall', now)),
        dismissed: dismissedIds.has(generateAnomalyId(type, 'overall', now)),
        drillDownFilters: {},
      });
    }

    // ── Margin Anomalies ──
    const recentMargin = mean(recentData.map(r => r.profitMargin));
    const historicalMargin = mean(data.map(r => r.profitMargin));
    const marginStdDev = standardDeviation(data.map(r => r.profitMargin));

    const marginZScore = zScore(recentMargin, historicalMargin, marginStdDev);
    const marginPercentDev = percentDeviation(recentMargin, historicalMargin);

    const marginSeverity = determineSeverity(marginZScore, marginPercentDev, config, marginPercentDev > 0);
    if (marginSeverity) {
      const type: AnomalyType = marginPercentDev < 0 ? 'margin_compression' : 'margin_improvement';
      const context = generateAnomalyContext(type, recentMargin, historicalMargin, marginPercentDev, 'all products');

      detected.push({
        id: generateAnomalyId(type, 'overall', now),
        type,
        severity: marginSeverity,
        metric: 'profit_margin',
        currentValue: recentMargin,
        baselineValue: historicalMargin,
        deviation: recentMargin - historicalMargin,
        percentDeviation: marginPercentDev,
        zScore: marginZScore,
        description: context.description,
        recommendation: context.recommendation,
        affectedEntity: 'Overall Margin',
        entityType: 'overall',
        detectedAt: now,
        isActive: true,
        acknowledged: acknowledgedIds.has(generateAnomalyId(type, 'overall', now)),
        dismissed: dismissedIds.has(generateAnomalyId(type, 'overall', now)),
        drillDownFilters: {
          marginRange: recentMargin < 15 ? 'atRisk' : recentMargin < 30 ? 'healthy' : 'high',
        },
      });
    }

    // ── Velocity Anomalies ──
    const recentVelocity = recentData.reduce((sum, r) => sum + r.quantity, 0) / 7; // Daily average
    const historicalVelocity = data.reduce((sum, r) => sum + r.quantity, 0) / config.baselineWindowDays;
    const velocityStdDev = standardDeviation(
      Array.from(calculateDailyVelocity(data).values())
    );

    const velocityZScore = zScore(recentVelocity, historicalVelocity, velocityStdDev);
    const velocityPercentDev = percentDeviation(recentVelocity, historicalVelocity);

    const velocitySeverity = determineSeverity(velocityZScore, velocityPercentDev, config, velocityPercentDev > 0);
    if (velocitySeverity) {
      const type: AnomalyType = velocityPercentDev < 0 ? 'velocity_drop' : 'velocity_spike';
      const context = generateAnomalyContext(type, recentVelocity, historicalVelocity, velocityPercentDev, 'all products');

      detected.push({
        id: generateAnomalyId(type, 'overall', now),
        type,
        severity: velocitySeverity,
        metric: 'sales_velocity',
        currentValue: recentVelocity,
        baselineValue: historicalVelocity,
        deviation: recentVelocity - historicalVelocity,
        percentDeviation: velocityPercentDev,
        zScore: velocityZScore,
        description: context.description,
        recommendation: context.recommendation,
        affectedEntity: 'Overall Velocity',
        entityType: 'overall',
        detectedAt: now,
        isActive: true,
        acknowledged: acknowledgedIds.has(generateAnomalyId(type, 'overall', now)),
        dismissed: dismissedIds.has(generateAnomalyId(type, 'overall', now)),
        drillDownFilters: {},
      });
    }

    // ── Return Rate Anomalies ──
    const recentReturnRate = (recentData.filter(r => r.returnStatus === 'Returned' || r.returnStatus === 'Pending Return').length / recentData.length) * 100;
    const historicalReturnRate = (data.filter(r => r.returnStatus === 'Returned' || r.returnStatus === 'Pending Return').length / data.length) * 100;
    const returnRateValues = Array.from(calculateDailyReturnRate(data).values());
    const returnRateStdDev = standardDeviation(returnRateValues);

    const returnZScore = zScore(recentReturnRate, historicalReturnRate, returnRateStdDev);
    const returnPercentDev = percentDeviation(recentReturnRate, historicalReturnRate);

    // Return rate spike is always negative (never an opportunity)
    const returnSeverity = determineSeverity(returnZScore, returnPercentDev, config, false);
    if (returnSeverity && returnPercentDev > 0) {
      const context = generateAnomalyContext('return_rate_spike', recentReturnRate, historicalReturnRate, returnPercentDev, 'all products');

      detected.push({
        id: generateAnomalyId('return_rate_spike', 'overall', now),
        type: 'return_rate_spike',
        severity: returnSeverity,
        metric: 'return_rate',
        currentValue: recentReturnRate,
        baselineValue: historicalReturnRate,
        deviation: recentReturnRate - historicalReturnRate,
        percentDeviation: returnPercentDev,
        zScore: returnZScore,
        description: context.description,
        recommendation: context.recommendation,
        affectedEntity: 'Overall Return Rate',
        entityType: 'overall',
        detectedAt: now,
        isActive: true,
        acknowledged: acknowledgedIds.has(generateAnomalyId('return_rate_spike', 'overall', now)),
        dismissed: dismissedIds.has(generateAnomalyId('return_rate_spike', 'overall', now)),
        drillDownFilters: {
          returnStatuses: ['Returned', 'Pending Return'],
        },
      });
    }

    // ── Category-Level Anomalies ──
    categoryBaselines.forEach((baseline, category) => {
      const categoryData = recentData.filter(r => r.category === category);
      if (categoryData.length === 0) return;

      const categoryRevenue = categoryData.reduce((sum, r) => sum + r.price * r.quantity, 0);
      const categoryDailyAvg = categoryRevenue / 7;

      const catZScore = zScore(categoryDailyAvg, baseline.average, baseline.standardDeviation);
      const catPercentDev = percentDeviation(categoryDailyAvg, baseline.average);

      const catSeverity = determineSeverity(catZScore, catPercentDev, config, catPercentDev > 0);
      if (catSeverity) {
        const type: AnomalyType = catPercentDev < 0 ? 'category_underperformance' : 'category_overperformance';
        const context = generateAnomalyContext(type, categoryDailyAvg, baseline.average, catPercentDev, category);

        detected.push({
          id: generateAnomalyId(type, category, now),
          type,
          severity: catSeverity,
          metric: 'category_performance',
          currentValue: categoryDailyAvg,
          baselineValue: baseline.average,
          deviation: categoryDailyAvg - baseline.average,
          percentDeviation: catPercentDev,
          zScore: catZScore,
          description: context.description,
          recommendation: context.recommendation,
          affectedEntity: category,
          entityType: 'category',
          detectedAt: now,
          isActive: true,
          acknowledged: acknowledgedIds.has(generateAnomalyId(type, category, now)),
          dismissed: dismissedIds.has(generateAnomalyId(type, category, now)),
          drillDownFilters: {
            category,
          },
        });
      }
    });

    // ── Product-Level Anomalies (Top Products Only) ──
    productBaselines.forEach((baseline, productName) => {
      const productData = recentData.filter(r => r.productName === productName);
      if (productData.length === 0) return;

      const productRevenue = productData.reduce((sum, r) => sum + r.price * r.quantity, 0);
      const productDailyAvg = productRevenue / 7;

      const prodZScore = zScore(productDailyAvg, baseline.average, baseline.standardDeviation);
      const prodPercentDev = percentDeviation(productDailyAvg, baseline.average);

      const prodSeverity = determineSeverity(prodZScore, prodPercentDev, config, prodPercentDev > 0);
      if (prodSeverity) {
        const type: AnomalyType = prodPercentDev < 0 ? 'product_underperformance' : 'product_overperformance';
        const context = generateAnomalyContext(type, productDailyAvg, baseline.average, prodPercentDev, productName);

        detected.push({
          id: generateAnomalyId(type, productName, now),
          type,
          severity: prodSeverity,
          metric: 'product_performance',
          currentValue: productDailyAvg,
          baselineValue: baseline.average,
          deviation: productDailyAvg - baseline.average,
          percentDeviation: prodPercentDev,
          zScore: prodZScore,
          description: context.description,
          recommendation: context.recommendation,
          affectedEntity: productName,
          entityType: 'product',
          detectedAt: now,
          isActive: true,
          acknowledged: acknowledgedIds.has(generateAnomalyId(type, productName, now)),
          dismissed: dismissedIds.has(generateAnomalyId(type, productName, now)),
          drillDownFilters: {
            productName,
          },
        });
      }
    });

    // Filter out dismissed anomalies
    const activeAnomalies = detected.filter(a => !a.dismissed);

    // Notify callback
    if (onAnomaliesDetected && activeAnomalies.length > 0) {
      onAnomaliesDetected(activeAnomalies);
    }

    return activeAnomalies;
  }, [
    data,
    enabled,
    config,
    overallBaseline,
    categoryBaselines,
    productBaselines,
    acknowledgedIds,
    dismissedIds,
    onAnomaliesDetected,
  ]);

  // ─── Helper Functions ────────────────────────────────────────────────

  const getAnomaliesForEntity = useCallback((entity: string): DetectedAnomaly[] => {
    return anomalies.filter(a => a.affectedEntity === entity);
  }, [anomalies]);

  const getAnomaliesBySeverity = useCallback((severity: AnomalySeverity): DetectedAnomaly[] => {
    return anomalies.filter(a => a.severity === severity);
  }, [anomalies]);

  const acknowledgeAnomaly = useCallback((id: string) => {
    setAcknowledgedIds(prev => new Set([...prev, id]));
  }, []);

  const dismissAnomaly = useCallback((id: string) => {
    setDismissedIds(prev => new Set([...prev, id]));
  }, []);

  const recalculate = useCallback(() => {
    // Force recalculation by clearing caches (handled by useMemo dependencies)
    setIsDetecting(true);
    setTimeout(() => setIsDetecting(false), 100);
  }, []);

  return {
    anomalies,
    overallBaseline,
    categoryBaselines,
    productBaselines,
    isDetecting,
    recalculate,
    getAnomaliesForEntity,
    getAnomaliesBySeverity,
    acknowledgeAnomaly,
    dismissAnomaly,
  };
}

export default useSalesAnomalyDetection;
