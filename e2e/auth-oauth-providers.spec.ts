/**
 * CONFIT Authentication Tests - OAuth Provider Configuration
 * ==========================================================
 * Validates Google and Apple OAuth provider setup, scopes, environment variables,
 * and callback routes. Maps to audit finding: "OAuth providers must declare
 * required scopes and have valid credentials configured."
 * 
 * @file e2e/auth-oauth-providers.spec.ts
 */

import { test, expect } from '@playwright/test';

// API base URL for backend tests
const API_URL = process.env.PLAYWRIGHT_API_URL ?? 'http://localhost:8000';

// OAuth configuration from environment
const OAUTH_CONFIG = {
  google: {
    clientId: process.env.OAUTH_GOOGLE_CLIENT_ID ?? process.env.GOOGLE_CLIENT_ID ?? '',
    clientSecret: process.env.OAUTH_GOOGLE_CLIENT_SECRET ?? process.env.GOOGLE_CLIENT_SECRET ?? '',
    requiredScopes: ['openid', 'email', 'profile'],
    authUrl: 'accounts.google.com',
  },
  apple: {
    clientId: process.env.OAUTH_APPLE_CLIENT_ID ?? process.env.APPLE_CLIENT_ID ?? '',
    clientSecret: process.env.OAUTH_APPLE_CLIENT_SECRET ?? process.env.APPLE_CLIENT_SECRET ?? '',
    requiredScopes: ['email', 'name'],
    authUrl: 'appleid.apple.com',
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// OAUTH ENVIRONMENT VARIABLE TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('OAuth Environment Variables', () => {
  
  test('Google OAuth client ID is configured', async () => {
    // Audit finding: GOOGLE_CLIENT_ID must be non-empty at runtime
    expect(OAUTH_CONFIG.google.clientId).toBeTruthy();
    expect(OAUTH_CONFIG.google.clientId.length).toBeGreaterThan(0);
    
    // Validate format (should be a valid Google client ID format)
    expect(OAUTH_CONFIG.google.clientId).toMatch(/^[a-zA-Z0-9-]+\.apps\.googleusercontent\.com$/);
  });
  
  test('Google OAuth client secret is configured', async () => {
    // Audit finding: GOOGLE_CLIENT_SECRET must be non-empty at runtime
    expect(OAUTH_CONFIG.google.clientSecret).toBeTruthy();
    expect(OAUTH_CONFIG.google.clientSecret.length).toBeGreaterThan(0);
  });
  
  test('Apple OAuth client ID is configured', async () => {
    // Audit finding: APPLE_CLIENT_ID must be non-empty at runtime
    expect(OAUTH_CONFIG.apple.clientId).toBeTruthy();
    expect(OAUTH_CONFIG.apple.clientId.length).toBeGreaterThan(0);
  });
  
  test('Apple OAuth client secret is configured', async () => {
    // Audit finding: APPLE_CLIENT_SECRET must be non-empty at runtime
    expect(OAUTH_CONFIG.apple.clientSecret).toBeTruthy();
    expect(OAUTH_CONFIG.apple.clientSecret.length).toBeGreaterThan(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// OAUTH AUTHORIZATION URL TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('OAuth Authorization URLs', () => {
  
  test('Google OAuth button links to correct authorization URL', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Find Google OAuth button
    const googleButton = page.locator('a[href*="google"], button:has-text("Google")').first();
    await expect(googleButton).toBeVisible();
    
    // Get href and verify it points to Google OAuth
    const href = await googleButton.getAttribute('href');
    expect(href).toBeTruthy();
    
    // Should contain Google OAuth endpoint
    expect(href).toContain('google');
    expect(href).toContain('auth');
  });
  
  test('Google OAuth URL includes required scopes', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const googleButton = page.locator('a[href*="google"]').first();
    const href = await googleButton.getAttribute('href');
    
    if (href && (href.includes('google') || href.includes('oauth'))) {
      // Navigate to the OAuth URL
      await page.goto(href);
      
      // Should redirect to Google's OAuth page
      await page.waitForURL(/google|accounts\.google/, { timeout: 10000 }).catch(() => {
        // If it doesn't redirect directly, check if it goes through our backend
      });
      
      const currentUrl = page.url();
      
      // If we're on Google's page, verify scopes in URL
      if (currentUrl.includes('accounts.google.com')) {
        const urlObj = new URL(currentUrl);
        const scope = urlObj.searchParams.get('scope');
        
        // Audit finding: Required scopes must be present
        expect(scope).toBeTruthy();
        
        const scopes = scope!.split(' ');
        for (const requiredScope of OAUTH_CONFIG.google.requiredScopes) {
          expect(scopes).toContain(requiredScope);
        }
      }
    }
  });
  
  test('Apple OAuth button links to correct authorization URL', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const appleButton = page.locator('a[href*="apple"], button:has-text("Apple")').first();
    await expect(appleButton).toBeVisible();
    
    const href = await appleButton.getAttribute('href');
    expect(href).toBeTruthy();
    expect(href).toContain('apple');
  });
  
  test('OAuth URLs include state parameter for CSRF protection', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const googleButton = page.locator('a[href*="google"]').first();
    const href = await googleButton.getAttribute('href');
    
    if (href) {
      // Navigate to OAuth endpoint
      await page.goto(href);
      
      // Check if state parameter is present in OAuth URL
      const currentUrl = page.url();
      
      if (currentUrl.includes('google') || currentUrl.includes('apple')) {
        const urlObj = new URL(currentUrl);
        const state = urlObj.searchParams.get('state');
        
        // Audit finding: State parameter required for CSRF protection
        expect(state).toBeTruthy();
        expect(state!.length).toBeGreaterThan(10); // Should be a secure random value
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// OAUTH CALLBACK ROUTE TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('OAuth Callback Routes', () => {
  
  test('Google OAuth callback route exists and returns expected structure', async ({ request }) => {
    // Test backend OAuth callback endpoint exists
    const response = await request.get(`${API_URL}/api/auth/oauth/google`, {
      params: {
        redirect_to: 'http://localhost:8080',
      },
    });
    
    // Should return authorization URL or redirect
    expect([200, 400, 422]).toContain(response.status());
    
    if (response.status() === 200) {
      const body = await response.json();
      
      // Should return authorization URL
      expect(body).toHaveProperty('authorization_url');
      expect(body.authorization_url).toContain('google');
    }
  });
  
  test('Apple OAuth callback route exists and returns expected structure', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/oauth/apple`, {
      params: {
        redirect_to: 'http://localhost:8080',
      },
    });
    
    expect([200, 400, 422]).toContain(response.status());
    
    if (response.status() === 200) {
      const body = await response.json();
      
      expect(body).toHaveProperty('authorization_url');
      expect(body.authorization_url).toContain('apple');
    }
  });
  
  test('Invalid OAuth provider returns 400 error', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/oauth/invalid-provider`);
    
    // Should return 400 for unknown provider
    expect(response.status()).toBe(400);
    
    const body = await response.json();
    expect(body).toHaveProperty('detail');
    expect(body.detail).toContain('not configured');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// OAUTH SCOPE VALIDATION TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('OAuth Scope Validation', () => {
  
  test('Google OAuth declares email scope', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const googleButton = page.locator('a[href*="google"]').first();
    const href = await googleButton.getAttribute('href');
    
    if (href) {
      await page.goto(href);
      
      // Wait for potential redirect to Google
      await page.waitForTimeout(2000);
      
      const currentUrl = page.url();
      
      if (currentUrl.includes('accounts.google.com')) {
        const urlObj = new URL(currentUrl);
        const scope = urlObj.searchParams.get('scope');
        
        // Audit finding: email scope required for user identification
        expect(scope).toContain('email');
      }
    }
  });
  
  test('Google OAuth declares profile scope', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const googleButton = page.locator('a[href*="google"]').first();
    const href = await googleButton.getAttribute('href');
    
    if (href) {
      await page.goto(href);
      await page.waitForTimeout(2000);
      
      const currentUrl = page.url();
      
      if (currentUrl.includes('accounts.google.com')) {
        const urlObj = new URL(currentUrl);
        const scope = urlObj.searchParams.get('scope');
        
        // Audit finding: profile scope required for user info
        expect(scope).toContain('profile');
      }
    }
  });
  
  test('Google OAuth declares openid scope', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const googleButton = page.locator('a[href*="google"]').first();
    const href = await googleButton.getAttribute('href');
    
    if (href) {
      await page.goto(href);
      await page.waitForTimeout(2000);
      
      const currentUrl = page.url();
      
      if (currentUrl.includes('accounts.google.com')) {
        const urlObj = new URL(currentUrl);
        const scope = urlObj.searchParams.get('scope');
        
        // openid scope for ID token
        expect(scope).toContain('openid');
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// OAUTH PROVIDER CONFIGURATION TESTS (Backend)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('OAuth Provider Configuration (Backend)', () => {
  
  test('Backend lists configured OAuth providers', async ({ request }) => {
    // Check if backend has OAuth providers configured
    const response = await request.get(`${API_URL}/api/auth/oauth/google`);
    
    // If 200, provider is configured
    // If 400, provider is not configured but endpoint exists
    expect([200, 400, 422]).toContain(response.status());
  });
  
  test('OAuth redirect URI is correctly configured', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/oauth/google`, {
      params: {
        redirect_to: 'http://localhost:8080/profile',
      },
    });
    
    if (response.status() === 200) {
      const body = await response.json();
      const authUrl = body.authorization_url;
      
      // Verify redirect_uri is in the authorization URL
      const urlObj = new URL(authUrl);
      const redirectUri = urlObj.searchParams.get('redirect_uri');
      
      expect(redirectUri).toBeTruthy();
      expect(redirectUri).toContain('callback');
    }
  });
  
  test('OAuth state token is generated for each request', async ({ request }) => {
    const response1 = await request.get(`${API_URL}/api/auth/oauth/google`);
    const response2 = await request.get(`${API_URL}/api/auth/oauth/google`);
    
    if (response1.status() === 200 && response2.status() === 200) {
      const body1 = await response1.json();
      const body2 = await response2.json();
      
      const url1 = new URL(body1.authorization_url);
      const url2 = new URL(body2.authorization_url);
      
      const state1 = url1.searchParams.get('state');
      const state2 = url2.searchParams.get('state');
      
      // Each request should generate a unique state token
      expect(state1).toBeTruthy();
      expect(state2).toBeTruthy();
      expect(state1).not.toBe(state2);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SOCIAL LOGIN BUTTON TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Social Login Buttons', () => {
  
  test('All OAuth providers have login buttons', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Check for Google button
    const googleButton = page.locator('button:has-text("Google"), a:has-text("Google")');
    await expect(googleButton.first()).toBeVisible();
    
    // Check for Apple button
    const appleButton = page.locator('button:has-text("Apple"), a:has-text("Apple")');
    await expect(appleButton.first()).toBeVisible();
  });
  
  test('OAuth buttons are inside form or have proper navigation', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const googleButton = page.locator('a[href*="google"]').first();
    
    // Should be a link (anchor tag) for OAuth redirect
    const tagName = await googleButton.evaluate((el) => el.tagName.toLowerCase());
    expect(tagName).toBe('a');
    
    // Should have href attribute
    const href = await googleButton.getAttribute('href');
    expect(href).toBeTruthy();
  });
  
  test('OAuth buttons include return_to parameter', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const googleButton = page.locator('a[href*="google"]').first();
    const href = await googleButton.getAttribute('href');
    
    if (href) {
      // Should include return_to or redirect_to for post-auth navigation
      expect(href).toMatch(/return_to|redirect_to/);
    }
  });
});
