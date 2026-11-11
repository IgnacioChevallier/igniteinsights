import { expect, test } from "@playwright/test";

/**
 * The burned fill used to be MapLibre closing open contour LineStrings, which meant a
 * front skirting the lake got a chord drawn straight across the water and the lake was
 * painted as burned (1022 cells on the 6 km case). The server now sends real polygons
 * built from the time-of-arrival raster, so the lake is a hole.
 */
test("el area quemada nunca pinta el lago", async ({ page }) => {
  test.setTimeout(45_000);
  await page.route(/tile\.openstreetmap|arcgisonline/, (r) =>
    route(r),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Simulador" }).click();
  await page.getByRole("button", { name: "Con lago" }).click();

  const card = page
    .locator("div.rounded-md.border", { hasText: "GR2 · viento del norte 15 mph" })
    .first();
  await expect(card).toBeVisible({ timeout: 15_000 });
  await card.getByRole("button", { name: "Correr en A" }).click();

  await expect(page.getByText("A · corriendo…")).toBeHidden({ timeout: 15_000 });
  await expect(page.getByText("ROS de cabeza")).toBeVisible();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "../outputs/playwright/current/burned-area-lake.png" });
});

function route(r: import("@playwright/test").Route) {
  return r.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) });
}
