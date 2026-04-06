import { test, expect } from "@playwright/test";

const PY_API = process.env.E2E_PYTHON_API ?? "http://localhost:8001";

test.describe("Vite commerce (needs Python API on 8001)", () => {
  test.beforeAll(async () => {
    try {
      const r = await fetch(`${PY_API}/api/products?limit=1`);
      if (!r.ok) {
        test.skip(true, `Python catalog not reachable at ${PY_API} — start backend first`);
      }
      const data = await r.json();
      if (!Array.isArray(data) || data.length < 1) {
        test.skip(true, "No products from /api/products — seed DB or check backend");
      }
    } catch {
      test.skip(true, `Python catalog not reachable at ${PY_API} — start backend first`);
    }
  });

  test("discover → product → size → cart → checkout", async ({ page }) => {
    await page.goto("http://localhost:8080/discover");
    await expect(page.getByRole("heading", { name: "Discover" })).toBeVisible({ timeout: 120_000 });

    const productLink = page.locator('a[href^="/product/"]').first();
    await expect(productLink).toBeVisible({ timeout: 60_000 });
    await productLink.click();
    await expect(page).toHaveURL(/\/product\/.+/);

    const sizePicker = page.locator("div.flex.flex-wrap.gap-2").getByRole("button").first();
    await expect(sizePicker).toBeVisible({ timeout: 20_000 });
    await sizePicker.click();

    const add = page.getByRole("button", { name: /Add to Cart/ });
    await expect(add).toBeVisible();
    await add.click();

    await page.goto("http://localhost:8080/cart");
    await expect(page).toHaveURL(/\/cart$/);

    await page.goto("http://localhost:8080/checkout");
    await expect(page).toHaveURL(/\/checkout$/);
  });
});

test.describe("Next auth shell (Fastify OAuth proxy expected at 4000 for real sign-in)", () => {
  test("login page and OAuth entry points (no provider round-trip in headless)", async ({ page }) => {
    await page.goto("http://localhost:3000/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible({ timeout: 120_000 });
    await expect(page.getByRole("link", { name: "Continue with Google" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Continue with Facebook" })).toBeVisible();

    await page.goto("http://localhost:3000/app");
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  });
});
