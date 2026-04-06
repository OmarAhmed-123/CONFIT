/**
 * CONFIT — Alert Recommendation Types
 * =====================================
 * TypeScript types for the Predictive Alert Recommendations Engine.
 * Covers recommendations, backtesting, pattern analysis, and A/B testing.
 */

// ─── Enums ─────────────────────────────────────────────────────────────────────

export type RecommendationType =
  | 'return_spike'
  | 'high_value_aov'
  | 'conversion_anomaly'
  | 'inventory_depletion'
  | 'seasonal_adjustment'
  | 'vip_inactivity';

export type RecommendationStatus =
  | 'pending'
  | 'shown'
  | 'accepted'
  | 'dismissed'
  | 'applied'
  | 'expired';

export type ConfidenceLevel = 'low' | 'medium' | 'high';

export type ImpactEstimate = 'low' | 'medium' | 'high' | 'critical';

export type ABTestGroup = 'control' | 'treatment';

export type BacktestEventType =
  | 'true_positive'
  | 'false_positive'
  | 'true_negative'
  | 'false_negative';

// ─── Backtesting Types ─────────────────────────────────────────────────────────

export interface BacktestEvent {
  event_type: BacktestEventType;
  timestamp: string;
  actual_value: number;
  threshold_value: number;
  deviation_percent: number;
  would_have_alerted: boolean;
  was_actionable?: boolean;
  context?: Record<string, unknown>;
}

export interface BacktestSummary {
  total_events: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
  false_positive_rate: number;
  significant_moments_caught: number;
  significant_moments_missed: number;
  analysis_period_days: number;
  data_points_analyzed: number;
}

export interface BacktestDisplay {
  summary_text: string;
  metrics: {
    precision: string;
    recall: string;
    false_positive_rate: string;
    significant_moments_caught: number;
  };
  significant_events: Array<{
    date: string;
    value: number;
    threshold: number;
    deviation: string;
    context?: Record<string, unknown>;
  }>;
  passes_validation: boolean;
}

// ─── Recommendation Types ──────────────────────────────────────────────────────

export interface ThresholdRecommendation {
  parameter_name: string;
  current_value: number | string;
  recommended_value: number | string;
  unit: string;
  percentile_used?: number;
  temporary?: boolean;
  revert_date?: string;
}

export interface RecommendationExplanation {
  summary: string;
  data_points: Record<string, number | string>;
  methodology: string;
  historical_examples: Array<Record<string, unknown>>;
}

export interface AlertRecommendation {
  id: string;
  store_id: string;
  type: RecommendationType;
  status: RecommendationStatus;

  // Content
  title: string;
  description?: string;

  // Threshold details
  thresholds: ThresholdRecommendation[];

  // Confidence and impact
  confidence: ConfidenceLevel;
  confidence_score: number;
  impact_estimate: ImpactEstimate;

  // Explanation
  explanation: RecommendationExplanation;

  // Backtesting
  backtest_summary?: BacktestSummary;
  backtest_events?: BacktestEvent[];
  backtest_display?: BacktestDisplay;

  // Metadata
  data_window_days: number;
  generated_at: string;
  expires_at?: string;

  // User interaction
  shown_at?: string;
  accepted_at?: string;
  dismissed_at?: string;
  applied_at?: string;
  user_feedback?: string;
  user_rating?: number;
  was_valuable?: boolean;

  // Ranking
  rank_score: number;
}

// ─── Pattern Analysis Types ────────────────────────────────────────────────────

export interface ReturnPatternAnalysis {
  baseline_weekly_returns: number;
  return_volatility: number;
  coefficient_of_variation?: number;
  spike_threshold_80th: number;
  spike_threshold_90th: number;
  products_with_high_return_velocity: Array<{
    product_id: string;
    product_name: string;
    return_count: number;
    velocity_per_week: number;
  }>;
  seasonal_return_patterns: Record<string, number>;
  total_returns_analyzed?: number;
  weeks_analyzed?: number;
}

export interface AOVPatternAnalysis {
  baseline_aov: number;
  aov_range_low: number;
  aov_range_high: number;
  aov_std_dev?: number;
  outlier_threshold_85th: number;
  outlier_threshold_90th: number;
  high_value_order_frequency: number;
  seasonal_aov_patterns: Record<string, number>;
  total_orders_analyzed?: number;
}

export interface ConversionPatternAnalysis {
  baseline_conversion_rate: number;
  rolling_7day_variance: number;
  deviation_threshold_drop: number;
  deviation_threshold_rise: number;
  historical_anomalies: Array<{
    date: string;
    value: number;
    baseline: number;
    deviation_percent: number;
    type: 'drop' | 'rise';
  }>;
  seasonal_conversion_patterns: Record<string, number>;
  total_days_analyzed?: number;
}

export interface InventoryVelocityAnalysis {
  category_velocities: Record<string, number>;
  fast_mover_threshold: number;
  slow_mover_threshold: number;
  recommended_stock_thresholds: Record<string, number>;
  total_products?: number;
  total_items_sold?: number;
}

export interface SeasonalPatternAnalysis {
  peak_seasons: string[];
  peak_conversion_lift_percent: number;
  peak_aov_lift_percent: number;
  is_q4_peak?: boolean;
  recommended_temporary_adjustments: {
    conversion_drop_threshold_percent?: number;
    conversion_rise_threshold_percent?: number;
    period?: string;
    auto_revert_date?: string;
  };
  months_analyzed?: number;
}

export interface CustomerSegmentAnalysis {
  vip_avg_purchase_cycle_days: number;
  returning_avg_purchase_cycle_days: number;
  recommended_vip_inactivity_days: number;
  recommended_returning_inactivity_days: number;
  at_risk_customers: Array<{
    customer_id: string;
    segment: string;
    days_since_last_order: number;
    ltv: number;
  }>;
  total_customers_analyzed?: number;
  vip_count?: number;
  returning_count?: number;
}

export interface StorePatternAnalysis {
  store_id: string;
  analysis_date: string;
  data_window_days: number;
  return_patterns: ReturnPatternAnalysis;
  aov_patterns: AOVPatternAnalysis;
  conversion_patterns: ConversionPatternAnalysis;
  inventory_patterns: InventoryVelocityAnalysis;
  seasonal_patterns: SeasonalPatternAnalysis;
  customer_segment_patterns: CustomerSegmentAnalysis;
  data_quality_score: number;
  has_sufficient_data: boolean;
}

// ─── A/B Testing Types ─────────────────────────────────────────────────────────

export interface ABTestMetrics {
  total_events?: number;
  unique_stores?: number;

  // Recommendation metrics
  recommendations_shown?: number;
  recommendations_accepted?: number;
  recommendations_dismissed?: number;
  recommendation_adoption_rate?: number;

  // Time metrics
  avg_time_to_accept_seconds?: number;
  median_time_to_accept_seconds?: number;

  // Alert metrics
  alerts_received?: number;
  alert_actions_taken?: number;
  alert_actionability_rate?: number;

  avg_time_to_alert_action_seconds?: number;
  median_time_to_alert_action_seconds?: number;

  // Configuration metrics
  threshold_changes?: number;
  manual_threshold_changes?: number;
  configuration_churn_count?: number;
}

export interface ABTestExperiment {
  id: string;
  name: string;
  description?: string;

  // Configuration
  control_group_size: number;
  treatment_group_size: number;
  start_date: string;
  end_date?: string;
  min_duration_days: number;

  // Status
  is_active: boolean;
  is_paused: boolean;

  // Metrics
  control_metrics: ABTestMetrics;
  treatment_metrics: ABTestMetrics;

  // Statistical significance
  significance_level?: number;
  p_value?: number;
  is_significant: boolean;

  created_at: string;
  updated_at: string;
}

export interface ABTestAssignment {
  id: string;
  experiment_id: string;
  store_id: string;
  group: ABTestGroup;
  assigned_at: string;
  metrics: ABTestMetrics;
}

export interface ABTestSignificanceResult {
  is_significant: boolean;
  p_value?: number;
  z_score?: number;
  control_rate?: number;
  treatment_rate?: number;
  relative_lift?: number;
  control_sample?: number;
  treatment_sample?: number;
  reason?: string;
  min_required?: number;
}

export interface ABTestReport {
  experiment: ABTestExperiment;
  duration_days: number;
  control_group: {
    store_count: number;
    metrics: ABTestMetrics;
  };
  treatment_group: {
    store_count: number;
    metrics: ABTestMetrics;
  };
  significance?: ABTestSignificanceResult;
  recommendations: string[];
}

// ─── API Request/Response Types ────────────────────────────────────────────────

export interface GenerateRecommendationsRequest {
  store_id: string;
  data_window_days?: number;
  force_refresh?: boolean;
}

export interface GenerateRecommendationsResponse {
  store_id: string;
  recommendations: AlertRecommendation[];
  pattern_analysis: StorePatternAnalysis | Record<string, never>;
  generated_at: string;
  cache_hit: boolean;
}

export interface ApplyRecommendationRequest {
  recommendation_id: string;
  store_id: string;
  custom_thresholds?: Record<string, number | string>;
}

export interface ApplyRecommendationResponse {
  success: boolean;
  recommendation_id: string;
  applied_thresholds: Record<string, number | string>;
  updated_preferences: Record<string, number | string>;
}

export interface DismissRecommendationRequest {
  recommendation_id: string;
  store_id: string;
  reason?: string;
}

export interface RecommendationFeedbackRequest {
  recommendation_id: string;
  store_id: string;
  rating: number;
  feedback_text?: string;
  was_valuable: boolean;
}

export interface RecommendationListRequest {
  store_id: string;
  status?: RecommendationStatus[];
  types?: RecommendationType[];
  min_confidence?: ConfidenceLevel;
  include_dismissed?: boolean;
  page?: number;
  limit?: number;
}

export interface RecommendationListResponse {
  recommendations: AlertRecommendation[];
  total_count: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// ─── UI Helper Types ───────────────────────────────────────────────────────────

export interface RecommendationCardProps {
  recommendation: AlertRecommendation;
  onApply?: (recommendation: AlertRecommendation) => void;
  onDismiss?: (recommendation: AlertRecommendation) => void;
  onCustomize?: (recommendation: AlertRecommendation) => void;
  onViewDetails?: (recommendation: AlertRecommendation) => void;
  isApplying?: boolean;
  showBacktest?: boolean;
  compact?: boolean;
  className?: string;
}

export interface RecommendationsPanelProps {
  storeId: string;
  onRecommendationApplied?: (recommendation: AlertRecommendation) => void;
  className?: string;
}

export type RecommendationFilterState = {
  types: RecommendationType[];
  status: RecommendationStatus[];
  confidence: ConfidenceLevel | 'all';
  sortBy: 'rank' | 'generated' | 'impact';
  sortDirection: 'asc' | 'desc';
};

// ─── Type Guards & Utilities ──────────────────────────────────────────────────

export function getRecommendationTypeLabel(type: RecommendationType): string {
  const labels: Record<RecommendationType, string> = {
    return_spike: 'Return Spike',
    high_value_aov: 'High-Value Orders',
    conversion_anomaly: 'Conversion Anomaly',
    inventory_depletion: 'Inventory Depletion',
    seasonal_adjustment: 'Seasonal Adjustment',
    vip_inactivity: 'VIP Inactivity',
  };
  return labels[type] || type;
}

export function getRecommendationTypeDescription(type: RecommendationType): string {
  const descriptions: Record<RecommendationType, string> = {
    return_spike: 'Detect unusual return patterns early',
    high_value_aov: 'Identify significant high-value orders',
    conversion_anomaly: 'Spot conversion rate anomalies',
    inventory_depletion: 'Monitor inventory depletion velocity',
    seasonal_adjustment: 'Adjust thresholds for peak seasons',
    vip_inactivity: 'Track VIP customer engagement',
  };
  return descriptions[type] || '';
}

export function getConfidenceLabel(confidence: ConfidenceLevel): string {
  return confidence.charAt(0).toUpperCase() + confidence.slice(1);
}

export function getImpactLabel(impact: ImpactEstimate): string {
  const labels: Record<ImpactEstimate, string> = {
    low: 'Low Impact',
    medium: 'Medium Impact',
    high: 'High Impact',
    critical: 'Critical Impact',
  };
  return labels[impact] || impact;
}

export function getImpactColor(impact: ImpactEstimate): string {
  const colors: Record<ImpactEstimate, string> = {
    low: 'text-muted-foreground',
    medium: 'text-purple-400',
    high: 'text-gold-400',
    critical: 'text-gold-500',
  };
  return colors[impact] || 'text-muted-foreground';
}

export function getConfidenceColor(confidence: ConfidenceLevel): string {
  const colors: Record<ConfidenceLevel, string> = {
    low: 'text-muted-foreground',
    medium: 'text-purple-400',
    high: 'text-emerald-400',
  };
  return colors[confidence] || 'text-muted-foreground';
}

export function formatThresholdValue(
  value: number | string,
  unit: string
): string {
  if (typeof value === 'string') return value;
  
  if (unit === '$' || unit.startsWith('EGP')) {
    return `${unit}${value.toLocaleString()}`;
  }
  if (unit === '%') {
    return `${value}%`;
  }
  if (unit === 'x AOV') {
    return `${value}x AOV`;
  }
  if (unit === 'days') {
    return `${value} days`;
  }
  if (unit === 'units') {
    return `${value} units`;
  }
  
  return `${value} ${unit}`.trim();
}

export function isRecommendationActionable(
  recommendation: AlertRecommendation
): boolean {
  return (
    recommendation.status !== 'dismissed' &&
    recommendation.status !== 'applied' &&
    recommendation.status !== 'expired'
  );
}

export function getRecommendationStatusBadge(
  status: RecommendationStatus
): { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' } {
  const badges: Record<RecommendationStatus, { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' }> = {
    pending: { label: 'New', variant: 'default' },
    shown: { label: 'Viewed', variant: 'secondary' },
    accepted: { label: 'Accepted', variant: 'success' },
    dismissed: { label: 'Dismissed', variant: 'warning' },
    applied: { label: 'Applied', variant: 'success' },
    expired: { label: 'Expired', variant: 'destructive' },
  };
  return badges[status] || { label: status, variant: 'default' };
}
