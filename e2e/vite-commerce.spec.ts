import { test, expect } from "@playwright/test";

/**
 * Vite storefront (port 8080): discover uses mock/API-backed catalog; no OAuth required.
 * Full Stripe modal is environment-dependent — this flow stops at checkout page load.
 */
test.describe("Vite commerce smoke", () => {
  test("discover → product → size → add to cart → cart → checkout", async ({ page }) => {
    await page.goto("/discover");
    await expect(page.getByRole("heading", { name: "Discover" })).toBeVisible({ timeout: 60_000 });

    const productLink = page.locator('a[href^="/product/"]').first();
    await expect(productLink).toBeVisible({ timeout: 30_000 });
    await productLink.click();
    await expect(page).toHaveURL(/\/product\/.+/);

    const sizePicker = page.locator("div.flex.flex-wrap.gap-2").getByRole("button").first();
    await expect(sizePicker).toBeVisible({ timeout: 15_000 });
    await sizePicker.click();

    const add = page.getByRole("button", { name: /Add to Cart/ });
    await expect(add).toBeVisible();
    await add.click();

    await page.goto("/cart");
    await expect(page).toHaveURL(/\/cart$/);

    await page.goto("/checkout");
    await expect(page).toHaveURL(/\/checkout$/);
  });
});
