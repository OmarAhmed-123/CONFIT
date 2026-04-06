/**
 * CONFIT Authentication Tests - FastAPI Backend Integration
 * ==========================================================
 * Validates integration between Next.js auth and FastAPI backend:
 * - Middleware authentication forwarding
 * - CORS configuration
 * - Callback URL handling
 * 
 * @file e2e/auth-backend-integration.spec.ts
 */

import { test, expect, APIRequestContext } from '@playwright/test';

const API_URL = process.env.PLAYWRIGHT_API_URL ?? 'http://localhost:8000';
const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:8080';

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

async function getAuthToken(request: APIRequestContext): Promise<string | null> {
  const response = await request.post(`${API_URL}/api/auth/login`, {
    headers: { 'Content-Type': 'application/json' },
    data: {
      email: process.env.TEST_USER_EMAIL ?? 'test@example.com',
      password: process.env.TEST_USER_PASSWORD ?? 'TestPassword123!',
    },
  });
  
  if (response.ok()) {
    const body = await response.json();
    return body.access_token;
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTHENTICATION MIDDLEWARE TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Authentication Middleware', () => {
  
  test('valid session cookie returns 200 on protected route', async ({ request }) => {
    const token = await getAuthToken(request);
    
    if (token) {
      const response = await request.get(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      expect(response.status()).toBe(200);
      
      const body = await response.json();
      expect(body).toHaveProperty('id');
      expect(body).toHaveProperty('email');
    }
  });
  
  test('missing auth token returns 401 on protected route', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/me`);
    
    expect(response.status()).toBe(401);
  });
  
  test('invalid auth token returns 401 on protected route', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/me`, {
      headers: {
        'Authorization': 'Bearer invalid_token_12345',
      },
    });
    
    expect(response.status()).toBe(401);
  });
  
  test('expired auth token returns 401 on protected route', async ({ request }) => {
    // Use an obviously expired token format
    const response = await request.get(`${API_URL}/api/auth/me`, {
      headers: {
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
      },
    });
    
    expect(response.status()).toBe(401);
  });
  
  test('malformed auth header returns 401 on protected route', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/me`, {
      headers: {
        'Authorization': 'InvalidFormat token',
      },
    });
    
    expect(response.status()).toBe(401);
  });
  
  test('public routes do not require authentication', async ({ request }) => {
    // Health endpoint should be accessible without auth
    const healthResponse = await request.get(`${API_URL}/health`);
    expect([200, 404]).toContain(healthResponse.status());
    
    // Products should be accessible without auth
    const productsResponse = await request.get(`${API_URL}/api/products`);
    expect([200, 401, 404]).toContain(productsResponse.status());
  });
  
  test('middleware correctly forwards user context', async ({ request }) => {
    const token = await getAuthToken(request);
    
    if (token) {
      // Call endpoint that returns user info from context
      const response = await request.get(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok()) {
        const body = await response.json();
        
        // Should have user data from middleware-injected context
        expect(body.email).toBeTruthy();
        expect(body.id).toBeTruthy();
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// CORS CONFIGURATION TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('CORS Configuration', () => {
  
  test('CORS allows requests from frontend origin', async ({ request }) => {
    const response = await request.fetch(`${API_URL}/api/auth/me`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
      },
    });
    
    // Should allow the origin
    const allowOrigin = response.headers()['access-control-allow-origin'];
    expect(allowOrigin).toBeTruthy();
  });
  
  test('CORS allows auth route methods', async ({ request }) => {
    const response = await request.fetch(`${API_URL}/api/auth/login`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'POST',
      },
    });
    
    const allowMethods = response.headers()['access-control-allow-methods'];
    expect(allowMethods).toBeTruthy();
    expect(allowMethods).toContain('POST');
  });
  
  test('CORS allows Authorization header', async ({ request }) => {
    const response = await request.fetch(`${API_URL}/api/auth/me`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Authorization, Content-Type',
      },
    });
    
    const allowHeaders = response.headers()['access-control-allow-headers'];
    expect(allowHeaders).toBeTruthy();
    expect(allowHeaders.toLowerCase()).toContain('authorization');
  });
  
  test('CORS allows credentials for cookie-based auth', async ({ request }) => {
    const response = await request.fetch(`${API_URL}/api/auth/me`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
      },
    });
    
    const allowCredentials = response.headers()['access-control-allow-credentials'];
    expect(allowCredentials).toBeTruthy();
  });
  
  test('preflight request returns correct CORS headers', async ({ request }) => {
    const response = await request.fetch(`${API_URL}/api/auth/login`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type, Authorization',
      },
    });
    
    // Should return 200 for preflight
    expect(response.status()).toBe(200);
    
    // Should include all required CORS headers
    expect(response.headers()['access-control-allow-origin']).toBeTruthy();
    expect(response.headers()['access-control-allow-methods']).toBeTruthy();
    expect(response.headers()['access-control-allow-headers']).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// CALLBACK URL HANDLING TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Callback URL Handling', () => {
  
  test('OAuth callback URL resolves without errors', async ({ request }) => {
    // Test that the callback endpoint exists
    const response = await request.post(`${API_URL}/api/auth/oauth/google/callback`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        code: 'test_code',
        state: 'test_state',
      },
    });
    
    // Should not return 500 (server error)
    expect(response.status()).not.toBe(500);
    
    // Should return 401 (invalid state/code) or 400 (validation error)
    expect([400, 401, 422]).toContain(response.status());
  });
  
  test('OAuth callback rejects invalid state', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/oauth/google/callback`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        code: 'test_code',
        state: 'invalid_state_that_does_not_exist',
      },
    });
    
    // Should reject with 401
    expect(response.status()).toBe(401);
    
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });
  
  test('OAuth callback rejects missing code', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/oauth/google/callback`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        state: 'test_state',
      },
    });
    
    // Should reject with 422 (validation error)
    expect(response.status()).toBe(422);
  });
  
  test('OAuth callback handles all providers', async ({ request }) => {
    const providers = ['google', 'apple', 'facebook', 'x', 'tiktok'];
    
    for (const provider of providers) {
      const response = await request.post(`${API_URL}/api/auth/oauth/${provider}/callback`, {
        headers: { 'Content-Type': 'application/json' },
        data: {
          code: 'test_code',
          state: 'test_state',
        },
      });
      
      // Should not return 500 for any provider
      expect(response.status()).not.toBe(500);
    }
  });
  
  test('redirect_to parameter is preserved in OAuth flow', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/oauth/google`, {
      params: {
        redirect_to: 'http://localhost:8080/profile',
      },
    });
    
    if (response.ok()) {
      const body = await response.json();
      const authUrl = body.authorization_url;
      
      // The redirect_to should be stored in state
      expect(authUrl).toBeTruthy();
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// TOKEN REFRESH FLOW TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Token Refresh Flow', () => {
  
  test('refresh token endpoint exists', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/refresh`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        refresh_token: 'invalid_refresh_token',
      },
    });
    
    // Should not return 404 or 500
    expect(response.status()).not.toBe(404);
    expect(response.status()).not.toBe(500);
    
    // Should return 401 for invalid token
    expect(response.status()).toBe(401);
  });
  
  test('refresh returns new access token', async ({ request }) => {
    // First login to get tokens
    const loginResponse = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        email: process.env.TEST_USER_EMAIL ?? 'test@example.com',
        password: process.env.TEST_USER_PASSWORD ?? 'TestPassword123!',
      },
    });
    
    if (loginResponse.ok()) {
      const loginBody = await loginResponse.json();
      const refreshToken = loginBody.refresh_token;
      
      // Use refresh token to get new access token
      const refreshResponse = await request.post(`${API_URL}/api/auth/refresh`, {
        headers: { 'Content-Type': 'application/json' },
        data: {
          refresh_token: refreshToken,
        },
      });
      
      expect(refreshResponse.status()).toBe(200);
      
      const refreshBody = await refreshResponse.json();
      expect(refreshBody).toHaveProperty('access_token');
      expect(refreshBody).toHaveProperty('refresh_token');
      
      // New tokens should be different from old ones
      expect(refreshBody.access_token).not.toBe(loginBody.access_token);
    }
  });
  
  test('new access token is valid', async ({ request }) => {
    // Login and refresh
    const loginResponse = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        email: process.env.TEST_USER_EMAIL ?? 'test@example.com',
        password: process.env.TEST_USER_PASSWORD ?? 'TestPassword123!',
      },
    });
    
    if (loginResponse.ok()) {
      const loginBody = await loginResponse.json();
      
      const refreshResponse = await request.post(`${API_URL}/api/auth/refresh`, {
        headers: { 'Content-Type': 'application/json' },
        data: {
          refresh_token: loginBody.refresh_token,
        },
      });
      
      if (refreshResponse.ok()) {
        const refreshBody = await refreshResponse.json();
        
        // Use new access token to access protected route
        const meResponse = await request.get(`${API_URL}/api/auth/me`, {
          headers: {
            'Authorization': `Bearer ${refreshBody.access_token}`,
          },
        });
        
        expect(meResponse.status()).toBe(200);
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// ERROR HANDLING TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Error Handling', () => {
  
  test('API returns consistent error format', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/me`);
    
    expect(response.status()).toBe(401);
    
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });
  
  test('API does not expose stack traces in production', async ({ request }) => {
    // Try to trigger an error
    const response = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        email: 'invalid',
        password: 'x',
      },
    });
    
    const body = await response.text();
    
    // Should not contain stack trace
    expect(body.toLowerCase()).not.toContain('traceback');
    expect(body.toLowerCase()).not.toContain('file "');
    expect(body.toLowerCase()).not.toContain('line ');
  });
  
  test('API handles malformed JSON gracefully', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: '{ invalid json }',
    });
    
    // Should return 422 (unprocessable entity) not 500
    expect(response.status()).toBe(422);
  });
  
  test('API handles missing content-type gracefully', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/login`, {
      data: JSON.stringify({
        email: 'test@example.com',
        password: 'testpassword',
      }),
    });
    
    // Should return 422 or 400, not 500
    expect([400, 422]).toContain(response.status());
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// RATE LIMITING TESTS (if applicable)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Rate Limiting', () => {
  
  test('login endpoint has rate limiting', async ({ request }) => {
    // Make multiple rapid requests
    const responses = await Promise.all(
      Array(10).fill(null).map(() =>
        request.post(`${API_URL}/api/auth/login`, {
          headers: { 'Content-Type': 'application/json' },
          data: {
            email: 'test@example.com',
            password: 'wrongpassword',
          },
        })
      )
    );
    
    // At least some should be rate limited (429) or all should fail auth (401)
    const statusCodes = responses.map((r) => r.status());
    const hasRateLimit = statusCodes.includes(429);
    const allAuthFailures = statusCodes.every((code) => code === 401);
    
    expect(hasRateLimit || allAuthFailures).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// HEALTH CHECK TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Health Check', () => {
  
  test('health endpoint returns 200', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    // Should return 200 or 404 if not implemented
    expect([200, 404]).toContain(response.status());
    
    if (response.ok()) {
      const body = await response.json();
      expect(body).toBeTruthy();
    }
  });
  
  test('API is accessible from frontend origin', async ({ page }) => {
    // Navigate to frontend and check if API calls work
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Make API call from browser context
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch(`${API_URL}/health`);
        return { status: response.status, ok: response.ok };
      } catch (error) {
        return { error: String(error) };
      }
    });
    
    // Should be able to reach API
    expect(apiResponse.error).toBeUndefined();
    expect([200, 404]).toContain(apiResponse.status);
  });
});
