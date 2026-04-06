/**
 * CONFIT API Endpoints
 * Centralized endpoint definitions
 */

export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/api/auth/login',
    REGISTER: '/api/auth/register',
    REFRESH: '/api/auth/refresh',
    ME: '/api/auth/me',
    UPDATE_PROFILE: '/api/auth/me',
    LOGOUT: '/api/auth/logout',
    EXISTS: '/api/auth/exists',
    OAUTH_CALLBACK: '/api/auth/oauth/callback',
    FORGOT_PASSWORD: '/api/auth/forgot-password',
    RESET_PASSWORD: '/api/auth/reset-password',
    ROLES: '/api/auth/roles',
  },

  // Products
  PRODUCTS: {
    LIST: '/api/products',
    DETAIL: (id: string) => `/api/products/${id}`,
    SEARCH: '/api/products/search',
    CATEGORIES: '/api/products/categories',
    BY_BRAND: (brandId: string) => `/api/products/brand/${brandId}`,
    BY_STORE: (storeId: string) => `/api/products/store/${storeId}`,
  },

  // Brands
  BRANDS: {
    LIST: '/api/brands',
    DETAIL: (id: string) => `/api/brands/${id}`,
    PRODUCTS: (id: string) => `/api/brands/${id}/products`,
  },

  // Stores
  STORES: {
    LIST: '/api/stores',
    DETAIL: (id: string) => `/api/stores/${id}`,
    NEARBY: '/api/stores/nearby',
  },

  // Cart & Checkout
  CART: {
    GET: '/api/cart',
    ADD_ITEM: '/api/cart/items',
    UPDATE_ITEM: (itemId: string) => `/api/cart/items/${itemId}`,
    REMOVE_ITEM: (itemId: string) => `/api/cart/items/${itemId}`,
    CLEAR: '/api/cart/clear',
  },

  // Orders
  ORDERS: {
    LIST: '/api/orders',
    CREATE: '/api/orders',
    DETAIL: (id: string) => `/api/orders/${id}`,
    CANCEL: (id: string) => `/api/orders/${id}/cancel`,
    TRACK: (id: string) => `/api/orders/${id}/track`,
  },

  // Payments
  PAYMENTS: {
    CONFIG: '/api/payments/config',
    INTENT: '/api/payments/intent',
    CONFIRM: '/api/payments/confirm',
    CHECKOUT_SESSION: '/api/payments/checkout-session',
    BNPL_PLAN: '/api/payments/bnpl/plan',
  },

  // Wardrobe
  WARDROBE: {
    LIST: '/api/wardrobe',
    ADD: '/api/wardrobe',
    DETAIL: (id: string) => `/api/wardrobe/${id}`,
    UPDATE: (id: string) => `/api/wardrobe/${id}`,
    DELETE: (id: string) => `/api/wardrobe/${id}`,
    AUTO_TAG: (id: string) => `/api/wardrobe/${id}/auto-tag`,
  },

  // Outfits
  OUTFITS: {
    LIST: '/api/outfits',
    CREATE: '/api/outfits',
    DETAIL: (id: string) => `/api/outfits/${id}`,
    UPDATE: (id: string) => `/api/outfits/${id}`,
    DELETE: (id: string) => `/api/outfits/${id}`,
    SHARE: (id: string) => `/api/outfits/${id}/share`,
  },

  // Virtual Try-On
  TRY_ON: {
    PREVIEW: '/api/tryon/preview',
    RENDER: '/api/tryon',
    STATUS: (jobId: string) => `/api/tryon/status/${jobId}`,
  },

  // Styling & Recommendations
  STYLING: {
    PROFILE: '/api/style-dna/profile',
    RECOMMENDATIONS: '/api/recommendations',
    OUTFIT_SUGGESTIONS: '/api/stylist/suggest',
  },

  // Wishlist
  WISHLIST: {
    LIST: '/api/wishlist',
    ADD: '/api/wishlist',
    REMOVE: (productId: string) => `/api/wishlist/${productId}`,
  },

  // CONFIT CARE (Donation System)
  CARE: {
    // Campaigns
    CAMPAIGNS: '/api/care/campaigns',
    CAMPAIGN_DETAIL: (id: string) => `/api/care/campaigns/${id}`,
    CAMPAIGN_UPDATE: (id: string) => `/api/care/campaigns/${id}`,
    CAMPAIGN_STATS: (id: string) => `/api/care/campaigns/${id}/stats`,
    
    // Beneficiaries
    BENEFICIARIES: (campaignId: string) => `/api/care/campaigns/${campaignId}/beneficiaries`,
    BENEFICIARY_DETAIL: (campaignId: string, beneficiaryId: string) => 
      `/api/care/campaigns/${campaignId}/beneficiaries/${beneficiaryId}`,
    
    // Vouchers
    VOUCHERS: (campaignId: string) => `/api/care/campaigns/${campaignId}/vouchers`,
    VOUCHER_VALIDATE: '/api/care/vouchers/validate',
    VOUCHER_REDEEM: '/api/care/vouchers/redeem',
    
    // Donor Dashboard
    DONOR_DASHBOARD: '/api/care/donor/dashboard',
    DONOR_CAMPAIGNS: '/api/care/donor/campaigns',
  },

  // Notifications
  NOTIFICATIONS: {
    LIST: '/api/notifications',
    MARK_READ: (id: string) => `/api/notifications/${id}/read`,
    MARK_ALL_READ: '/api/notifications/read-all',
    PREFERENCES: '/api/notification-preferences',
  },

  // Analytics
  ANALYTICS: {
    DASHBOARD: '/api/analytics/dashboard',
    EVENTS: '/api/analytics/events',
    TRACK: '/api/analytics/track',
    
    // Store Analytics
    STORE_DASHBOARD: (storeId: string) => `/api/v1/analytics/stores/${storeId}/dashboard`,
    STORE_HEATMAP: (storeId: string) => `/api/v1/analytics/stores/${storeId}/heatmap`,
    STORE_TOP_PRODUCTS: (storeId: string) => `/api/v1/analytics/stores/${storeId}/top-products`,
    
    // Brand/Factory Analytics
    BRAND_DASHBOARD: (brandId: string) => `/api/v1/analytics/brands/${brandId}/dashboard`,
    BRAND_REJECTIONS: (brandId: string) => `/api/v1/analytics/brands/${brandId}/rejections`,
    BRAND_REGIONAL_SALES: (brandId: string) => `/api/v1/analytics/brands/${brandId}/regional-sales`,
    
    // User Personal Analytics
    USER_SUMMARY: '/api/v1/analytics/me/summary',
    USER_ACTIVITY: '/api/v1/analytics/me/activity',
    USER_WARDROBE_STATS: '/api/v1/analytics/me/wardrobe-stats',
    USER_TRY_ON_HISTORY: '/api/v1/analytics/me/try-on-history',
    USER_COUPON_HISTORY: '/api/v1/analytics/me/coupon-history',
    
    // Admin Platform Analytics
    ADMIN_OVERVIEW: '/api/v1/analytics/admin/overview',
    ADMIN_METRICS: '/api/v1/analytics/admin/metrics',
    ADMIN_REVENUE: '/api/v1/analytics/admin/revenue',
    ADMIN_FUNNEL: '/api/v1/analytics/admin/funnel',
    ADMIN_GEOGRAPHIC: '/api/v1/analytics/admin/geographic',
  },

  // Profile
  PROFILE: {
    GET: '/api/profile',
    UPDATE: '/api/profile',
    STYLE_PROFILE: '/api/profile/style',
    BODY_PROFILE: '/api/profile/body',
    BUDGET_PROFILE: '/api/profile/budget',
  },

  // MUSE — Virtual Stylist (v1)
  MUSE: {
    CHAT: '/api/v1/muse/chat',
    HISTORY: (sessionId: string) => `/api/v1/muse/history/${sessionId}`,
    CLEAR_SESSION: (sessionId: string) => `/api/v1/muse/session/${sessionId}`,
  },

  // MIRROR — Virtual Try-On (v1)
  MIRROR: {
    TRY_ON: '/api/v1/mirror/try-on',
    RESULT: (taskId: string) => `/api/v1/mirror/try-on/${taskId}`,
    SESSIONS: '/api/v1/mirror/sessions',
    DELETE_DATA: '/api/v1/mirror/data',
  },

  // SNAP & STYLE — Visual Search (v1)
  VISUAL_SEARCH: {
    BY_IMAGE: '/api/v1/search/visual',
    BY_TEXT: '/api/v1/search/text',
  },

  // MY CLOSET — Virtual Wardrobe (v1)
  CLOSET: {
    ITEMS: '/api/v1/closet/items',
    ITEM_DETAIL: (id: string) => `/api/v1/closet/items/${id}`,
    SUGGESTIONS: '/api/v1/closet/suggestions',
    CHECK_DUPLICATE: '/api/v1/closet/check-duplicate',
  },

  // AI Admin — Cost Dashboard (v1)
  AI_ADMIN: {
    BUDGET: '/api/v1/ai-admin/budget',
    DAILY_REPORT: '/api/v1/ai-admin/daily-report',
    COST_REPORT: '/api/v1/ai-admin/cost-report',
    KILL_SWITCH: '/api/v1/ai-admin/kill-switch',
    USER_COSTS: '/api/v1/ai-admin/user-costs',
  },

  // Health
  HEALTH: '/api/health',
} as const;
