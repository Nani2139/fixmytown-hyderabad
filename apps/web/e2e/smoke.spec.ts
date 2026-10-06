import { expect, test } from "@playwright/test";

test.use({
  geolocation: { latitude: 17.3616, longitude: 78.4747 },
  permissions: ["geolocation"],
});

test("home map opens an empty circle", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: /FixMyTown/ })).toBeVisible();
  await expect(page.getByText(/Nothing open in this circle yet|ఈ వృత్తంలో ఇంకా/)).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.locator(".leaflet-container")).toBeVisible();
});

test("sign in offers Google", async ({ page }) => {
  await page.goto("/signin");
  await expect(page.getByRole("button", { name: "Continue with Google" })).toBeVisible();
});

test("ask has no sample tickets to cite", async ({ page }) => {
  await page.goto("/ask");
  await page.getByPlaceholder(/ask a question/i).fill("open pothole Charminar");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.locator(".answer")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("link", { name: /WW-24-/ })).toHaveCount(0);
});
