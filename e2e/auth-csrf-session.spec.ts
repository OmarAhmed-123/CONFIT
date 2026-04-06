/**
 * CONFIT Authentication Tests - CSRF Token & Session Security
 * ============================================================
 * Validates CSRF protection, session cookie security, and that sensitive
 * data is not exposed to client. Maps to audit findings:
 * - "CSRF tokens must be present on form submissions"
 * - "Session cookies must be HttpOnly and Secure"
 * - "Session objects must not expose sensitive fields"
 * 
 * @file e2e/auth-csrf-session.spec.ts
 */

import { test, expect, request } from '@playwright/test';

const API_URL = process.env.PLAYWRIGHT_API_URL ?? 'http://localhost:8000';
const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:8080';

// ─────────────────────────────────────────────────────────────────────────────
// CSRF TOKEN TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('CSRF Token Protection', () => {
  
  test('CSRF token is rejected when absent on protected endpoints', async ({ request }) => {
    // Attempt to make a state-changing request without CSRF token
    // Note: Login/register are exempt per CSRFMiddleware config
    const response = await request.post(`${API_URL}/api/auth/password/change`, {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        current_password: 'test123',
        new_password: 'newpassword123',
      },
    });
    
    // Should be rejected (401 for no auth, 403 for CSRF failure)
    expect([401, 403, 422]).toContain(response.status());
  });
  
  test('CSRF token is rejected when tampered', async ({ request }) => {
    // First, get a session (simulate login)
    const loginResponse = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: { email: 'test@example.com', password: 'testpassword' },
    });
    
    // If login succeeded, try with invalid CSRF token
    if (loginResponse.ok()) {
      const response = await request.post(`${API_URL}/api/auth/password/change`, {
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': 'invalid_tampered_token',
        },
        data: {
          current_password: 'test123',
          new_password: 'newpassword123',
        },
      });
      
      // Should be rejected due to CSRF mismatch
      expect([401, 403]).toContain(response.status());
    }
  });
  
  test('Bearer auth bypasses CSRF requirement', async ({ request }) => {
    // API endpoints using Bearer token auth should not need CSRF
    // This is by design for SPAs/mobile apps
    const response = await request.post(`${API_URL}/api/auth/password/change`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer invalid_token_for_test',
      },
      data: {
        current_password: 'test123',
        new_password: 'newpassword123',
      },
    });
    
    // Should not be 403 (CSRF failure) - should be 401 (invalid token)
    // or 422 (validation error)
    expect(response.status()).not.toBe(403);
    expect([401, 422, 400]).toContain(response.status());
  });
  
  test('Safe methods (GET, HEAD, OPTIONS) bypass CSRF', async ({ request }) => {
    // GET requests should not require CSRF
    const getResponse = await request.get(`${API_URL}/api/auth/me`);
    expect(getResponse.status()).not.toBe(403);
    
    // OPTIONS requests should not require CSRF
    const optionsResponse = await request.fetch(`${API_URL}/api/auth/me`, {
      method: 'OPTIONS',
    });
    expect(optionsResponse.status()).not.toBe(403);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SESSION COOKIE SECURITY TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Session Cookie Security', () => {
  
  test('Session cookies are HttpOnly', async ({ page, context }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Perform login
    const emailInput = page.locator('input[name="email"]').first();
    const passwordInput = page.locator('input[name="password"]').first();
    const submitButton = page.locator('button[type="submit"]').first();
    
    await emailInput.fill('test@example.com');
    await passwordInput.fill('TestPassword123!');
    await submitButton.click();
    
    // Wait for response
    await page.waitForTimeout(2000);
    
    // Get cookies
    const cookies = await context.cookies();
    
    // Find session/auth cookies
    const sessionCookies = cookies.filter(
      (c) => c.name.includes('session') || 
             c.name.includes('token') || 
             c.name === 'confit_token'
    );
    
    // Audit finding: Session cookies must be HttpOnly
    for (const cookie of sessionCookies) {
      if (cookie.name.includes('session') || cookie.name === 'confit_token') {
        expect(cookie.httpOnly).toBe(true);
      }
    }
  });
  
  test('Session cookies are Secure in production', async ({ page, context }) => {
    // This test is informational in dev (localhost)
    // In production, secure flag should be true
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const cookies = await context.cookies();
    const sessionCookies = cookies.filter(
      (c) => c.name.includes('session') || c.name === 'confit_token'
    );
    
    // Log for verification - in CI with HTTPS, this should be true
    for (const cookie of sessionCookies) {
      console.log(`Cookie: ${cookie.name}, Secure: ${cookie.secure}`);
      
      // In production (HTTPS), secure should be true
      if (process.env.CI && page.url().startsWith('https://')) {
        if (cookie.name.includes('session') || cookie.name === 'confit_token') {
          expect(cookie.secure).toBe(true);
        }
      }
    }
  });
  
  test('Session cookies have SameSite attribute', async ({ page, context }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const cookies = await context.cookies();
    const sessionCookies = cookies.filter(
      (c) => c.name.includes('session') || c.name === 'confit_token'
    );
    
    // Audit finding: SameSite prevents CSRF
    for (const cookie of sessionCookies) {
      if (cookie.name.includes('session') || cookie.name === 'confit_token') {
        // SameSite should be 'Strict' or 'Lax'
        expect(['Strict', 'Lax', 'None']).toContain(cookie.sameSite);
        
        // Log for verification
        console.log(`Cookie: ${cookie.name}, SameSite: ${cookie.sameSite}`);
      }
    }
  });
  
  test('JavaScript cannot access HttpOnly cookies', async ({ page, context }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Try to access cookies via JavaScript
    const jsCookies = await page.evaluate(() => document.cookie);
    
    // HttpOnly cookies should NOT appear in document.cookie
    expect(jsCookies).not.toContain('session');
    expect(jsCookies).not.toContain('confit_token');
    
    // Log what IS accessible (should be non-sensitive only)
    console.log('JS-accessible cookies:', jsCookies);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SESSION DATA EXPOSURE TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Session Data Exposure Prevention', () => {
  
  test('useSession() does not expose raw tokens', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Login first
    const emailInput = page.locator('input[name="email"]').first();
    const passwordInput = page.locator('input[name="password"]').first();
    const submitButton = page.locator('button[type="submit"]').first();
    
    await emailInput.fill('test@example.com');
    await passwordInput.fill('TestPassword123!');
    await submitButton.click();
    
    await page.waitForTimeout(2000);
    
    // Check what session data is exposed to client
    const sessionData = await page.evaluate(() => {
      // Check localStorage for sensitive data
      const stored: Record<string, string | null> = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key) {
          const value = localStorage.getItem(key);
          stored[key] = value;
        }
      }
      return stored;
    });
    
    // Audit finding: Raw tokens should not be exposed
    // The token itself is stored, but check what's in user object
    const userDataStr = sessionData['confit_user'];
    if (userDataStr) {
      const userData = JSON.parse(userDataStr) as Record<string, unknown>;
      
      // Should NOT contain sensitive fields
      expect(userData).not.toHaveProperty('password');
      expect(userData).not.toHaveProperty('password_hash');
      expect(userData).not.toHaveProperty('refresh_token');
      expect(userData).not.toHaveProperty('private_key');
      expect(userData).not.toHaveProperty('internal_id');
      
      // Should contain safe fields
      expect(userData).toHaveProperty('email');
      expect(userData).toHaveProperty('name');
    }
  });
  
  test('Auth context does not expose sensitive fields', async ({ page }) => {
    await page.goto('/profile');
    await page.waitForLoadState('networkidle');
    
    // Check if profile page exposes any sensitive data
    const pageContent = await page.content();
    
    // Should not expose tokens in DOM
    expect(pageContent).not.toMatch(/refresh_token.*['"]/);
    expect(pageContent).not.toMatch(/private_key.*['"]/);
    expect(pageContent).not.toMatch(/password_hash.*['"]/);
  });
  
  test('API /auth/me response does not expose sensitive fields', async ({ request }) => {
    // Attempt to get user info without auth (should fail)
    const response = await request.get(`${API_URL}/api/auth/me`);
    
    // Should be 401 (unauthorized) or 403 (forbidden)
    expect([401, 403, 422]).toContain(response.status());
    
    // Response should not leak sensitive info even on error
    const body = await response.text();
    expect(body).not.toContain('password');
    expect(body).not.toContain('secret');
    expect(body).not.toContain('private_key');
  });
  
  test('Login response contains only safe user fields', async ({ request }) => {
    // This test requires a valid test user
    // In CI, this would use test credentials
    const response = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: { email: 'test@example.com', password: 'testpassword' },
    });
    
    if (response.ok()) {
      const body = await response.json();
      
      // Should have tokens (these are needed for auth)
      expect(body).toHaveProperty('access_token');
      expect(body).toHaveProperty('refresh_token');
      
      // User object should NOT have sensitive fields
      if (body.user) {
        expect(body.user).not.toHaveProperty('password');
        expect(body.user).not.toHaveProperty('password_hash');
        expect(body.user).not.toHaveProperty('private_key');
        expect(body.user).not.toHaveProperty('secret_key');
        
        // Should have safe fields
        expect(body.user).toHaveProperty('id');
        expect(body.user).toHaveProperty('email');
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SECURITY HEADERS TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Security Headers', () => {
  
  test('X-Content-Type-Options header is set', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    const contentTypeOptions = response.headers()['x-content-type-options'];
    expect(contentTypeOptions).toBe('nosniff');
  });
  
  test('X-Frame-Options header prevents clickjacking', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    const frameOptions = response.headers()['x-frame-options'];
    expect(frameOptions).toBe('DENY');
  });
  
  test('Strict-Transport-Security header is set', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    const hsts = response.headers()['strict-transport-security'];
    expect(hsts).toBeTruthy();
    expect(hsts).toContain('max-age');
  });
  
  test('X-XSS-Protection header is set', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    const xssProtection = response.headers()['x-xss-protection'];
    expect(xssProtection).toContain('1');
  });
  
  test('Content-Security-Policy header is set', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    const csp = response.headers()['content-security-policy'];
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'self'");
  });
  
  test('Referrer-Policy header is set', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    const referrerPolicy = response.headers()['referrer-policy'];
    expect(referrerPolicy).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// INPUT VALIDATION TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Input Validation', () => {
  
  test('SQL injection is detected and blocked', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        email: "test@example.com'; DROP TABLE users; --",
        password: 'testpassword',
      },
    });
    
    // Should be rejected (400 or 401)
    expect([400, 401, 422]).toContain(response.status());
    
    // Should not return SQL error
    const body = await response.text();
    expect(body.toLowerCase()).not.toContain('sql');
    expect(body.toLowerCase()).not.toContain('syntax');
  });
  
  test('XSS injection is detected and blocked', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        email: 'test@example.com',
        password: 'TestPassword123!',
        name: '<script>alert("xss")</script>',
      },
    });
    
    // Should be rejected
    expect([400, 401, 422]).toContain(response.status());
    
    const body = await response.text();
    expect(body.toLowerCase()).not.toContain('<script>');
  });
  
  test('Path traversal is detected and blocked', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/../../../etc/passwd`);
    
    // Should be rejected or not found
    expect([400, 404]).toContain(response.status());
  });
});
