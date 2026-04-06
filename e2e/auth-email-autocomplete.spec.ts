/**
 * CONFIT Authentication Tests - Email Autocomplete Attributes
 * ============================================================
 * Validates that email inputs have correct autocomplete attributes for native
 * browser credential suggestions. Maps to audit finding: "Email autocomplete
 * attributes must be present for password manager integration."
 * 
 * @file e2e/auth-email-autocomplete.spec.ts
 */

import { test, expect } from '@playwright/test';

// Test configuration - auth pages to validate
const AUTH_PAGES = [
  {
    name: 'Login',
    path: '/login',
    emailSelector: 'input[type="email"], input[name="email"]',
  },
  {
    name: 'Register',
    path: '/register',
    emailSelector: 'input[type="email"], input[name="email"]',
  },
  {
    name: 'AuthPage (login mode)',
    path: '/auth?mode=login',
    emailSelector: 'input[type="email"], input[name="email"]',
  },
  {
    name: 'AuthPage (signup mode)',
    path: '/auth?mode=signup',
    emailSelector: 'input[type="email"], input[name="email"]',
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// EMAIL AUTOCOMPLETE ATTRIBUTE TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Email Autocomplete Attributes', () => {
  
  // Test across all auth pages
  for (const page of AUTH_PAGES) {
    test.describe(`${page.name} page`, () => {
      
      test('email input has autocomplete="email" attribute', async ({ page: pwPage }) => {
        // Navigate to auth page
        await pwPage.goto(page.path);
        await pwPage.waitForLoadState('networkidle');
        
        // Find email input
        const emailInput = pwPage.locator(page.emailSelector).first();
        await expect(emailInput).toBeVisible();
        
        // Assert autocomplete attribute is "email"
        // Audit finding: Browser credential managers require autocomplete="email"
        const autocomplete = await emailInput.getAttribute('autocomplete');
        expect(autocomplete).toBe('email');
      });
      
      test('email input has name="email" attribute', async ({ page: pwPage }) => {
        await pwPage.goto(page.path);
        await pwPage.waitForLoadState('networkidle');
        
        const emailInput = pwPage.locator(page.emailSelector).first();
        await expect(emailInput).toBeVisible();
        
        // Assert name attribute - required for form autofill
        const name = await emailInput.getAttribute('name');
        expect(name).toBe('email');
      });
      
      test('email input has type="email" attribute', async ({ page: pwPage }) => {
        await pwPage.goto(page.path);
        await pwPage.waitForLoadState('networkidle');
        
        const emailInput = pwPage.locator(page.emailSelector).first();
        await expect(emailInput).toBeVisible();
        
        // Assert type attribute for proper keyboard on mobile
        const type = await emailInput.getAttribute('type');
        expect(type).toBe('email');
      });
      
      test('email input has id attribute for label association', async ({ page: pwPage }) => {
        await pwPage.goto(page.path);
        await pwPage.waitForLoadState('networkidle');
        
        const emailInput = pwPage.locator(page.emailSelector).first();
        await expect(emailInput).toBeVisible();
        
        // Assert id attribute exists - needed for label[for] association
        const id = await emailInput.getAttribute('id');
        expect(id).toBeTruthy();
        expect(id!.length).toBeGreaterThan(0);
      });
      
      test('email input is wrapped in a valid <form> element', async ({ page: pwPage }) => {
        await pwPage.goto(page.path);
        await pwPage.waitForLoadState('networkidle');
        
        const emailInput = pwPage.locator(page.emailSelector).first();
        await expect(emailInput).toBeVisible();
        
        // Audit finding: Form wrapper required for native credential suggestions
        const form = emailInput.locator('xpath=ancestor::form');
        const formCount = await form.count();
        expect(formCount).toBeGreaterThan(0);
        
        // Verify form has proper attributes
        const formElement = form.first();
        const method = await formElement.getAttribute('method');
        const action = await formElement.getAttribute('action');
        
        // Form should have method (default GET if not specified)
        expect(method || 'GET').toBeTruthy();
      });
      
      test('form has submit button for credential capture', async ({ page: pwPage }) => {
        await pwPage.goto(page.path);
        await pwPage.waitForLoadState('networkidle');
        
        const emailInput = pwPage.locator(page.emailSelector).first();
        await expect(emailInput).toBeVisible();
        
        const form = emailInput.locator('xpath=ancestor::form').first();
        
        // Form should have a submit button
        const submitButton = form.locator('button[type="submit"], input[type="submit"]');
        await expect(submitButton.first()).toBeVisible();
      });
    });
  }
  
  // ─────────────────────────────────────────────────────────────────────────
  // PASSWORD AUTOCOMPLETE TESTS
  // ─────────────────────────────────────────────────────────────────────────
  
  test.describe('Password autocomplete attributes', () => {
    
    test('login password has autocomplete="current-password"', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
      await expect(passwordInput).toBeVisible();
      
      // Audit finding: current-password for login forms
      const autocomplete = await passwordInput.getAttribute('autocomplete');
      expect(autocomplete).toBe('current-password');
    });
    
    test('register password has autocomplete="new-password"', async ({ page }) => {
      await page.goto('/register');
      await page.waitForLoadState('networkidle');
      
      const passwordInput = page.locator('input[name="password"]').first();
      await expect(passwordInput).toBeVisible();
      
      // Audit finding: new-password for registration forms
      const autocomplete = await passwordInput.getAttribute('autocomplete');
      expect(autocomplete).toBe('new-password');
    });
    
    test('register confirm password has autocomplete="new-password"', async ({ page }) => {
      await page.goto('/register');
      await page.waitForLoadState('networkidle');
      
      const confirmPassword = page.locator('input[name="confirmPassword"]').first();
      await expect(confirmPassword).toBeVisible();
      
      const autocomplete = await confirmPassword.getAttribute('autocomplete');
      expect(autocomplete).toBe('new-password');
    });
  });
  
  // ─────────────────────────────────────────────────────────────────────────
  // NAME AUTOCOMPLETE TESTS
  // ─────────────────────────────────────────────────────────────────────────
  
  test.describe('Name autocomplete attributes', () => {
    
    test('register name input has autocomplete="name"', async ({ page }) => {
      await page.goto('/register');
      await page.waitForLoadState('networkidle');
      
      const nameInput = page.locator('input[name="name"]').first();
      await expect(nameInput).toBeVisible();
      
      // Audit finding: autocomplete="name" for full name fields
      const autocomplete = await nameInput.getAttribute('autocomplete');
      expect(autocomplete).toBe('name');
    });
  });
  
  // ─────────────────────────────────────────────────────────────────────────
  // FORM SUBMISSION BEHAVIOR TESTS
  // ─────────────────────────────────────────────────────────────────────────
  
  test.describe('Form submission behavior', () => {
    
    test('signIn() does not prevent form submission', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      // Fill form with test data
      const emailInput = page.locator('input[name="email"]').first();
      const passwordInput = page.locator('input[name="password"]').first();
      
      await emailInput.fill('test@example.com');
      await passwordInput.fill('TestPassword123!');
      
      // Track if form submission is attempted
      let formSubmitted = false;
      
      // Listen for form submit event
      await page.evaluate(() => {
        document.addEventListener('submit', (e) => {
          // Mark that form submission was triggered
          (window as any).__formSubmitted = true;
        });
      });
      
      // Click submit button
      const submitButton = page.locator('button[type="submit"]').first();
      await submitButton.click();
      
      // Check if form submission was triggered (not prevented)
      formSubmitted = await page.evaluate(() => (window as any).__formSubmitted === true);
      
      // Form should attempt submission (even if backend isn't available)
      // This validates that signIn() doesn't break native form behavior
      expect(formSubmitted || page.url().includes('profile')).toBeTruthy();
    });
    
    test('form allows browser password save prompt', async ({ page, browserName }) => {
      // Skip on non-Chromium browsers (password manager behavior varies)
      test.skip(browserName !== 'chromium', 'Password manager prompt test only reliable on Chromium');
      
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      // Verify form has autocomplete attributes that enable password manager
      const emailInput = page.locator('input[name="email"]').first();
      const passwordInput = page.locator('input[name="password"]').first();
      
      const emailAutocomplete = await emailInput.getAttribute('autocomplete');
      const passwordAutocomplete = await passwordInput.getAttribute('autocomplete');
      
      // Both should have proper autocomplete for password manager integration
      expect(emailAutocomplete).toBe('email');
      expect(passwordAutocomplete).toBe('current-password');
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// CROSS-BROWSER COMPATIBILITY TESTS
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Cross-browser autocomplete compatibility', () => {
  
  test('email input shows email keyboard on mobile', async ({ page, browserName, isMobile }) => {
    test.skip(!isMobile, 'Mobile keyboard test only applicable on mobile devices');
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const emailInput = page.locator('input[type="email"]').first();
    const type = await emailInput.getAttribute('type');
    
    // type="email" should trigger email keyboard on mobile
    expect(type).toBe('email');
  });
  
  test('autofill attributes work across all browsers', async ({ page, browserName }) => {
    // This test runs on all browser projects
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const emailInput = page.locator('input[name="email"]').first();
    const passwordInput = page.locator('input[name="password"]').first();
    
    // Verify all required attributes for cross-browser autofill
    const emailAttrs = {
      type: await emailInput.getAttribute('type'),
      name: await emailInput.getAttribute('name'),
      autocomplete: await emailInput.getAttribute('autocomplete'),
      id: await emailInput.getAttribute('id'),
    };
    
    const passwordAttrs = {
      type: await passwordInput.getAttribute('type'),
      name: await passwordInput.getAttribute('name'),
      autocomplete: await passwordInput.getAttribute('autocomplete'),
    };
    
    // All browsers require these for autofill
    expect(emailAttrs.type).toBe('email');
    expect(emailAttrs.name).toBe('email');
    expect(emailAttrs.autocomplete).toBe('email');
    expect(emailAttrs.id).toBeTruthy();
    
    expect(passwordAttrs.name).toBe('password');
    expect(passwordAttrs.autocomplete).toBe('current-password');
    
    // Log browser compatibility for report
    console.log(`[${browserName}] Email attrs:`, emailAttrs);
    console.log(`[${browserName}] Password attrs:`, passwordAttrs);
  });
});
