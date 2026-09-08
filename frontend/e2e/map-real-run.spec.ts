import { expect, test } from "@playwright/test";

/**
 * Launching a real run used to be possible only from the header of the "Datos" section —
 * the map, where the result appears, had no way to start one, and its empty state told
 * the operator to run a simulation while offering no button to do it.
 *
 * Nothing here presses the button: it downloads from FIRMS and NOAA and then runs ELMFIRE
 * for minutes. What is checked is that the control is present, says what it will pull, and
 * is wired to the same settings `/settings` writes.
 */
test.describe("lanzar una corrida real desde el mapa", () => {
  test.beforeEach(async ({ page }) => {
    await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
      route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
    );
  });

  test("el boton vive en la sidebar del mapa y declara sus fuentes", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Mapa" }).click();

    const aside = page.locator("aside").first();
    const run = aside.getByRole("button", { name: "Ejecutar simulación real" });
    await expect(run).toBeVisible();
    await expect(run).toBeEnabled();

    // The defaults: live FIRMS and GFS, static layers left alone. Saying so is the point —
    // the button must not be able to pull the ~500 MB canopy layer by surprise.
    await expect(aside.getByText(/Incendios FIRMS · últimos 1 día/)).toBeVisible();
    await expect(aside.getByText(/Meteorología GFS · ciclo actual/)).toBeVisible();
    await expect(aside.getByText(/Sin volver a pedir: relieve, combustibles, dosel/)).toBeVisible();

    await page.screenshot({ path: "../playwright-screenshots/map-real-run.png" });
  });

  test("las fuentes salen de Ajustes, no de un segundo lugar", async ({ page }) => {
    await page.goto("/");
    // Written the way /settings writes it: a historical window with the static layers on.
    await page.evaluate(() =>
      localStorage.setItem(
        "igniteinsights.settings",
        JSON.stringify({
          include_firms: true, include_dem: true, include_gfs: true,
          include_worldcover: true, include_canopy: false,
          firms_day_range: 3, firms_start_date: "2024-02-01",
        }),
      ),
    );
    await page.reload();
    await page.getByRole("button", { name: "Mapa" }).click();

    const aside = page.locator("aside").first();
    await expect(aside.getByText(/Incendios FIRMS desde 2024-02-01 · 3 días/)).toBeVisible();
    // A historical fire must not be paired with today's weather, and the summary has to
    // say which cycle it will use or that guarantee is invisible.
    await expect(aside.getByText(/Meteorología GFS del mismo período/)).toBeVisible();
    await expect(aside.getByText(/relieve, combustibles \(se omiten/)).toBeVisible();
  });
});
