import { expect, test } from "@playwright/test";

/**
 * The playground draws synthetic scenarios: flat ground, one fuel class, uniform wind.
 * A satellite basemap under that is actively misleading, so the map has to show what the
 * scenario assumes instead — and still let the operator switch back to the real imagery.
 *
 * Runs against the real backend (the scenario geometry and its colour are built
 * server-side, so stubbing them would test the fixture rather than the pipeline).
 */
test.describe("mapa esquemático del playground", () => {
  test.beforeEach(async ({ page }) => {
    // Basemap tiles must never decide whether a screenshot passes.
    await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
      route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
    );
    await page.goto("/");
    await page.getByRole("button", { name: "Playground" }).click();
  });

  test("dibuja el escenario y conserva el mapa real", async ({ page }) => {
    await expect(page.getByText(/Dominios .*sintéticos/)).toBeVisible();

    // TU5 with wind and slope exercises every synthetic layer at once.
    const card = page
      .locator("div.rounded-md.border", { hasText: "TU5 · la propuesta de IGN-20" })
      .first();
    await card.getByRole("button", { name: "Correr en A" }).click();

    // The scenario is drawn immediately — the slab and the vectors do not wait for
    // ELMFIRE — so the fuel legend is not evidence the run finished.
    await expect(page.getByText("TU5 · Bosque con sotobosque").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Esquemático" }).first()).toBeVisible();

    // The run itself is a real ELMFIRE call on a 12 km domain. Wait for the result.
    await expect(page.getByText("A · corriendo…")).toBeHidden({ timeout: 180_000 });
    await expect(page.getByText("ROS de cabeza")).toBeVisible();

    // A synthetic run has no FIRMS input: claiming one in the legend would invite reading
    // the slab as real ground.
    await expect(page.getByText("Perímetro FIRMS observado", { exact: false })).toHaveCount(0);

    // The wind key names its compass point, which is the only part of a 15 mph difference
    // in direction that survives into a still screenshot.
    await expect(page.getByText("viento 15 mph hacia el S", { exact: true })).toBeVisible();
    // This scenario has no slope, so no slope arrow and no slope key.
    await expect(page.getByText(/pendiente .* cuesta abajo/)).toHaveCount(0);

    // Both legends live at bottom-left; at the same offset the scenario box covered the
    // isochrone key completely.
    // The horizon comes from the isochrones, not a 12 h fallback: this preset runs 6 h,
    // and a ramp stretched to 12 would never reach its red end.
    await expect(page.getByText(/Isócronas previstas 0 → 6 h/).first()).toBeVisible();

    // The real imagery stays one click away.
    await expect(page.getByRole("button", { name: "Satélite" }).first()).toBeVisible();

    await page.screenshot({
      path: "../playwright-screenshots/playground-synthetic.png",
      fullPage: false,
    });

    await page.getByRole("button", { name: "Satélite" }).first().click();
    await page.waitForTimeout(1200);
    await page.screenshot({
      path: "../playwright-screenshots/playground-satellite.png",
      fullPage: false,
    });

    // Last, because switching terrain deliberately discards the result the screenshots
    // above are meant to show. The lake is picked as a picture and redraws without a
    // second ELMFIRE call: it comes from POST /preview, which is pure geometry.
    await page.getByRole("button", { name: "Con lago" }).click();
    await expect(page.getByText("lago (no combustible)").first()).toBeVisible();
    // The result on screen was produced on the old ground; leaving it up would invite
    // reading a lake-less run as if the barrier had been there.
    await expect(page.getByText("ROS de cabeza")).toHaveCount(0);

    await page.getByRole("button", { name: "Uniforme" }).click();
    await expect(page.getByText("lago (no combustible)")).toHaveCount(0);
  });
});
