/**
 * CONFIT Frontend — AI Features Service
 * ======================================
 * Client-side integration for MUSE, MIRROR, SNAP & STYLE, MY CLOSET.
 * Connects to /api/v1/* endpoints.
 */

import { api, API_BASE_URL, getAccessToken } from '@/lib/api/client';

// ═══════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════

// ── MUSE ────────────────────────────────────────────────────────────

export interface MuseOutfitItem {
  sku: string;
  name: string;
  brand?: string;
  price?: number;
  image_url?: string;
}

export interface MuseOutfit {
  outfit_id: string;
  title: string;
  items: MuseOutfitItem[];
  total_price: number;
  occasion?: string;
  styling_tips: string[];
  from_closet: string[];
  from_catalog: string[];
}

export interface MuseChatRequest {
  message: string;
  language?: 'en' | 'ar';
  session_id?: string;
}

export interface MuseChatResponse {
  reply: string;
  outfits: MuseOutfit[];
  follow_ups: string[];
  session_id: string;
  tokens_used: number;
  cost_usd: number;
}

export interface MuseSessionHistory {
  session_id: string;
  messages: { role: string; content: string; timestamp?: string }[];
}

// ── MIRROR ──────────────────────────────────────────────────────────

export interface MirrorTryOnStartResponse {
  task_id: string;
  status: 'queued';
}

export interface MirrorTryOnResult {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result_image_url?: string;
  fit_score: number;
  processing_time_ms: number;
  error_message?: string;
}

export interface MirrorSessionSummary {
  session_id: string;
  product_id: string;
  status: string;
  created_at: string;
  result_image_url?: string;
}

// ── SNAP & STYLE ────────────────────────────────────────────────────

export interface VisualSearchAttributes {
  type?: string;
  color: string[];
  style: string[];
  pattern: string[];
}

export interface VisualSearchMatch {
  product_id: string;
  sku?: string;
  name: string;
  brand?: string;
  price?: number;
  currency: string;
  image_url?: string;
  similarity_score: number;
  matched_attributes: string[];
}

export interface VisualSearchResponse {
  session_id: string;
  attributes: VisualSearchAttributes;
  matches: VisualSearchMatch[];
  total_results: number;
  processing_time_ms: number;
}

export interface TextSearchResponse {
  results: VisualSearchMatch[];
  total_results: number;
}

// ── MY CLOSET ───────────────────────────────────────────────────────

export interface ClosetItem {
  id: string;
  name: string;
  category: string;
  subcategory?: string;
  colors: string[];
  patterns: string[];
  materials: string[];
  brands: string[];
  tags: string[];
  image_url?: string;
  purchase_price?: number;
  times_worn: number;
  is_favorite: boolean;
  created_at: string;
}

export interface ClosetOutfitItem {
  item_id: string;
  name: string;
  category: string;
  color?: string;
  image_url?: string;
  source: 'closet' | 'catalog';
  sku?: string;
}

export interface ClosetOutfitSuggestion {
  outfit_id: string;
  name: string;
  items: ClosetOutfitItem[];
  occasion?: string;
  style_match_score: number;
  color_harmony_score: number;
  tips: string[];
}

export interface DuplicateAlert {
  has_duplicate: boolean;
  similarity_score: number;
  existing_item?: ClosetItem;
  message: string;
}

// ── AI ADMIN ────────────────────────────────────────────────────────

export interface AIBudgetStatus {
  daily_budget_usd: number;
  spent_usd: number;
  remaining_usd: number;
  percent_used: number;
  is_warning: boolean;
  is_exceeded: boolean;
  kill_switch_active: boolean;
}

export interface AIServiceCostSummary {
  service: string;
  total_cost_usd: number;
  total_calls: number;
  total_tokens_in: number;
  total_tokens_out: number;
  avg_latency_ms: number;
  success_rate: number;
  unique_users: number;
}

export interface AIDailyReport {
  date: string;
  total_cost_usd: number;
  total_calls: number;
  services: AIServiceCostSummary[];
}

// ═══════════════════════════════════════════════════════════════════
// MUSE SERVICE
// ═══════════════════════════════════════════════════════════════════

export const museService = {
  /** Chat with MUSE AI stylist */
  chat: (payload: MuseChatRequest) =>
    api.post<MuseChatResponse>('/api/v1/muse/chat', payload),

  /** Get session conversation history */
  getHistory: (sessionId: string) =>
    api.get<MuseSessionHistory>(`/api/v1/muse/history/${sessionId}`),

  /** Clear a session */
  clearSession: (sessionId: string) =>
    api.delete<{ success: boolean }>(`/api/v1/muse/session/${sessionId}`),
};

// ═══════════════════════════════════════════════════════════════════
// MIRROR SERVICE
// ═══════════════════════════════════════════════════════════════════

export const mirrorService = {
  /** Start a virtual try-on (returns task_id for polling) */
  startTryOn: async (
    userPhoto: File,
    productVariantId: string,
    category: string = 'upper_body'
  ): Promise<MirrorTryOnStartResponse> => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append('user_photo', userPhoto);
    formData.append('product_variant_id', productVariantId);
    formData.append('category', category);

    const response = await fetch(`${API_BASE_URL}/api/v1/mirror/try-on`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData?.detail?.message || errorData?.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  /** Poll for try-on result */
  getResult: (taskId: string) =>
    api.get<MirrorTryOnResult>(`/api/v1/mirror/try-on/${taskId}`),

  /** List user's try-on sessions */
  getSessions: (limit = 20) =>
    api.get<MirrorSessionSummary[]>(`/api/v1/mirror/sessions?limit=${limit}`),

  /** GDPR: Delete all user try-on data */
  deleteUserData: () =>
    api.delete<{ success: boolean }>('/api/v1/mirror/data'),

  /** Helper: Poll until result is ready */
  pollUntilReady: async (
    taskId: string,
    onProgress?: (status: string) => void,
    maxAttempts = 60,
    intervalMs = 2000
  ): Promise<MirrorTryOnResult> => {
    for (let i = 0; i < maxAttempts; i++) {
      const result = await mirrorService.getResult(taskId);
      onProgress?.(result.status);

      if (result.status === 'completed' || result.status === 'failed') {
        return result;
      }

      await new Promise((r) => setTimeout(r, intervalMs));
    }

    return {
      task_id: taskId,
      status: 'failed',
      fit_score: 0,
      processing_time_ms: 0,
      error_message: 'Timeout waiting for result',
    };
  },
};

// ═══════════════════════════════════════════════════════════════════
// SNAP & STYLE SERVICE
// ═══════════════════════════════════════════════════════════════════

export const visualSearchService = {
  /** Search by uploaded image */
  searchByImage: async (
    file: File,
    limit = 20,
    category?: string
  ): Promise<VisualSearchResponse> => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    params.set('limit', String(limit));
    if (category) params.set('category', category);

    const response = await fetch(
      `${API_BASE_URL}/api/v1/search/visual?${params}`,
      {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData?.detail?.message || errorData?.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  /** Search by text query */
  searchByText: (query: string, limit = 20, category?: string) => {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    if (category) params.set('category', category);
    return api.get<TextSearchResponse>(`/api/v1/search/text?${params}`);
  },
};

// ═══════════════════════════════════════════════════════════════════
// MY CLOSET SERVICE
// ═══════════════════════════════════════════════════════════════════

export const closetService = {
  /** Upload a photo to add to closet */
  uploadItem: async (
    photo: File,
    name?: string
  ): Promise<ClosetItem> => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append('photo', photo);
    if (name) formData.append('name', name);

    const response = await fetch(`${API_BASE_URL}/api/v1/closet/items`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData?.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  /** List closet items */
  getItems: (category?: string, search?: string) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (search) params.set('search', search);
    const qs = params.toString();
    return api.get<ClosetItem[]>(`/api/v1/closet/items${qs ? `?${qs}` : ''}`);
  },

  /** Get outfit suggestions mixing closet + catalog */
  getSuggestions: (occasion?: string) => {
    const params = new URLSearchParams();
    if (occasion) params.set('occasion', occasion);
    const qs = params.toString();
    return api.get<ClosetOutfitSuggestion[]>(`/api/v1/closet/suggestions${qs ? `?${qs}` : ''}`);
  },

  /** Check for duplicate purchase before checkout */
  checkDuplicate: (data: {
    product_name: string;
    category?: string;
    color?: string;
    product_sku?: string;
  }) => api.post<DuplicateAlert>('/api/v1/closet/check-duplicate', data),

  /** Delete a closet item */
  deleteItem: (itemId: string) =>
    api.delete<{ success: boolean }>(`/api/v1/closet/items/${itemId}`),
};

// ═══════════════════════════════════════════════════════════════════
// AI ADMIN SERVICE
// ═══════════════════════════════════════════════════════════════════

export const aiAdminService = {
  /** Get current budget status */
  getBudgetStatus: () =>
    api.get<AIBudgetStatus>('/api/v1/ai-admin/budget'),

  /** Get 24h aggregate cost report */
  getDailyReport: (date?: string) =>
    api.get<AIDailyReport>(`/api/v1/ai-admin/daily-report${date ? `?target_date=${date}` : ''}`),

  /** Get custom range cost report */
  getCostReport: (startDate: string, endDate: string, groupBy = 'service') =>
    api.get<any>(`/api/v1/ai-admin/cost-report?start_date=${startDate}&end_date=${endDate}&group_by=${groupBy}`),

  /** Toggle kill-switch */
  toggleKillSwitch: (activate: boolean) =>
    api.post<{ kill_switch: string; message: string }>('/api/v1/ai-admin/kill-switch', { activate }),

  /** Get per-user cost history */
  getUserCosts: (userId: string, limit = 100) =>
    api.get<any[]>(`/api/v1/ai-admin/user-costs?user_id=${userId}&limit=${limit}`),
};
