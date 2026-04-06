import { defineConfig, devices } from "@playwright/test";

/**
 * Vite storefront (8080) + Next app (3000). Python catalog should be on 8001 (Vite proxy).
 * Run: npm run test:e2e:playwright:fullstack
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/full-stack*.spec.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:8080",
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
    {
      command: "npm run dev:web",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
