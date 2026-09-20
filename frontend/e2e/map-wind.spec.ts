import { expect, test } from "@playwright/test";

/**
 * The wind the run was actually driven by, animated over the map the way the playground
 * animates a scenario's. Read from the run's own ws/wd rasters, so it cannot disagree with
 * what ELMFIRE was given, and it follows the clock: GFS carries one band per hour.
 */
test("el mapa anima el viento real de la corrida", async ({ page }) => {
  await page.route(/tile\.openstreetmap|arcgisonline/, (r) =>
    r.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Mapa" }).click();

  const aside = page.locator("aside").first();
  // Says the direction in words, because an animation says nothing in a screenshot.
  await expect(aside.getByText(/viento .* mph hacia el/)).toBeVisible({ timeout: 20_000 });

  await page.waitForTimeout(2500); // let the particle trails build
  await page.screenshot({ path: "../playwright-screenshots/map-wind.png" });
});
