/**
 * CONFIT Analytics Service
 * Handles all analytics-related API calls for dashboards
 */

import { api } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';

// ===========================================
// Types
// ===========================================

// Store Analytics Types
export interface TopSKU {
  sku: string;
  product_name?: string;
  view_count: number;
}

export interface ReturnReasonBreakdown {
  fit: number;
  color: number;
  quality: number;
  other: number;
}

export interface StoreDashboardData {
  store_id: string;
  store_name: string;
  visitors_today: number;
  visitors_7d: number;
  visitors_30d: number;
  conversion_rate: number;
  try_on_to_purchase_rate: number;
  top_viewed_skus: TopSKU[];
  bopis_avg_pickup_time_minutes: number | null;
  return_reason_breakdown: ReturnReasonBreakdown;
  coupon_redemption_rate: number;
  donor_coupon_attribution_egp: number;
  revenue_today_egp: number;
  revenue_7d_egp: number;
  revenue_30d_egp: number;
  orders_today: number;
  orders_7d: number;
  orders_30d: number;
}

export interface HeatmapCell {
  hour: number;
  day_of_week: number;
  visitor_count: number;
}

export interface StoreHeatmapData {
  store_id: string;
  data: HeatmapCell[];
}

export interface TopProduct {
  product_id: string | null;
  sku: string;
  view_count?: number;
  purchase_count?: number;
}

// Brand Analytics Types
export interface SKUSales {
  sku: string;
  product_name?: string;
  quantity_sold: number;
  revenue_egp: number;
}

export interface MidwayRejectionBreakdown {
  fabric_qa: number;
  stitch_qa: number;
  final_qa: number;
  size_mismatch: number;
  color_mismatch: number;
}

export interface StyledWith {
  product_id: string;
  product_name?: string;
  brand_id: string;
  brand_name: string;
  styled_together_count: number;
}

export interface RegionalSales {
  city: string;
  sales_count: number;
  revenue_egp: number;
}

export interface ForecastData {
  date: string;
  predicted_sales: number;
  confidence_lower: number;
  confidence_upper: number;
}

export interface BrandDashboardData {
  brand_id: string;
  brand_name: string;
  products_sold_total: number;
  products_sold_30d: number;
  sku_breakdown: SKUSales[];
  midway_rejections_count: number;
  midway_rejections_by_reason: MidwayRejectionBreakdown;
  outfit_to_purchase_ratio: number;
  return_reduction_delta: number | null;
  most_styled_with: StyledWith[];
  regional_heatmap_egypt: RegionalSales[];
  forecast_next_30d: ForecastData[];
}

export interface RejectionDetail {
  sku: string;
  stage: string;
  reason_code: string;
  timestamp: string;
}

// User Analytics Types
export interface VisitedStore {
  store_id: string;
  store_name: string;
  address: string;
  city: string;
  location?: { lat: number; lng: number } | null;
  visit_count: number;
  last_visited: string;
}

export interface UserSummaryData {
  user_id: string;
  outfits_saved: number;
  outfits_saved_30d: number;
  try_on_sessions_30d: number;
  money_saved_via_coupons_egp: number;
  reuse_score: number;
  visited_stores: VisitedStore[];
  total_orders: number;
  total_spent_egp: number;
  member_since: string;
}

export interface ActivityItem {
  date: string;
  event_type: string;
  event_name: string;
  details: Record<string, unknown>;
}

export interface WardrobeStats {
  user_id: string;
  total_items: number;
  times_worn_total: number;
  reuse_score: number;
  sustainability_impact: {
    co2_saved_kg: number;
    water_saved_liters: number;
  };
  category_breakdown: Record<string, number>;
  brand_breakdown: Record<string, number>;
}

export interface TryOnSession {
  session_id: string;
  product_id: string | null;
  timestamp: string;
  quality_score?: number;
  added_to_bag: boolean;
}

export interface CouponHistory {
  user_id: string;
  period_days: number;
  total_coupons_used: number;
  total_savings_egp: number;
  donor_coupons_redeemed: number;
  donor_savings_egp: number;
  coupons: Array<{
    coupon_code: string;
    discount_egp: number;
    order_id?: string;
    timestamp: string;
    donor_id?: string;
  }>;
}

// Admin Analytics Types
export interface RetentionCohort {
  cohort_date: string;
  users_count: number;
  d1_retention: number;
  d7_retention: number;
  d30_retention: number;
}

export interface CouponHealth {
  active_coupons: number;
  redeemed_coupons: number;
  expired_coupons: number;
  total_discount_egp: number;
}

export interface AdminOverviewData {
  confident_purchases_per_month: number;
  dau: number;
  wau: number;
  mau: number;
  retention_cohorts: RetentionCohort[];
  fraud_flags_count: number;
  nps_score: number | null;
  csat_score: number | null;
  coupon_ecosystem_health: CouponHealth;
  total_revenue_egp: number;
  total_orders: number;
  total_users: number;
  active_stores: number;
  active_brands: number;
}

export interface PlatformMetrics {
  period_start: string;
  period_end: string;
  total_events: number;
  events_by_type: Record<string, number>;
  top_events: Array<{ event_name: string; count: number }>;
}

export interface FunnelStage {
  stage: string;
  event_name: string;
  unique_users: number;
  conversion_from_previous: number | null;
}

// ===========================================
// Analytics Service
// ===========================================

export const analyticsService = {
  // -------------------------
  // Store Analytics
  // -------------------------
  
  /**
   * Get store dashboard data
   */
  async getStoreDashboard(storeId: string): Promise<StoreDashboardData> {
    return api.get<StoreDashboardData>(API_ENDPOINTS.ANALYTICS.STORE_DASHBOARD(storeId));
  },

  /**
   * Get store visitor heatmap
   */
  async getStoreHeatmap(storeId: string, days: number = 7): Promise<StoreHeatmapData> {
    return api.get<StoreHeatmapData>(
      `${API_ENDPOINTS.ANALYTICS.STORE_HEATMAP(storeId)}?days=${days}`
    );
  },

  /**
   * Get store top products
   */
  async getStoreTopProducts(
    storeId: string,
    days: number = 30,
    limit: number = 10
  ): Promise<{ store_id: string; period_days: number; top_viewed: TopProduct[]; top_purchased: TopProduct[] }> {
    return api.get(
      `${API_ENDPOINTS.ANALYTICS.STORE_TOP_PRODUCTS(storeId)}?days=${days}&limit=${limit}`
    );
  },

  // -------------------------
  // Brand Analytics
  // -------------------------

  /**
   * Get brand dashboard data
   */
  async getBrandDashboard(brandId: string): Promise<BrandDashboardData> {
    return api.get<BrandDashboardData>(API_ENDPOINTS.ANALYTICS.BRAND_DASHBOARD(brandId));
  },

  /**
   * Get brand midway rejections
   */
  async getBrandRejections(
    brandId: string,
    days: number = 30,
    stage?: string
  ): Promise<{
    brand_id: string;
    period_days: number;
    total_rejections: number;
    rejections: RejectionDetail[];
  }> {
    const params = new URLSearchParams({ days: String(days) });
    if (stage) params.append('stage', stage);
    return api.get(`${API_ENDPOINTS.ANALYTICS.BRAND_REJECTIONS(brandId)}?${params}`);
  },

  /**
   * Get brand regional sales
   */
  async getBrandRegionalSales(
    brandId: string,
    days: number = 30
  ): Promise<{
    brand_id: string;
    period_days: number;
    regional_breakdown: RegionalSales[];
  }> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.BRAND_REGIONAL_SALES(brandId)}?days=${days}`);
  },

  // -------------------------
  // User Analytics
  // -------------------------

  /**
   * Get user personal summary
   */
  async getUserSummary(): Promise<UserSummaryData> {
    return api.get<UserSummaryData>(API_ENDPOINTS.ANALYTICS.USER_SUMMARY);
  },

  /**
   * Get user activity timeline
   */
  async getUserActivity(
    days: number = 30,
    limit: number = 50
  ): Promise<{ user_id: string; period_days: number; activities: ActivityItem[] }> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.USER_ACTIVITY}?days=${days}&limit=${limit}`);
  },

  /**
   * Get user wardrobe stats
   */
  async getWardrobeStats(): Promise<WardrobeStats> {
    return api.get<WardrobeStats>(API_ENDPOINTS.ANALYTICS.USER_WARDROBE_STATS);
  },

  /**
   * Get user try-on history
   */
  async getTryOnHistory(
    days: number = 30,
    limit: number = 50
  ): Promise<{ user_id: string; period_days: number; total_sessions: number; sessions: TryOnSession[] }> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.USER_TRY_ON_HISTORY}?days=${days}&limit=${limit}`);
  },

  /**
   * Get user coupon history
   */
  async getCouponHistory(days: number = 90): Promise<CouponHistory> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.USER_COUPON_HISTORY}?days=${days}`);
  },

  // -------------------------
  // Admin Analytics
  // -------------------------

  /**
   * Get admin platform overview
   */
  async getAdminOverview(): Promise<AdminOverviewData> {
    return api.get<AdminOverviewData>(API_ENDPOINTS.ANALYTICS.ADMIN_OVERVIEW);
  },

  /**
   * Get platform metrics
   */
  async getPlatformMetrics(days: number = 7): Promise<PlatformMetrics> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.ADMIN_METRICS}?days=${days}`);
  },

  /**
   * Get revenue analytics
   */
  async getRevenueAnalytics(
    days: number = 30,
    groupBy: 'day' | 'week' | 'month' | 'store' | 'brand' = 'day'
  ): Promise<{
    period_days: number;
    group_by: string;
    data: Array<{
      period?: string;
      store_id?: string;
      store_name?: string;
      brand_id?: string;
      brand_name?: string;
      orders: number;
      revenue_egp: number;
    }>;
  }> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.ADMIN_REVENUE}?days=${days}&group_by=${groupBy}`);
  },

  /**
   * Get conversion funnel
   */
  async getConversionFunnel(days: number = 30): Promise<{
    period_days: number;
    funnel: FunnelStage[];
  }> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.ADMIN_FUNNEL}?days=${days}`);
  },

  /**
   * Get geographic distribution
   */
  async getGeographicDistribution(days: number = 30): Promise<{
    period_days: number;
    users_by_country: Record<string, number>;
    orders_by_city_egypt: Record<string, number>;
  }> {
    return api.get(`${API_ENDPOINTS.ANALYTICS.ADMIN_GEOGRAPHIC}?days=${days}`);
  },
};
