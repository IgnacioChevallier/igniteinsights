import { expect, test } from "@playwright/test";

/**
 * Two winds of different direction produced burn scars that looked identical, because a
 * scar elongated only ~1.1x reads as a circle whatever way you rotate it. The direction
 * was never wrong — the map just had no way to show it. So the map has to say it: an
 * animated flow field for the sense of motion, and a compass label for the still.
 */
test("el viento se lee en el mapa, y la losa muestra su combustible", async ({ page }) => {
  await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Simulador" }).click();

  const card = (name: string) =>
    page.locator("div.rounded-md.border", { hasText: name }).first();

  // Two winds 45 degrees apart, the pair that started this. Nothing is run: POST /preview
  // is pure geometry, so the map draws without waiting minutes for ELMFIRE.
  await card("GR2 · viento del norte 15 mph").getByRole("button", { name: "Correr en A" }).click();
  await card("GR2 · viento del noreste 15 mph").getByRole("button", { name: "Correr en B" }).click();

  // The compass point is the part that survives a screenshot.
  // Both slots preview and complete through the deterministic API-contract stub.
  const seen = { timeout: 30_000 };
  await expect(page.getByText("viento 15 mph hacia el S", { exact: true })).toBeVisible(seen);
  await expect(page.getByText("viento 15 mph hacia el SO", { exact: true })).toBeVisible(seen);

  await page.waitForTimeout(2500); // let the particle trails build up
  await page.screenshot({ path: "../outputs/playwright/current/wind-particles.png" });

  // The lake is a different fuel, so it must be a different texture, not just a colour.
  await page.getByRole("button", { name: "Con lago" }).click();
  await expect(page.getByText("lago (no combustible)").first()).toBeVisible();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: "../outputs/playwright/current/wind-particles-lake.png" });

  // A timber model must not look like a grassland: the texture is the whole point.
  await page.getByRole("button", { name: "Uniforme" }).click();
  await card("TL3 · el baseline").getByRole("button", { name: "Correr en A" }).click();
  await card("TU5 · la propuesta de IGN-20").getByRole("button", { name: "Correr en B" }).click();
  await expect(page.getByText(/TL3 ·/).last()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/TU5 ·/).last()).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: "../outputs/playwright/current/fuel-textures.png" });
});
