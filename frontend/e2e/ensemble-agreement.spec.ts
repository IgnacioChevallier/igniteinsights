import { expect, test } from "@playwright/test";

/**
 * "Acuerdo del ensamble" is a thematic background: off by default, fetched only when
 * enabled, exclusive with arrival time and intensity, and never a reason for the map to
 * break when the run has no artifact.
 */
test.beforeEach(async ({ page }) => {
  await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
});

test("carga el acuerdo sólo al activarlo y muestra su procedencia", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/ensemble-agreement")) requests.push(request.url());
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Mapa" }).click();
  const aside = page.locator("aside").first();
  const agreement = aside.getByRole("switch", { name: "Acuerdo del ensamble" });
  const arrival = aside.getByRole("checkbox", { name: "Tiempo de llegada" });

  await expect(agreement).not.toBeChecked();
  await page.waitForTimeout(1000);
  expect(requests).toHaveLength(0);

  await arrival.check();
  await agreement.click();
  await expect(arrival).not.toBeChecked();

  const legend = page.getByTestId("ensemble-agreement-legend");
  for (const role of ["alto acuerdo", "escenario central", "propagación posible"]) {
    await expect(legend.getByText(role)).toBeVisible();
  }
  await legend.getByRole("button", { name: "Información del acuerdo del ensamble" }).hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toContainText("Miembros válidos: 31/31");
  await expect(tooltip).toContainText("Ciclo meteorológico: GEFS 2026-09-06 00 UTC");
  await expect(tooltip).toContainText("Horizonte: 12 h");
  await expect(tooltip).toContainText("Vigencia:");
  expect(requests).toHaveLength(1);
  await page.screenshot({ path: "../playwright-screenshots/ensemble-agreement.png" });

  await arrival.check();
  await expect(agreement).not.toBeChecked();
  await expect(legend).toHaveCount(0);
});

test("sin artefacto, avisa y deja el mapa como estaba", async ({ page }) => {
  await page.route("**/api/simulations/*/ensemble-agreement", (route) =>
    route.fulfill({ status: 404, json: { detail: "No ensemble agreement artifact" } }),
  );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/");
  await page.getByRole("button", { name: "Mapa" }).click();
  const aside = page.locator("aside").first();
  await aside.getByRole("switch", { name: "Acuerdo del ensamble" }).click();

  await expect(
    aside.getByText("No hay acuerdo del ensamble disponible para esta ejecución."),
  ).toBeVisible();
  await expect(page.getByTestId("ensemble-agreement-legend")).toHaveCount(0);
  // The panel's "Algunas capas no se cargaron" alert: an absent artifact is not a failure.
  await expect(aside.getByRole("alert")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("un artefacto incompleto no se dibuja", async ({ page }) => {
  await page.route("**/api/simulations/*/ensemble-agreement", (route) =>
    route.fulfill({
      json: {
        status: "success",
        data: { layer: { id: "ensemble_agreement" }, metadata: { valid_members: 31 } },
        error: null,
      },
    }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Mapa" }).click();
  const aside = page.locator("aside").first();
  await aside.getByRole("switch", { name: "Acuerdo del ensamble" }).click();

  await expect(aside.getByText(/El artefacto de acuerdo está incompleto/)).toBeVisible();
  await expect(page.getByTestId("ensemble-agreement-legend")).toHaveCount(0);
});
