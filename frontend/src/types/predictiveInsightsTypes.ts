/**
 * CONFIT — Predictive Insights Types
 * ====================================
 * TypeScript types for the intelligent predictive analytics and anomaly
 * detection layer integrated with the Sales Insights Widget.
 */

// ─── Anomaly Types ───

export type AnomalyType =
  | 'revenue_drop'
  | 'revenue_spike'
  | 'margin_compression'
  | 'margin_improvement'
  | 'velocity_drop'
  | 'velocity_spike'
  | 'return_rate_spike'
  | 'category_underperformance'
  | 'category_overperformance'
  | 'product_underperformance'
  | 'product_overperformance';

export type AnomalySeverity = 'critical' | 'warning' | 'opportunity';

export type AnomalyMetric =
  | 'revenue'
  | 'profit_margin'
  | 'sales_velocity'
  | 'return_rate'
  | 'category_performance'
  | 'product_performance';

// ─── Baseline Types ───

export interface BaselineMetrics {
  /** Rolling average of the metric */
  average: number;
  /** Standard deviation for anomaly detection */
  standardDeviation: number;
  /** Interquartile range for IQR-based detection */
  iqr: {
    q1: number;
    q3: number;
    iqr: number;
    lowerBound: number;
    upperBound: number;
  };
  /** Z-score threshold for anomaly detection */
  zScoreThreshold: number;
  /** Percentage deviation threshold */
  percentDeviationThreshold: number;
  /** Rolling window size in days */
  windowDays: number;
  /** Number of data points used */
  sampleSize: number;
  /** Last computed timestamp */
  computedAt: string;
}

export interface ProductBaseline extends BaselineMetrics {
  productId: string;
  productName: string;
  category: string;
}

export interface CategoryBaseline extends BaselineMetrics {
  category: string;
  productCount: number;
}

// ─── Anomaly Detection Result ───

export interface DetectedAnomaly {
  id: string;
  type: AnomalyType;
  severity: AnomalySeverity;
  metric: AnomalyMetric;
  
  /** Current observed value */
  currentValue: number;
  /** Baseline reference value */
  baselineValue: number;
  /** Absolute deviation */
  deviation: number;
  /** Percentage deviation from baseline */
  percentDeviation: number;
  /** Z-score of the deviation */
  zScore: number;
  
  /** Contextual description */
  description: string;
  /** Actionable recommendation */
  recommendation: string;
  
  /** Affected entity (product name, category, etc.) */
  affectedEntity: string;
  /** Entity type for drill-down */
  entityType: 'product' | 'category' | 'overall';
  
  /** Timestamp when anomaly was detected */
  detectedAt: string;
  /** Whether the anomaly is still active */
  isActive: boolean;
  /** Whether the user has acknowledged this anomaly */
  acknowledged: boolean;
  /** Whether the user has dismissed this anomaly */
  dismissed: boolean;
  
  /** Filters to apply for drill-down */
  drillDownFilters: AnomalyDrillDownFilters;
}

export interface AnomalyDrillDownFilters {
  productName?: string;
  category?: string;
  dateRange?: { start: string; end: string };
  marginRange?: 'high' | 'healthy' | 'atRisk';
  returnStatuses?: string[];
}

// ─── Forecast Types ───

export type ForecastHorizon = '7d' | '14d' | '30d';

export type TrendDirection = 'up' | 'down' | 'stable';

export interface ForecastPoint {
  date: string;
  /** Predicted value */
  predicted: number;
  /** Lower bound of confidence interval */
  lowerBound: number;
  /** Upper bound of confidence interval */
  upperBound: number;
  /** Confidence level (0-1) */
  confidence: number;
}

export interface RevenueForecast {
  horizon: ForecastHorizon;
  points: ForecastPoint[];
  /** Total predicted revenue for the horizon */
  totalPredicted: number;
  /** Trend direction */
  trend: TrendDirection;
  /** Overall confidence in the forecast */
  confidence: number;
  /** Method used for forecasting */
  method: 'exponential_smoothing' | 'linear_regression' | 'moving_average';
  /** Computed timestamp */
  computedAt: string;
}

export interface MetricTrend {
  metric: AnomalyMetric;
  direction: TrendDirection;
  /** Percentage change rate per period */
  rateOfChange: number;
  /** Confidence in the trend detection */
  confidence: number;
  /** Number of data points analyzed */
  sampleSize: number;
}

// ─── Emerging Opportunity Types ───

export interface EmergingOpportunity {
  id: string;
  type: 'category_growth' | 'product_momentum' | 'margin_improvement';
  /** Entity name (category or product) */
  entity: string;
  entityType: 'category' | 'product';
  /** Current performance metric */
  currentValue: number;
  /** Baseline for comparison */
  baselineValue: number;
  /** Percentage improvement */
  improvementPercent: number;
  /** Trend over recent period */
  trend: TrendDirection;
  /** Velocity of change (accelerating/decelerating) */
  velocity: 'accelerating' | 'steady' | 'decelerating';
  /** Confidence in the opportunity */
  confidence: number;
  /** Description of the opportunity */
  description: string;
  /** Detected timestamp */
  detectedAt: string;
  /** Whether user has viewed this */
  acknowledged: boolean;
  /** Filters for drill-down */
  drillDownFilters: AnomalyDrillDownFilters;
}

// ─── Alert Configuration ───

export interface AnomalyDetectionConfig {
  /** Z-score threshold for critical anomalies */
  criticalZScoreThreshold: number;
  /** Z-score threshold for warning anomalies */
  warningZScoreThreshold: number;
  /** Minimum percent deviation to flag */
  minPercentDeviation: number;
  /** Rolling window for baseline (days) */
  baselineWindowDays: number;
  /** Minimum data points required */
  minDataPoints: number;
  /** Enable opportunity detection */
  enableOpportunities: boolean;
  /** Enable forecasting */
  enableForecasting: boolean;
  /** Forecast horizons to compute */
  forecastHorizons: ForecastHorizon[];
}

export const DEFAULT_ANOMALY_CONFIG: AnomalyDetectionConfig = {
  criticalZScoreThreshold: 2.5,
  warningZScoreThreshold: 2.0,
  minPercentDeviation: 15,
  baselineWindowDays: 30,
  minDataPoints: 10,
  enableOpportunities: true,
  enableForecasting: true,
  forecastHorizons: ['7d', '14d', '30d'],
};

// ─── Predictive Insights State ───

export interface PredictiveInsightsState {
  /** Detected anomalies */
  anomalies: DetectedAnomaly[];
  /** Revenue forecasts by horizon */
  forecasts: Record<ForecastHorizon, RevenueForecast | null>;
  /** Emerging opportunities */
  opportunities: EmergingOpportunity[];
  /** Baseline metrics by category */
  categoryBaselines: Record<string, CategoryBaseline>;
  /** Baseline metrics by product */
  productBaselines: Record<string, ProductBaseline>;
  /** Overall baseline metrics */
  overallBaseline: BaselineMetrics | null;
  /** Current trends */
  trends: MetricTrend[];
  /** Whether insights are being computed */
  isComputing: boolean;
  /** Last computation timestamp */
  lastComputed: string | null;
  /** Configuration */
  config: AnomalyDetectionConfig;
  /** Alert sensitivity level (user-adjustable) */
  sensitivity: 'high' | 'medium' | 'low';
}

// ─── Severity Helpers ───

export function getAnomalySeverityConfig(severity: AnomalySeverity) {
  const configs = {
    critical: {
      color: 'text-gold-400',
      bgColor: 'bg-gold-500/10',
      borderColor: 'border-l-gold-500',
      glowColor: 'shadow-gold-500/20',
      icon: 'AlertTriangle',
      label: 'Critical',
      description: 'Significant deviation requiring immediate attention',
    },
    warning: {
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-l-purple-500',
      glowColor: 'shadow-purple-500/20',
      icon: 'AlertCircle',
      label: 'Warning',
      description: 'Moderate deviation worth monitoring',
    },
    opportunity: {
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-l-emerald-500',
      glowColor: 'shadow-emerald-500/20',
      icon: 'TrendingUp',
      label: 'Opportunity',
      description: 'Positive trend worth capitalizing on',
    },
  };
  return configs[severity];
}

export function getAnomalyTypeConfig(type: AnomalyType) {
  const configs: Record<AnomalyType, { label: string; description: string; isPositive: boolean }> = {
    revenue_drop: {
      label: 'Revenue Drop',
      description: 'Revenue significantly below baseline',
      isPositive: false,
    },
    revenue_spike: {
      label: 'Revenue Spike',
      description: 'Revenue significantly above baseline',
      isPositive: true,
    },
    margin_compression: {
      label: 'Margin Compression',
      description: 'Profit margins declining below historical average',
      isPositive: false,
    },
    margin_improvement: {
      label: 'Margin Improvement',
      description: 'Profit margins improving above historical average',
      isPositive: true,
    },
    velocity_drop: {
      label: 'Sales Velocity Drop',
      description: 'Sales velocity significantly decreased',
      isPositive: false,
    },
    velocity_spike: {
      label: 'Sales Velocity Spike',
      description: 'Sales velocity significantly increased',
      isPositive: true,
    },
    return_rate_spike: {
      label: 'Return Rate Spike',
      description: 'Return rate significantly elevated',
      isPositive: false,
    },
    category_underperformance: {
      label: 'Category Underperformance',
      description: 'Category performing below baseline',
      isPositive: false,
    },
    category_overperformance: {
      label: 'Category Overperformance',
      description: 'Category performing above baseline',
      isPositive: true,
    },
    product_underperformance: {
      label: 'Product Underperformance',
      description: 'Product performing below baseline',
      isPositive: false,
    },
    product_overperformance: {
      label: 'Product Momentum',
      description: 'Product gaining momentum',
      isPositive: true,
    },
  };
  return configs[type];
}

// ─── Sensitivity Configuration ───

export function getSensitivityConfig(sensitivity: 'high' | 'medium' | 'low'): Partial<AnomalyDetectionConfig> {
  const configs = {
    high: {
      criticalZScoreThreshold: 2.0,
      warningZScoreThreshold: 1.5,
      minPercentDeviation: 10,
    },
    medium: {
      criticalZScoreThreshold: 2.5,
      warningZScoreThreshold: 2.0,
      minPercentDeviation: 15,
    },
    low: {
      criticalZScoreThreshold: 3.0,
      warningZScoreThreshold: 2.5,
      minPercentDeviation: 25,
    },
  };
  return configs[sensitivity];
}
