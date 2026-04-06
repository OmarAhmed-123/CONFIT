/**
 * CONFIT CARE Donation System Service
 * Handles donor campaigns, beneficiaries, and vouchers
 */

import { api } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import type { DonationCampaign, Beneficiary as BaseBeneficiary, Voucher as BaseVoucher } from '@/types';

// ===========================================
// Types
// ===========================================

export interface CreateCampaignRequest {
  title: string;
  description?: string;
  target_amount: number;
  currency?: string;
  start_date?: string;
  end_date?: string;
}

export interface UpdateCampaignRequest {
  title?: string;
  description?: string;
  target_amount?: number;
  status?: 'draft' | 'active' | 'paused' | 'completed' | 'cancelled';
  end_date?: string;
}

export interface CreateBeneficiaryRequest {
  name: string;
  email?: string;
  phone?: string;
  budget_cap: number;
  currency?: string;
  restrictions?: string[];
}

export interface CreateVoucherRequest {
  beneficiary_id?: string;
  amount: number;
  currency?: string;
  expires_at?: string;
}

export interface ValidateVoucherRequest {
  code: string;
  order_total: number;
}

export interface RedeemVoucherRequest {
  code: string;
  order_id: string;
  amount: number;
}

export interface CampaignStats {
  total_donated: number;
  total_spent: number;
  total_beneficiaries: number;
  active_vouchers: number;
  recent_transactions: Transaction[];
}

export interface Transaction {
  id: string;
  type: 'donation' | 'redemption' | 'refund';
  amount: number;
  currency: string;
  voucher_code?: string;
  beneficiary_name?: string;
  created_at: string;
}

export interface DonorDashboard {
  total_campaigns: number;
  total_donated: number;
  total_impact: number;
  active_beneficiaries: number;
  campaigns: DonationCampaign[];
  recent_activity: Transaction[];
  total_beneficiaries_supported?: number;
  total_impact_value?: number;
  currency?: string;
  recent_campaigns?: Campaign[];
  recent_orders?: CareOrder[];
  spending_by_category?: Record<string, number>;
}

// Extended types for new CARE system
export interface Campaign {
  id: string;
  campaign_name: string;
  campaign_type: string;
  status: string;
  total_beneficiaries: number;
  total_budget_allocated: number;
  total_budget_used: number;
  engagement_rate: number;
  completion_rate: number;
  created_at: string;
  end_date?: string;
  donor_id?: string;
  description?: string;
  currency?: string;
  allowed_categories?: string[];
  excluded_brands?: string[];
}

export interface Voucher {
  id: string;
  voucher_token: string;
  campaign_id: string;
  beneficiary_id?: string;
  budget_allocated: number;
  budget_used: number;
  budget_remaining: number;
  currency: string;
  status: string;
  expires_at: string;
  accessed_at?: string;
  code?: string;
  amount?: number;
  balance?: number;
}

export interface Session {
  id: string;
  session_token: string;
  voucher_id: string;
  status: string;
  expires_at: string;
  otp_verified: boolean;
  created_at: string;
}

export interface CareOrder {
  id: string;
  order_id: string;
  voucher_id: string;
  beneficiary_id: string;
  total_amount: number;
  items_count: number;
  status: string;
  created_at: string;
}

export interface Beneficiary extends BaseBeneficiary {
  id: string;
  campaign_id: string;
  name: string;
  email?: string;
  phone?: string;
  budget_allocated: number;
  budget_used: number;
  budget_remaining: number;
  is_active: boolean;
}

export interface SessionContext {
  session: Session;
  voucher: Voucher;
  beneficiary: Beneficiary;
  campaign: Campaign;
  budget_remaining: number;
  allowed_categories?: string[];
  excluded_brands?: string[];
  occasion_filter?: string;
}

// ===========================================
// CARE Service
// ===========================================

export const careService = {
  // ===========================================
  // Campaign Operations
  // ===========================================

  /**
   * Get donor dashboard summary
   */
  async getDonorDashboard(): Promise<DonorDashboard> {
    return api.get<DonorDashboard>(API_ENDPOINTS.CARE.DONOR_DASHBOARD);
  },

  /**
   * Get all campaigns for current donor
   */
  async getDonorCampaigns(): Promise<DonationCampaign[]> {
    return api.get<DonationCampaign[]>(API_ENDPOINTS.CARE.DONOR_CAMPAIGNS);
  },

  /**
   * Get all campaigns (public)
   */
  async getCampaigns(): Promise<DonationCampaign[]> {
    return api.get<DonationCampaign[]>(API_ENDPOINTS.CARE.CAMPAIGNS);
  },

  /**
   * Get campaign details
   */
  async getCampaign(campaignId: string): Promise<DonationCampaign> {
    return api.get<DonationCampaign>(API_ENDPOINTS.CARE.CAMPAIGN_DETAIL(campaignId));
  },

  /**
   * Create a new donation campaign
   */
  async createCampaign(data: CreateCampaignRequest): Promise<DonationCampaign> {
    return api.post<DonationCampaign>(API_ENDPOINTS.CARE.CAMPAIGNS, data);
  },

  /**
   * Update campaign
   */
  async updateCampaign(campaignId: string, data: UpdateCampaignRequest): Promise<DonationCampaign> {
    return api.patch<DonationCampaign>(API_ENDPOINTS.CARE.CAMPAIGN_UPDATE(campaignId), data);
  },

  /**
   * Get campaign statistics
   */
  async getCampaignStats(campaignId: string): Promise<CampaignStats> {
    return api.get<CampaignStats>(API_ENDPOINTS.CARE.CAMPAIGN_STATS(campaignId));
  },

  // ===========================================
  // Beneficiary Operations
  // ===========================================

  /**
   * Get all beneficiaries for a campaign
   */
  async getBeneficiaries(campaignId: string): Promise<Beneficiary[]> {
    return api.get<Beneficiary[]>(API_ENDPOINTS.CARE.BENEFICIARIES(campaignId));
  },

  /**
   * Add beneficiary to campaign
   */
  async addBeneficiary(campaignId: string, data: CreateBeneficiaryRequest): Promise<Beneficiary> {
    return api.post<Beneficiary>(API_ENDPOINTS.CARE.BENEFICIARIES(campaignId), data);
  },

  /**
   * Update beneficiary
   */
  async updateBeneficiary(
    campaignId: string,
    beneficiaryId: string,
    data: Partial<CreateBeneficiaryRequest>
  ): Promise<Beneficiary> {
    return api.patch<Beneficiary>(
      API_ENDPOINTS.CARE.BENEFICIARY_DETAIL(campaignId, beneficiaryId),
      data
    );
  },

  /**
   * Remove beneficiary
   */
  async removeBeneficiary(campaignId: string, beneficiaryId: string): Promise<void> {
    await api.delete(API_ENDPOINTS.CARE.BENEFICIARY_DETAIL(campaignId, beneficiaryId));
  },

  // ===========================================
  // Voucher Operations
  // ===========================================

  /**
   * Get all vouchers for a campaign
   */
  async getVouchers(campaignId: string): Promise<Voucher[]> {
    return api.get<Voucher[]>(API_ENDPOINTS.CARE.VOUCHERS(campaignId));
  },

  /**
   * Create voucher(s) for campaign
   */
  async createVouchers(campaignId: string, vouchers: CreateVoucherRequest[]): Promise<Voucher[]> {
    return api.post<Voucher[]>(API_ENDPOINTS.CARE.VOUCHERS(campaignId), { vouchers });
  },

  /**
   * Validate voucher code
   */
  async validateVoucher(code: string, orderTotal: number): Promise<{
    valid: boolean;
    voucher?: Voucher;
    max_usable?: number;
    message?: string;
  }> {
    return api.post(API_ENDPOINTS.CARE.VOUCHER_VALIDATE, {
      code,
      order_total: orderTotal,
    });
  },

  /**
   * Redeem voucher for order
   */
  async redeemVoucher(request: RedeemVoucherRequest): Promise<{
    success: boolean;
    amount_applied: number;
    new_balance: number;
    voucher: Voucher;
  }> {
    return api.post(API_ENDPOINTS.CARE.VOUCHER_REDEEM, request);
  },

  // ===========================================
  // Beneficiary Session Operations (New)
  // ===========================================

  /**
   * Validate voucher token (beneficiary entry)
   */
  async validateVoucherToken(voucherToken: string): Promise<Voucher> {
    return api.post('/api/care/vouchers/validate', { voucher_token: voucherToken });
  },

  /**
   * Initiate beneficiary session
   */
  async initiateSession(voucherToken: string): Promise<Session> {
    return api.post('/api/care/session/initiate', { voucher_token: voucherToken });
  },

  /**
   * Send OTP to beneficiary
   */
  async sendOTP(sessionId: string): Promise<{ message: string }> {
    return api.post(`/api/care/session/${sessionId}/otp/send`);
  },

  /**
   * Verify OTP code
   */
  async verifyOTP(sessionId: string, otpCode: string): Promise<Session> {
    return api.post(`/api/care/session/${sessionId}/otp/verify`, { otp_code: otpCode });
  },

  /**
   * Get session context (for authenticated beneficiary)
   */
  async getSessionContext(sessionToken: string): Promise<SessionContext> {
    return api.get(`/api/care/session/${sessionToken}/context`);
  },

  /**
   * Update session cart
   */
  async updateSessionCart(sessionToken: string, cartData: any): Promise<{ message: string }> {
    return api.post(`/api/care/session/${sessionToken}/cart`, cartData);
  },

  /**
   * Create care order
   */
  async createCareOrder(sessionToken: string, orderData: any): Promise<CareOrder> {
    return api.post('/api/care/orders', { session_id: sessionToken, ...orderData });
  },

  /**
   * Get care order by ID
   */
  async getCareOrder(orderId: string): Promise<CareOrder> {
    return api.get(`/api/care/orders/${orderId}`);
  },

  /**
   * Activate campaign with beneficiaries
   */
  async activateCampaign(campaignId: string, data: { beneficiaries: any[]; send_invitations: boolean }): Promise<Campaign> {
    return api.post(`/api/care/campaigns/${campaignId}/activate`, data);
  },

  /**
   * Delete campaign
   */
  async deleteCampaign(campaignId: string): Promise<void> {
    await api.delete(`/api/care/campaigns/${campaignId}`);
  },

  /**
   * Generate campaign report
   */
  async generateReport(campaignId: string, params: { report_type: string; format: string }): Promise<{
    report_id: string;
    download_url: string;
    generated_at: string;
  }> {
    return api.post(`/api/care/campaigns/${campaignId}/report`, params);
  },

  /**
   * Get campaign analytics
   */
  async getCampaignAnalytics(campaignId: string): Promise<any> {
    return api.get(`/api/care/campaigns/${campaignId}/analytics`);
  },

  /**
   * Get campaign audit log
   */
  async getCampaignAuditLog(campaignId: string, actionCategory?: string): Promise<any> {
    const query = actionCategory ? `?action_category=${actionCategory}` : '';
    return api.get(`/api/care/campaigns/${campaignId}/audit-log${query}`);
  },
};
