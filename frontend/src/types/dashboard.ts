/**
 * CONFIT — Store Owner Dashboard Types
 * =====================================
 * Type definitions for the B2B analytics dashboard.
 */

// ─── Sale Record ────────────────────────────────────────────────

export interface SaleRecord {
  id: string;
  productName: string;
  thumbnail: string;
  category: SaleCategory;
  productType: string;
  price: number;
  quantity: number;
  currency: string;
  customerName: string;
  customerEmail?: string;
  customerPhone?: string;
  customerSegment: CustomerSegment;
  saleDate: string; // ISO 8601
  profitMargin: number; // 0–100 percentage
  returnStatus: ReturnStatus;
  sku: string;
  brand: string;
  storeName: string;
  storeAddress?: string;
  paymentMethod: string;
  orderId: string;
}

export type SaleCategory = 'Clothes' | 'Shoes' | 'Accessories' | 'Full Outfit';

export type CustomerSegment = 'New Customer' | 'Returning' | 'VIP' | 'Wholesale';

export type ReturnStatus = 'Completed' | 'Returned' | 'Pending Return';

// ─── Dashboard Filters ─────────────────────────────────────────

export type DateRangePreset = 'today' | 'this_week' | 'this_month' | 'custom';

export interface DashboardFilters {
  categories: SaleCategory[];
  dateRange: DateRangePreset;
  customDateFrom?: string;
  customDateTo?: string;
  productType: string;
  productName?: string; // Drill-down: specific product
  priceMin: number;
  priceMax: number;
  customerSegment: string;
  marginRange?: 'high' | 'healthy' | 'atRisk'; // Drill-down: margin category
  returnStatuses?: ReturnStatus[]; // Drill-down: return status filter
}

export const INITIAL_DASHBOARD_FILTERS: DashboardFilters = {
  categories: [],
  dateRange: 'this_month',
  productType: 'all',
  productName: undefined,
  priceMin: 0,
  priceMax: 50000,
  customerSegment: 'all',
  marginRange: undefined,
  returnStatuses: undefined,
};

// ─── Active Filter Chip ────────────────────────────────────────

export interface FilterChip {
  key: string;
  label: string;
  onRemove: () => void;
}

// ─── KPI Data ───────────────────────────────────────────────────

export interface KPIValue {
  current: number;
  previous: number;
  delta: number; // percentage change
  formatted: string;
}

export interface KPIData {
  totalSales: KPIValue;
  conversionRate: KPIValue;
  returnRate: KPIValue;
  avgOrderValue: KPIValue;
}

// ─── Sort ───────────────────────────────────────────────────────

export type SaleSortField =
  | 'productName'
  | 'category'
  | 'price'
  | 'quantity'
  | 'customerName'
  | 'saleDate'
  | 'profitMargin'
  | 'returnStatus';

export type SortDirection = 'asc' | 'desc';

// ─── Pagination ─────────────────────────────────────────────────

export interface PaginationState {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

// ─── Product Type Mapping ───────────────────────────────────────

export const CATEGORY_PRODUCT_TYPES: Record<SaleCategory, string[]> = {
  'Clothes': ['Tops', 'Bottoms', 'Dresses', 'Blazers', 'T-Shirts', 'Jackets'],
  'Shoes': ['Formal', 'Casual', 'Sneakers', 'Heels', 'Boots'],
  'Accessories': ['Jewelry', 'Bags', 'Watches', 'Belts', 'Scarves'],
  'Full Outfit': ['Casual Set', 'Formal Set', 'Evening Set', 'Bridal Set'],
};
