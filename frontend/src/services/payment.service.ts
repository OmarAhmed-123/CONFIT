/**
 * CONFIT Payment Service
 * Handles Stripe Checkout, Paymob, Fawry, and payment operations
 * 
 * Egypt Payment Stack:
 *   - Paymob: Cards, Meeza, InstaPay, Valu BNPL
 *   - Fawry: COD, Cards, Wallets, Kiosk
 *   - Stripe: International customers only
 */

import { api } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import type { PaymentIntent, CheckoutSession, BNPLPlan, Order } from '@/types';

// ===========================================
// Types
// ===========================================

export type EgyptPaymentProvider = 'paymob' | 'fawry' | 'valu' | 'cash_on_delivery';
export type FawryPaymentMethod = 'CARD' | 'CASH_ON_DELIVERY' | 'WALLET' | 'FAWRY_REF_NUMBER';
export type PaymobPaymentMethod = 'card' | 'card_3ds' | 'meeza' | 'instapay' | 'valu';

export interface CreateCheckoutSessionRequest {
  order_id: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CreatePaymentIntentRequest {
  order_id: string;
}

export interface CreateEgyptPaymentRequest {
  order_id: string;
  provider: EgyptPaymentProvider;
  billing?: {
    email?: string;
    phone?: string;
    first_name?: string;
    last_name?: string;
    country?: string;
    city?: string;
    street?: string;
    postal_code?: string;
  };
  // Fawry-specific
  payment_method?: FawryPaymentMethod;
  wallet_number?: string;
  delivery_address?: Record<string, string>;
  // Valu-specific
  tenor?: 6 | 9 | 12 | 18 | 24;
  // Idempotency
  idempotency_key?: string;
}

export interface ConfirmPaymentRequest {
  order_id: string;
  payment_intent_id?: string;
  payment_success?: boolean;
}

export interface BNPLPlanRequest {
  total_amount: number;
  installments?: number;
  annual_interest_rate?: number;
  currency?: string;
}

export interface PaymentConfig {
  stripe_enabled: boolean;
  publishable_key: string | null;
  paymob_enabled: boolean;
  paymob_iframe_ready: boolean;
  paymob_iframe_url: string | null;
  paymob_integration_ids: {
    card: string | null;
    card_3ds: string | null;
    meeza: string | null;
    instapay: string | null;
    valu: string | null;
  };
  fawry_enabled: boolean;
  fawry_merchant_code: string | null;
  paypal_enabled: boolean;
  paypal_client_id: string | null;
  default_currency: string;
  stripe_use_case: 'international_customers_only' | 'disabled' | 'all';
}

export interface EgyptPaymentResponse {
  payment_record_id: string;
  provider: string;
  status: string;
  // Paymob
  payment_key?: string;
  iframe_url?: string;
  paymob_order_id?: string;
  // Fawry
  reference_number?: string;
  fawry_reference?: string;
  redirect_url?: string;
  instructions?: string;
  // Valu
  tenor_months?: number;
  monthly_installment_egp?: number;
  installment_schedule?: Array<{ month: number; amount_egp: number }>;
}

// ===========================================
// Payment Service
// ===========================================

export const paymentService = {
  /**
   * Get payment configuration (publishable keys, feature flags)
   */
  async getConfig(): Promise<PaymentConfig> {
    return api.get<PaymentConfig>(API_ENDPOINTS.PAYMENTS.CONFIG);
  },

  /**
   * Create Stripe Checkout Session
   * This redirects to Stripe's hosted checkout page
   */
  async createCheckoutSession(
    orderId: string,
    options?: { successUrl?: string; cancelUrl?: string }
  ): Promise<CheckoutSession> {
    const request: CreateCheckoutSessionRequest = {
      order_id: orderId,
      success_url: options?.successUrl || `${window.location.origin}/checkout/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: options?.cancelUrl || `${window.location.origin}/checkout/cancel`,
    };

    return api.post<CheckoutSession>(API_ENDPOINTS.PAYMENTS.CHECKOUT_SESSION, request);
  },

  /**
   * Create PaymentIntent for embedded payment element
   * Use this for custom checkout flows (not Stripe-hosted)
   */
  async createPaymentIntent(orderId: string): Promise<PaymentIntent> {
    return api.post<PaymentIntent>(API_ENDPOINTS.PAYMENTS.INTENT, {
      order_id: orderId,
    });
  },

  /**
   * Confirm payment success
   * Validates payment with backend after Stripe confirmation
   */
  async confirmPayment(request: ConfirmPaymentRequest): Promise<{ success: boolean; order?: Order }> {
    return api.post<{ success: boolean; order?: Order }>(
      API_ENDPOINTS.PAYMENTS.CONFIRM,
      request
    );
  },

  /**
   * Calculate BNPL installment plan
   */
  async calculateBNPLPlan(request: BNPLPlanRequest): Promise<BNPLPlan> {
    return api.post<BNPLPlan>(API_ENDPOINTS.PAYMENTS.BNPL_PLAN, {
      total_amount: request.total_amount,
      installments: request.installments || 4,
      annual_interest_rate: request.annual_interest_rate || 0,
      currency: request.currency || 'EGP',
    });
  },

  /**
   * Create Egypt payment session (Paymob, Fawry, Valu, COD)
   */
  async createEgyptPayment(request: CreateEgyptPaymentRequest): Promise<EgyptPaymentResponse> {
    const headers: Record<string, string> = {};
    if (request.idempotency_key) {
      headers['X-Idempotency-Key'] = request.idempotency_key;
    }
    
    return api.post<EgyptPaymentResponse>(
      '/api/payments/unified/session',
      {
        order_id: request.order_id,
        provider: request.provider,
        billing: request.billing,
        payment_method: request.payment_method,
        tenor: request.tenor,
      },
      { headers }
    );
  },

  /**
   * Check Valu BNPL eligibility
   */
  async checkValuEligibility(
    phone: string,
    amountPiastres: number,
    tenor?: 6 | 9 | 12 | 18 | 24
  ): Promise<{
    eligible: boolean;
    max_amount_egp: number;
    available_tenors: number[];
    reason?: string;
  }> {
    return api.post('/api/payments/valu/eligibility', {
      phone,
      amount_piastres: amountPiastres,
      tenor,
    });
  },

  /**
   * Get Fawry reference number status
   */
  async getFawryStatus(referenceNumber: string): Promise<{
    status: string;
    amount: number;
    expires_at?: string;
  }> {
    return api.get(`/api/payments/fawry/status/${referenceNumber}`);
  },

  /**
   * Redirect to Stripe Checkout
   * Call this after creating a checkout session
   */
  redirectToCheckout(sessionId: string): never {
    // This should be called from client-side with Stripe.js
    // The actual redirect happens via Stripe.js
    throw new Error('Use Stripe.js redirectToCheckout on the client side');
  },

  /**
   * Open Paymob iframe for payment
   */
  openPaymobIframe(iframeUrl: string): void {
    window.location.href = iframeUrl;
  },

  /**
   * Open Fawry redirect for 3DS card payment
   */
  openFawryRedirect(redirectUrl: string): void {
    window.location.href = redirectUrl;
  },
};
