/**
 * CONFIT Frontend Type Definitions
 * Central type definitions for the entire application
 */

// ===========================================
// User & Authentication Types
// ===========================================

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  avatar_url?: string;
  phone?: string;
  address?: Address;
  style_preference?: string;
  body_profile?: BodyProfile;
  budget_range?: BudgetRange;
  preferred_brands?: string[];
  occasion_preferences?: string[];
  marketing_consent?: boolean;
  data_sharing_consent?: boolean;
  created_at: string;
  updated_at?: string;
}

/** Auth/session user shape (snake_case + camelCase tolerated; used by AuthContext). */
export interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  avatar_url?: string;
  phone?: string;
  address?: {
    street?: string;
    city?: string;
    zipCode?: string;
    state?: string;
    zip?: string;
  };
  stylePreferences?: StylePreferences;
  style_preference?: string;
  body_profile?: { height?: string; weight?: string; bodyShape?: string; fitPreference?: string };
  budget_range?: { min?: number; max?: number; currency?: string };
  preferred_brands?: string[];
  occasion_preferences?: string[];
  marketing_consent?: boolean;
  data_sharing_consent?: boolean;
  roles?: string[];
  createdAt?: Date;
  updatedAt?: Date;
  created_at?: string;
  updated_at?: string;
}

export interface StylePreferences {
  styles: StyleType[];
  occasions: OccasionType[];
  colors: string[];
  budgetRange: BudgetRangeCatalog;
  preferredBrands: string[];
  bodyType?: BodyType;
}

export type StyleType =
  | 'casual'
  | 'formal'
  | 'streetwear'
  | 'minimalist'
  | 'bohemian'
  | 'classic'
  | 'sporty'
  | 'elegant';

export type OccasionType =
  | 'work'
  | 'wedding'
  | 'party'
  | 'casual'
  | 'date'
  | 'vacation'
  | 'formal-event'
  | 'formal'
  | 'active'
  | 'everyday';

/** Catalog / discover filters (strict min/max). */
export interface BudgetRangeCatalog {
  min: number;
  max: number;
  currency: string;
}

export type BodyType =
  | 'athletic'
  | 'slim'
  | 'curvy'
  | 'plus-size'
  | 'petite'
  | 'tall';

export type ProductCategory =
  | 'tops'
  | 'bottoms'
  | 'dresses'
  | 'outerwear'
  | 'shoes'
  | 'accessories'
  | 'bags';

export type SortOption =
  | 'relevance'
  | 'price-asc'
  | 'price-desc'
  | 'newest'
  | 'popularity';

export interface Address {
  street?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  lat?: number;
  lng?: number;
}

export interface BodyProfile {
  height?: number;
  weight?: number;
  body_type?: string;
  skin_tone?: string;
  measurements?: {
    chest?: number;
    waist?: number;
    hips?: number;
    inseam?: number;
  };
}

export interface BudgetRange {
  min?: number;
  max?: number;
  currency?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number;
}

// ===========================================
// Product & Catalog Types
// ===========================================

export interface Product {
  id: string;
  name: string;
  description?: string;
  category: string | ProductCategory;
  subcategory?: string;
  color?: string;
  size?: string;
  price: number;
  currency: string;
  brand_id?: string;
  /** API relation or plain catalog label from mocks */
  brand?: Brand | string;
  brandId?: string;
  store_id?: string;
  store?: Store;
  image_url?: string;
  images?: string[];
  tags?: string[];
  style_compatibility?: number;
  styleCompatibility?: number;
  inventory_count?: number;
  is_available?: boolean;
  inStock?: boolean;
  originalPrice?: number;
  gender?: 'men' | 'women' | 'unisex';
  colors?: string[];
  sizes?: string[];
  created_at?: string;
  updated_at?: string;
}

export interface Brand {
  id: string;
  name: string;
  description?: string;
  logo_url?: string;
  banner_url?: string;
  website?: string;
}

export interface Store {
  id: string;
  brand_id: string;
  name: string;
  address: string;
  city: string;
  state?: string;
  country: string;
  postal_code: string;
  phone?: string;
  email?: string;
  location?: {
    lat: number;
    lng: number;
  };
  hours?: Record<string, string>;
  services?: string[];
}

// ===========================================
// Shopping & Cart Types
// ===========================================

export interface CartItem {
  id: string;
  product_id: string;
  product?: Product;
  quantity: number;
  price: number;
  size?: string;
  color?: string;
}

export interface Cart {
  id: string;
  user_id: string;
  items: CartItem[];
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  currency: string;
}

export interface Order {
  id: string;
  order_number: string;
  user_id: string;
  user?: User;
  items: OrderItem[];
  status: OrderStatus;
  payment_status: PaymentStatus;
  payment_method?: string;
  delivery_method: 'shipping' | 'pickup';
  shipping_address?: Address;
  pickup_store_id?: string;
  pickup_store?: Store;
  pickup_time?: string;
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  currency: string;
  tracking_number?: string;
  estimated_delivery?: string;
  placed_at: string;
  updated_at?: string;
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_id?: string;
  name: string;
  quantity: number;
  price: number;
  image_url?: string;
}

export type OrderStatus = 
  | 'pending' 
  | 'confirmed' 
  | 'processing' 
  | 'shipped' 
  | 'delivered' 
  | 'cancelled'
  | 'returned';

export type PaymentStatus = 
  | 'pending' 
  | 'success' 
  | 'failed' 
  | 'refunded'
  | 'partial_refund';

// ===========================================
// Payment Types
// ===========================================

export interface PaymentIntent {
  client_secret: string;
  publishable_key: string;
  payment_intent_id: string;
}

export interface CheckoutSession {
  session_id: string;
  checkout_url: string;
}

export interface BNPLPlan {
  currency: string;
  total_amount: number;
  total_interest: number;
  effective_apr: number;
  installments: BNPLInstallment[];
}

export interface BNPLInstallment {
  number: number;
  due_date: string;
  principal: number;
  interest: number;
  total: number;
  remaining_balance: number;
}

// ===========================================
// CONFIT CARE Types
// ===========================================

export interface DonationCampaign {
  id: string;
  donor_id: string;
  donor?: User;
  title: string;
  description?: string;
  target_amount: number;
  current_amount: number;
  currency: string;
  status: CampaignStatus;
  beneficiaries?: Beneficiary[];
  vouchers?: Voucher[];
  start_date: string;
  end_date?: string;
  created_at: string;
  updated_at?: string;
}

export type CampaignStatus = 
  | 'draft' 
  | 'active' 
  | 'paused' 
  | 'completed' 
  | 'cancelled';

export interface Beneficiary {
  id: string;
  campaign_id: string;
  name: string;
  email?: string;
  phone?: string;
  budget_cap: number;
  currency: string;
  restrictions?: string[];
  total_spent: number;
  is_active: boolean;
  created_at: string;
}

export interface Voucher {
  id: string;
  code: string;
  campaign_id: string;
  beneficiary_id?: string;
  amount: number;
  currency: string;
  balance: number;
  status: VoucherStatus;
  expires_at?: string;
  used_at?: string;
  created_at: string;
}

export type VoucherStatus = 
  | 'active' 
  | 'used' 
  | 'expired' 
  | 'cancelled';

// ===========================================
// Virtual Try-On Types
// ===========================================

export interface TryOnRequest {
  user_image_base64: string;
  garment_image_url: string;
  garment_name?: string;
  garment_category?: string;
}

export interface TryOnResult {
  success: boolean;
  job_id?: string;
  status?: string;
  result_image?: string;
  timing_ms?: number;
  cache_hit?: boolean;
  warnings?: string[];
  error_message?: string;
  error_code?: string;
}

// ===========================================
// Wardrobe & Outfit Types
// ===========================================

export interface WardrobeItem {
  id: string;
  owner_user_id: string;
  name: string;
  brand?: string;
  category: string;
  color?: string;
  size?: string;
  price?: number;
  currency: string;
  image_url?: string;
  tags?: string[];
  notes?: string;
  source_product_id?: string;
  created_at: string;
  updated_at?: string;
}

/** Persisted wardrobe outfit (API / closet). */
export interface WardrobeOutfitRecord {
  id: string;
  owner_user_id: string;
  title: string;
  items: WardrobeItem[];
  occasion?: string;
  notes?: string;
  budget_limit?: number;
  total_price?: number;
  currency: string;
  share_slug?: string;
  created_at: string;
  updated_at?: string;
}

/** Stylist / mock “complete look” (discover, AI sections). */
export interface StylistOutfitItem {
  product: Product;
  position: 'top' | 'bottom' | 'layer' | 'shoes' | 'accessory';
}

export interface Outfit {
  id: string;
  name: string;
  items: StylistOutfitItem[];
  occasion: OccasionType;
  totalPrice: number;
  styleScore: number;
  createdAt: Date;
  userId: string;
}

export interface OutfitSuggestion {
  id: string;
  name: string;
  image: string;
  price: number;
  styleScore: number;
}

// ===========================================
// Styling & Recommendation Types
// ===========================================

export interface StyleProfile {
  user_id: string;
  primary_style?: string;
  secondary_styles?: string[];
  color_preferences?: string[];
  pattern_preferences?: string[];
  fit_preferences?: string[];
  occasion_preferences?: Record<string, string[]>;
  brand_affinities?: Record<string, number>;
  confidence_score?: number;
}

export interface Recommendation {
  id: string;
  type: 'product' | 'outfit' | 'style';
  items: Product[];
  reason?: string;
  score?: number;
  created_at: string;
}

// ===========================================
// Notification Types
// ===========================================

export interface Notification {
  id: string;
  receiver_id: string;
  order_id?: string;
  store_id?: string;
  message: string;
  metadata?: Record<string, unknown>;
  read_status: boolean;
  created_at: string;
}

// ===========================================
// Analytics Types
// ===========================================

export interface AnalyticsEvent {
  event_type: string;
  event_data?: Record<string, unknown>;
  timestamp?: string;
}

export interface DashboardMetrics {
  total_orders?: number;
  total_spent?: number;
  items_in_wardrobe?: number;
  outfits_created?: number;
  try_ons_completed?: number;
  eco_impact?: {
    co2_saved_kg: number;
    water_saved_l: number;
  };
}
