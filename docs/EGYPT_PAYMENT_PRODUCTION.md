# Egypt Payment Stack - Production Configuration

This guide covers production deployment of Egypt payment providers for CONFIT.

## Overview

CONFIT uses Egypt-specific payment providers optimized for local customers:

| Provider | Use Case | Market Share |
|----------|----------|--------------|
| **Paymob** | Cards, Meeza, InstaPay, Valu BNPL | Primary gateway |
| **Fawry** | COD, Cards, Wallets, Kiosk | 40%+ of Egypt e-commerce |
| **Stripe** | International customers only | Non-EGP transactions |

## Required Environment Variables

### Paymob Configuration

```bash
# Primary Paymob credentials
PAYMOB_API_KEY=<your-production-api-key>
PAYMOB_HMAC_SECRET=<your-hmac-secret>
PAYMOB_SECRET_KEY=egy_sk_live_<your-secret-key>
PAYMOB_PUBLIC_KEY=egy_pk_live_<your-public-key>
PAYMOB_IFRAME_ID=<your-iframe-id>

# Integration IDs (get from Paymob dashboard)
PAYMOB_INTEGRATION_ID=<card-integration-id>
PAYMOB_INTEGRATION_ID_3DS=<3ds-integration-id>
PAYMOB_INTEGRATION_ID_MEEZA=<meeza-integration-id>
PAYMOB_INTEGRATION_ID_INSTAPAY=<instapay-integration-id>
PAYMOB_INTEGRATION_ID_VALU=<valu-bnpl-integration-id>

# Optional: Custom base URL (default: https://accept.paymob.com/api)
PAYMOB_BASE_URL=https://accept.paymob.com/api
PAYMOB_IFRAME_URL=https://accept.paymob.com/api/acceptance/iframes
```

### Fawry Configuration

```bash
# Fawry credentials
FAWRY_ENVIRONMENT=production
FAWRY_MERCHANT_CODE=<your-merchant-code>
FAWRY_SECURITY_KEY=<your-security-key>
FAWRY_CALLBACK_URL=https://api.confit.app/api/payments/unified/webhooks/fawry
```

### Stripe Configuration (International Only)

```bash
# Stripe for international customers
STRIPE_SECRET_KEY=sk_live_<your-secret-key>
STRIPE_PUBLISHABLE_KEY=pk_live_<your-publishable-key>
STRIPE_WEBHOOK_SECRET=whsec_<your-webhook-secret>

# Stripe routing for Egypt
STRIPE_USE_CASE=international_customers_only
```

### Currency Settings

```bash
# Default currency for Egypt
STOREFRONT_DEFAULT_CURRENCY=EGP
```

## Webhook Configuration

### Production Webhook URLs

Configure these URLs in each provider's dashboard:

| Provider | Webhook URL |
|----------|-------------|
| Paymob | `https://api.confit.app/api/payments/unified/webhooks/paymob` |
| Fawry | `https://api.confit.app/api/payments/unified/webhooks/fawry` |
| Valu | `https://api.confit.app/api/payments/unified/webhooks/valu` |
| PayPal | `https://api.confit.app/api/payments/unified/webhooks/paypal` |
| Stripe | `https://api.confit.app/api/payments/unified/webhooks/stripe` |

### Webhook Security

- **Paymob**: HMAC SHA512 signature verification
- **Fawry**: MD5 hash signature verification
- **Valu**: Routed through Paymob (same HMAC)
- **Stripe**: Stripe signature verification
- **PayPal**: PayPal webhook ID verification

## Database Migration

Run the Egypt payment stack migration before deploying:

```bash
cd backend
alembic upgrade head
```

This adds:
- `tax_amount_cents` column to `payments` table
- New payment providers: `fawry`, `valu`, `cash_on_delivery`
- New payment status: `pending_cod`
- Default currency changed to `egp`

## Payment Flow by Method

### 1. Card Payment (Paymob)

```
1. Frontend calls /api/payments/unified/session with provider=paymob
2. Backend creates Paymob order and payment key
3. Frontend redirects to Paymob iframe URL
4. User completes 3DS authentication
5. Paymob webhook confirms payment
6. Order status updated to "paid"
```

### 2. Meeza Card (Paymob)

```
Same as card, but with PAYMOB_INTEGRATION_ID_MEEZA
```

### 3. InstaPay (Paymob)

```
1. Frontend calls /api/payments/unified/session with provider=paymob, payment_method=instapay
2. Backend creates order with InstaPay integration ID
3. User redirected to bank selection
4. Bank transfer completed
5. Webhook confirms payment
```

### 4. Valu BNPL (Paymob)

```
1. Frontend checks eligibility via /api/payments/valu/eligibility
2. User selects installment tenor (6, 9, 12, 18, 24 months)
3. Frontend calls /api/payments/unified/session with provider=valu, tenor=<months>
4. Backend creates Valu charge via Paymob
5. User completes Valu authentication
6. Webhook confirms BNPL approval
7. Installment schedule displayed to user
```

### 5. Cash on Delivery (Fawry)

```
1. Frontend calls /api/payments/unified/session with provider=fawry, payment_method=CASH_ON_DELIVERY
2. Backend creates COD charge with Fawry
3. Payment status set to "pending_cod"
4. Order dispatched to courier
5. Courier collects cash on delivery
6. Backend manually updates payment to "succeeded" after confirmation
```

### 6. Fawry Kiosk/ATM

```
1. Frontend calls /api/payments/unified/session with provider=fawry, payment_method=FAWRY_REF_NUMBER
2. Backend creates charge, returns reference number
3. Frontend displays reference number to user
4. User pays at Fawry kiosk/ATM within 24 hours
5. Fawry webhook confirms payment
6. Order status updated to "paid"
```

### 7. Mobile Wallet (Fawry)

```
1. Frontend calls /api/payments/unified/session with provider=fawry, payment_method=WALLET, wallet_number=<number>
2. Backend creates wallet charge
3. User confirms on mobile wallet app
4. Fawry webhook confirms payment
```

## Tax Calculation

Egypt VAT (14%) is automatically calculated:

```python
from services.tax_service import calculate_egypt_vat

# Amount in piastres (EGP * 100)
result = calculate_egypt_vat(10000)  # 100 EGP

# Returns:
# {
#   "subtotal_piastres": 10000,
#   "vat_piastres": 1400,  # 14 EGP
#   "total_piastres": 11400,  # 114 EGP
#   "vat_rate": 0.14,
#   "country": "EG"
# }
```

## Testing Checklist

### Pre-Launch

- [ ] Paymob HMAC verification working
- [ ] Fawry MD5 signature verification working
- [ ] All integration IDs configured
- [ ] Webhook URLs registered in provider dashboards
- [ ] Database migration completed
- [ ] VAT calculation tested
- [ ] COD flow tested end-to-end
- [ ] Valu BNPL eligibility check working

### Production Monitoring

- [ ] Set up alerts for failed payments
- [ ] Monitor webhook delivery rates
- [ ] Track payment method distribution
- [ ] Monitor COD collection rates

## Support Contacts

| Provider | Support |
|----------|---------|
| Paymob | support@paymob.com |
| Fawry | support@fawry.com |
| Valu | support@valu.eg |

## Security Notes

1. **Never log card numbers or CVV** - Masked in all logs
2. **Always verify webhook signatures** - Reject unsigned requests
3. **Use idempotency keys** - Prevent duplicate charges
4. **Store amounts as piastres** - Avoid floating-point errors
5. **HTTPS only** - All payment endpoints require TLS
