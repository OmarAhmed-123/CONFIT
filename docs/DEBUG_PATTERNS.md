# Payment Integration Debug Patterns
=====================================
Diagnostic signatures for common payment flow failures in CONFIT.
Use this guide to identify and fix issues in Paymob and PayPal integrations.

---

## Table of Contents
1. [CORS Misconfiguration](#cors-misconfiguration)
2. [Missing or Broken Paymob Iframe](#missing-or-broken-paymob-iframe)
3. [PayPal SDK Not Loading](#paypal-sdk-not-loading)
4. [SSL/Certificate Errors](#sslcertificate-errors)
5. [API Rate Limiting](#api-rate-limiting)
6. [Sandbox vs Production Key Mismatch](#sandbox-vs-production-key-mismatch)
7. [HMAC Verification Failures](#hmac-verification-failures)
8. [OAuth Token Failures](#oauth-token-failures)

---

## CORS Misconfiguration

### Symptoms
- Frontend requests to `/api/payments/*` fail with network errors
- Browser console shows: `Access to fetch at '...' from origin '...' has been blocked by CORS policy`
- Preflight OPTIONS requests return 403 or 400

### How It Appears in Logs/Dashboard
```json
{
  "error_type": "cors",
  "url": "https://api.example.com/api/payments/unified/session",
  "message": "CORS policy blocked the request",
  "status_code": null
}
```

### Dashboard Indicators
- **CORS & SSL Issues panel**: Shows entries with `issue_type: "cors"`
- **Transaction Logs**: Request shows `status_code: null` and `error` contains "CORS"

### Common Causes
1. `FRONTEND_URL` env var doesn't match actual frontend origin
2. `CORS_ORIGINS` not set correctly in production
3. Missing `allow_credentials: true` for cookie-based auth
4. Preflight headers not exposed

### Fix
```bash
# backend/.env
FRONTEND_URL=https://your-frontend-domain.com
ALLOWED_ORIGINS=https://api.your-domain.com,https://admin.your-domain.com
```

```python
# In app.py CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID"],
)
```

### Verification
```bash
curl -X OPTIONS https://api.your-domain.com/api/payments/unified/session \
  -H "Origin: https://your-frontend-domain.com" \
  -H "Access-Control-Request-Method: POST" \
  -v
# Should return 200 with Access-Control-Allow-Origin header
```

---

## Missing or Broken Paymob Iframe

### Symptoms
- Paymob iframe shows blank/white screen
- Iframe loads but payment form doesn't render
- Console error: `Refused to display '...' in a frame because of X-Frame-Options`
- Payment key generation succeeds but iframe URL fails

### How It Appears in Logs/Dashboard
```json
{
  "error_type": "iframe",
  "message": "Paymob iframe load timeout after 15000ms",
  "metadata": {
    "iframeUrl": "https://accept.paymob.com/api/acceptance/iframes/1023190?payment_token=...",
    "timeout": 15000
  }
}
```

### Dashboard Indicators
- **Client Errors panel**: Shows `error_type: "iframe"`
- **Performance Metrics**: `iframe_load` shows very high or missing values
- **CORS & SSL Issues**: May show CSP-related blocks

### Common Causes
1. **Missing `PAYMOB_IFRAME_ID`**: The iframe numeric ID is not configured
2. **Invalid payment key**: Token expired or malformed
3. **CSP blocking**: Content Security Policy blocks iframe sources
4. **Empty iframe src**: Frontend didn't receive `iframe_url` from API

### Fix

**Check iframe ID configuration:**
```bash
# backend/.env
PAYMOB_IFRAME_ID=1023190  # Get from Paymob dashboard → Integrations → Iframe ID
```

**Verify payment key in response:**
```json
// API response from /api/payments/unified/session should include:
{
  "provider": "paymob",
  "iframe_url": "https://accept.paymob.com/api/acceptance/iframes/1023190?payment_token=...",
  "public_key": "egy_pk_..."
}
```

**CSP Headers (if applicable):**
```http
Content-Security-Policy: frame-src 'self' https://accept.paymob.com;
```

### Verification
1. Open the iframe URL directly in browser - should show payment form
2. Check `PAYMOB_IFRAME_ID` matches the ID in Paymob dashboard
3. Verify payment key hasn't expired (default 3600 seconds)

---

## PayPal SDK Not Loading

### Symptoms
- PayPal buttons don't render
- Console error: `paypal is not defined`
- Console error: `Script error for paypal SDK`
- Payment page shows "PayPal is not available"

### How It Appears in Logs/Dashboard
```json
{
  "error_type": "sdk",
  "message": "PayPal SDK failed to load within timeout",
  "metadata": {
    "attempts": 30,
    "timeout": 15000,
    "clientId": "A...B"
  }
}
```

### Dashboard Indicators
- **Client Errors panel**: Shows `error_type: "sdk"`
- **Performance Metrics**: `sdk_init` shows no data or very high latency
- **API Key Validation**: PayPal status shows "invalid" or "error"

### Common Causes
1. **Wrong `PAYPAL_CLIENT_ID`**: Sandbox ID used in live mode or vice versa
2. **Script blocked**: Ad blockers or CSP blocking `paypal.com` domains
3. **Network timeout**: Slow connection to PayPal CDN
4. **Invalid client ID format**: Client ID doesn't match expected pattern

### Fix

**Verify client ID matches mode:**
```bash
# Sandbox (test)
PAYPAL_CLIENT_ID=A...test...B
PAYPAL_CLIENT_SECRET=E...test...F
PAYPAL_MODE=sandbox

# Live (production)
PAYPAL_CLIENT_ID=A...live...B
PAYPAL_CLIENT_SECRET=E...live...F
PAYPAL_MODE=live
```

**Check SDK script URL:**
```html
<!-- Should include correct client ID and intent -->
<script src="https://www.paypal.com/sdk/js?client-id=YOUR_CLIENT_ID&intent=capture"></script>
```

**CSP Headers:**
```http
Content-Security-Policy: script-src 'self' 'unsafe-inline' https://www.paypal.com https://www.sandbox.paypal.com;
```

### Verification
```javascript
// In browser console after page load
console.log(window.paypal); // Should show PayPal SDK object
```

---

## SSL/Certificate Errors

### Symptoms
- API requests fail with `net::ERR_CERT_AUTHORITY_INVALID`
- Console shows `SSL certificate problem`
- Webhooks not received from payment providers
- Iframe shows "Your connection is not private"

### How It Appears in Logs/Dashboard
```json
{
  "issue_type": "ssl",
  "url": "https://api.your-domain.com/api/payments/unified/webhooks/paypal",
  "message": "SSL certificate verification failed"
}
```

### Dashboard Indicators
- **CORS & SSL Issues panel**: Shows `issue_type: "ssl"`
- **Transaction Logs**: Error contains "SSL", "certificate", or "TLS"

### Common Causes
1. **Self-signed certificate**: Dev environment using untrusted cert
2. **Expired certificate**: SSL cert has passed expiration date
3. **Wrong hostname**: Certificate issued for different domain
4. **Missing intermediate CA**: Incomplete certificate chain

### Fix

**Development (self-signed):**
```bash
# Accept self-signed cert locally
# Or use mkcert for trusted local certs
mkcert localhost 127.0.0.1
```

**Production:**
```bash
# Check certificate expiration
openssl s_client -connect api.your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

# Renew Let's Encrypt certificate
certbot renew --force-renewal
```

**Webhook URLs:**
- PayPal and Paymob require valid SSL for webhook endpoints
- Use ngrok or similar for local webhook testing

### Verification
```bash
# Test SSL certificate
curl -v https://api.your-domain.com/health
# Should show SSL certificate details without errors
```

---

## API Rate Limiting

### Symptoms
- Sudden spike in 429 responses
- Error message: "Too many requests"
- Intermittent failures during high traffic
- Requests work, then suddenly fail

### How It Appears in Logs/Dashboard
```json
{
  "status_code": 429,
  "response": {
    "body": {
      "error": "rate_limit_exceeded",
      "retry_after": 60
    }
  },
  "error": "HTTP 429: Rate limit exceeded"
}
```

### Dashboard Indicators
- **Transaction Logs**: Multiple entries with `status_code: 429`
- **Success rate drops** significantly during peak times
- **Latency increases** before failures

### Common Causes
1. **Paymob API limits**: Too many auth token requests
2. **PayPal API limits**: Excessive order creation calls
3. **Internal rate limiter**: FastAPI SlowAPI limiting requests
4. **Redis connection issues**: Rate limit counter not resetting

### Fix

**Cache auth tokens (Paymob):**
```python
# Don't request new token for each transaction
# Cache token until it expires (usually 1 hour)
from functools import lru_cache
from datetime import datetime, timedelta

_token_cache = {"token": None, "expires_at": None}

async def get_cached_auth_token():
    if _token_cache["token"] and _token_cache["expires_at"] > datetime.now():
        return _token_cache["token"]
    # Fetch new token...
```

**Adjust internal rate limits:**
```bash
# backend/.env
RATE_LIMIT_DEFAULT=120/minute
RATE_LIMIT_PAYMENTS=60/minute
```

**Handle 429 responses:**
```python
import asyncio
import httpx

async def request_with_retry(client, url, max_retries=3):
    for attempt in range(max_retries):
        response = await client.get(url)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            await asyncio.sleep(retry_after)
            continue
        return response
```

### Verification
```bash
# Check response headers for rate limit info
curl -I https://api.your-domain.com/api/payments/unified/session
# Look for: X-RateLimit-Limit, X-RateLimit-Remaining
```

---

## Sandbox vs Production Key Mismatch

### Symptoms
- Payment works in test but fails in production
- "Invalid credentials" errors despite correct keys
- PayPal shows sandbox UI in production mode
- Paymob rejects live cards with sandbox keys

### How It Appears in Logs/Dashboard
```json
{
  "provider": "paypal",
  "status": "invalid",
  "message": "Client ID is for sandbox but mode is live"
}
```

### Dashboard Indicators
- **API Key Validation panel**: Shows validation failures
- **Environment Status panel**: Shows `PAYPAL_MODE` or provider mode
- **Transaction Logs**: 401/403 responses from provider APIs

### Common Causes
1. **Wrong `PAYPAL_MODE`**: Set to "sandbox" with live credentials
2. **Mixed credentials**: Sandbox client ID with live secret
3. **Environment variable mismatch**: Different values in different environments
4. **Paymob base URL**: Using wrong regional endpoint

### Fix

**Verify mode matches credentials:**
```bash
# For sandbox testing
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=<sandbox-client-id-from-developer.paypal.com>
PAYPAL_CLIENT_SECRET=<sandbox-secret>

# For production
PAYPAL_MODE=live
PAYPAL_CLIENT_ID=<live-client-id>
PAYPAL_CLIENT_SECRET=<live-secret>
```

**Paymob regional endpoints:**
```bash
# Egypt (default)
PAYMOB_BASE_URL=https://accept.paymob.com/api

# Other regions may have different base URLs
# Check your Paymob dashboard for the correct endpoint
```

### Verification
```bash
# Run the test scenario from dashboard
# POST /debug/test-scenarios/paypal
# POST /debug/test-scenarios/paymob

# Check the Environment Status panel
# All provider variables should be present and valid_format: true
```

---

## HMAC Verification Failures

### Symptoms
- Paymob webhooks return 403 "Invalid HMAC"
- Payment confirmed on frontend but webhook rejected
- Logs show "HMAC verification failed"

### How It Appears in Logs/Dashboard
```json
{
  "status_code": 403,
  "error": "Invalid HMAC",
  "request": {
    "payload": {
      "hmac": "abc123...",
      "obj": {...}
    }
  }
}
```

### Dashboard Indicators
- **Transaction Logs**: Webhook requests with `status_code: 403`
- **Error message**: "Invalid HMAC" in response body

### Common Causes
1. **Missing `PAYMOB_HMAC_SECRET`**: Not configured in environment
2. **Wrong HMAC secret**: Using API key instead of HMAC secret
3. **Encoding issues**: HMAC computed with wrong encoding
4. **Field order mismatch**: Concatenation order doesn't match Paymob spec

### Fix

**Configure HMAC secret:**
```bash
# Get from Paymob dashboard → Integrations → HMAC Secret
PAYMOB_HMAC_SECRET=your-hmac-secret-here

# Or use Egypt Secret Key as fallback
PAYMOB_SECRET_KEY=egy_sk_test_your-secret-key
```

**Verify HMAC calculation:**
```python
# See services/payment_platform/providers/paymob_provider.py
# verify_callback_hmac() implements the correct field order

# Test HMAC locally:
import hmac
import hashlib
secret = b"YOUR_HMAC_SECRET"
concat = "amount_cents + created_at + currency + ..."  # All fields concatenated
digest = hmac.new(secret, concat.encode("utf-8"), hashlib.sha512).hexdigest()
```

### Verification
```bash
# Use the debug endpoint to test webhook processing
# Send a test webhook payload and check response
curl -X POST https://api.your-domain.com/api/payments/unified/webhooks/paymob \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "obj={...}&hmac=..."
```

---

## OAuth Token Failures

### Symptoms
- PayPal integration returns 401 "Invalid client"
- Paymob auth returns 400 "Invalid API key"
- "Authentication failed" errors

### How It Appears in Logs/Dashboard
```json
{
  "provider": "paypal",
  "step": "oauth_token",
  "status": "fail",
  "message": "HTTP 401: Invalid client credentials"
}
```

### Dashboard Indicators
- **Test Scenarios panel**: OAuth step shows "fail"
- **API Key Validation panel**: Shows "invalid" status
- **Transaction Logs**: Auth requests with 401 status

### Common Causes
1. **Expired credentials**: Client secret rotated but not updated
2. **Wrong encoding**: Basic auth header not base64 encoded
3. **Missing scopes**: Token request missing required scopes
4. **Account restrictions**: PayPal account not approved for live transactions

### Fix

**PayPal OAuth:**
```python
# Correct Basic auth encoding
import base64
credentials = f"{client_id}:{client_secret}"
encoded = base64.b64encode(credentials.encode()).decode()

headers = {
    "Authorization": f"Basic {encoded}",
    "Content-Type": "application/x-www-form-urlencoded",
}
data = {"grant_type": "client_credentials"}
```

**Paymob Auth:**
```python
# API key should be sent as-is in JSON body
payload = {"api_key": api_key}  # Not base64 encoded
```

**Verify credentials are active:**
- PayPal: Check Developer Dashboard → Apps → Your App
- Paymob: Check Dashboard → Developers → API Key

### Verification
```bash
# Run test scenarios from dashboard
# Both auth steps should pass

# Direct API test
curl -X POST https://api-m.sandbox.paypal.com/v1/oauth2/token \
  -H "Authorization: Basic $(echo -n 'CLIENT_ID:SECRET' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials"
```

---

## Quick Reference: Debug Endpoint Summary

| Endpoint | Purpose |
|----------|---------|
| `GET /debug/logs` | Recent payment API logs |
| `GET /debug/logs/{trace_id}` | Specific log detail |
| `GET /debug/client-errors` | Frontend error reports |
| `GET /debug/env-check` | Environment variable validation |
| `GET /debug/api-keys/validate` | Live API key testing |
| `GET /debug/perf-metrics` | Performance statistics |
| `GET /debug/cors-ssl-issues` | CORS/SSL problem log |
| `GET /debug/replay/candidates` | Failed requests for replay |
| `POST /debug/replay` | Replay a failed request |
| `POST /debug/test-scenarios/paymob` | Run Paymob flow test |
| `POST /debug/test-scenarios/paypal` | Run PayPal flow test |

---

## Environment Variables Checklist

### Paymob Required
- [ ] `PAYMOB_API_KEY` - JWT from dashboard
- [ ] `PAYMOB_INTEGRATION_ID` - Numeric integration ID
- [ ] `PAYMOB_IFRAME_ID` - Numeric iframe ID
- [ ] `PAYMOB_HMAC_SECRET` or `PAYMOB_SECRET_KEY` - For webhook verification

### PayPal Required
- [ ] `PAYPAL_CLIENT_ID` - From Developer Dashboard
- [ ] `PAYPAL_CLIENT_SECRET` - From Developer Dashboard
- [ ] `PAYPAL_MODE` - "sandbox" or "live"
- [ ] `PAYPAL_WEBHOOK_ID` - For webhook verification (optional)

### Frontend Required
- [ ] `VITE_API_URL` - Backend API base URL
- [ ] `VITE_PAYPAL_CLIENT_ID` - For PayPal SDK (optional, can use backend response)
- [ ] `VITE_PAYMOB_PUBLIC_KEY` - For Paymob JS (optional)

---

## Support Escalation

If issues persist after following this guide:

1. **Check provider status pages:**
   - Paymob: https://status.accept.paymob.com
   - PayPal: https://www.paypal-status.com

2. **Collect diagnostic data:**
   - Export logs from dashboard
   - Note trace IDs of failed requests
   - Screenshot error messages

3. **Contact provider support:**
   - Paymob: Support via dashboard
   - PayPal: Business Help Center

4. **Internal escalation:**
   - Create issue with trace IDs and timestamps
   - Include environment details from `/debug/env-check`
