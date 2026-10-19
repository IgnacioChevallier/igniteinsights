import { expect, test } from "@playwright/test";

/**
 * 3D terrain is opt-in: the 2D map stays the default, and a synthetic scenario (which
 * assumes flat ground) cannot be draped over real relief.
 */
test.beforeEach(async ({ page }) => {
  // Empty bodies: the elevation tiles fail to decode, which must not break the map either.
  await page.route(/tile\.openstreetmap|arcgisonline|\/api\/v1\/terrain\//, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
  await page.goto("/");
});

test("el relieve 3D se activa y se desactiva", async ({ page }) => {
  await page.getByRole("button", { name: "Mapa" }).click();

  const map = page.locator("[data-terrain]").first();
  const toggle = page.getByRole("button", { name: "3D" }).first();
  await expect(map).toHaveAttribute("data-terrain", "off");
  await expect(toggle).toHaveAttribute("aria-pressed", "false");

  const particles = page.getByTestId("wind-particle-canvas");
  await expect(particles).toHaveAttribute("data-particle-count", /^[1-9]/, { timeout: 20_000 });

  await toggle.click();
  await expect(map).toHaveAttribute("data-terrain", "on");
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  // Over terrain each particle step costs a GPU readback; only the draped speed surface stays.
  await expect(particles).toHaveAttribute("data-particle-count", "0");

  await toggle.click();
  await expect(map).toHaveAttribute("data-terrain", "off");
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect(particles).toHaveAttribute("data-particle-count", /^[1-9]/);
});

test("el mapa esquemático no admite relieve", async ({ page }) => {
  await page.getByRole("button", { name: "Simulador" }).click();

  const map = page.locator("[data-terrain]").first();
  const toggle = page.getByRole("button", { name: "3D" }).first();
  await expect(toggle).toBeDisabled();
  await expect(map).toHaveAttribute("data-terrain", "off");

  // Back on real imagery the relief is available again.
  await page.getByRole("button", { name: "Satélite" }).first().click();
  await expect(toggle).toBeEnabled();
});
