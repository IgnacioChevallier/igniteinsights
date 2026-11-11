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

    // One line, and it is a link: as plain text the window read as a fixed property of
    // the button rather than the one thing you change between runs.
    const window_ = aside.getByRole("link", { name: /Incendios FIRMS/ });
    await expect(window_).toBeVisible();
    await expect(window_).toHaveAttribute("href", "/settings");

    // The paragraphs that used to explain all this are gone on purpose.
    await expect(aside.getByText(/Meteorología GFS/)).toHaveCount(0);
    await expect(aside.getByText(/Sin volver a pedir/)).toHaveCount(0);
    await expect(aside.getByText(/Las fuentes se configuran/)).toHaveCount(0);

    // The gear the header already had, now beside the button it configures.
    await expect(aside.getByRole("link", { name: "Configuración" })).toBeVisible();

    await page.screenshot({ path: "../outputs/playwright/current/map-real-run.png" });
  });

  test("el engranaje del mapa configura las mismas fuentes que usa el boton", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Mapa" }).click();

    const aside = page.locator("aside").first();
    await expect(aside.getByText(/Incendios FIRMS · últimos 1 día/)).toBeVisible();
    await aside.getByRole("link", { name: "Configuración" }).click();

    // One settings page, reached from either entry point — not a second copy of the form.
    // Generous: a dev server compiles /settings on its first visit.
    await expect(
      page.getByRole("heading", { name: "Configuración", exact: true }),
    ).toBeVisible({ timeout: 30_000 });
    // Retried until it sticks: the heading is server-rendered, so it goes visible before
    // React hydrates, and a fill landing in that gap sets the DOM value while onChange
    // never fires. Polling on the stored value is what makes this deterministic.
    await expect
      .poll(
        async () => {
          await page.locator("#firms_day_range").fill("4");
          return page.evaluate(
            () =>
              JSON.parse(localStorage.getItem("igniteinsights.settings") ?? "{}")
                .firms_day_range,
          );
        },
        { timeout: 15_000 },
      )
      .toBe(4);

    // Back lands on the map: it is the default section. Clicking "Mapa" here raced the
    // navigation and asserted against the page being torn down.
    await page.getByRole("button", { name: "← Volver al panel" }).click();

    // What the map says it will pull has to be what the settings page just wrote.
    await expect(aside.getByText(/Incendios FIRMS · últimos 4 días/)).toBeVisible({
      timeout: 15_000,
    });
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
  });
});
