import { expect, test } from "@playwright/test";

/**
 * "Acuerdo del ensamble" is a thematic background: off by default, fetched only when
 * ticked, exclusive with arrival time and intensity, and never a reason for the map to
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
  const agreement = aside.getByRole("checkbox", { name: "Acuerdo del ensamble" });
  const arrival = aside.getByRole("checkbox", { name: "Tiempo de llegada" });

  await expect(agreement).not.toBeChecked();
  await page.waitForTimeout(1000);
  expect(requests).toHaveLength(0);

  await arrival.check();
  await agreement.check();
  await expect(arrival).not.toBeChecked();

  const legend = page.getByTestId("ensemble-agreement-legend");
  await expect(legend.getByText("acuerdo entre simulaciones", { exact: true })).toBeVisible();
  await expect(legend.getByText("31/31")).toBeVisible();
  await expect(legend.getByText("GEFS 2026-09-06 00 UTC")).toBeVisible();
  await expect(legend.getByText("12 h")).toBeVisible();
  await expect(legend.getByText("Vigencia")).toBeVisible();
  await expect(legend.getByText("Generado")).toBeVisible();
  await expect(legend.getByText("No es una probabilidad calibrada.")).toBeVisible();
  await expect(legend.getByText(/no considera combate ni supresión/)).toBeVisible();
  await expect(legend.getByText(/puede extenderse fuera de la zona ≥ 0,10/)).toBeVisible();
  for (const role of ["alto acuerdo", "escenario central", "propagación posible"]) {
    await expect(legend.getByText(role)).toBeVisible();
  }
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
  await aside.getByRole("checkbox", { name: "Acuerdo del ensamble" }).check();

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
  await aside.getByRole("checkbox", { name: "Acuerdo del ensamble" }).check();

  await expect(aside.getByText(/El artefacto de acuerdo está incompleto/)).toBeVisible();
  await expect(page.getByTestId("ensemble-agreement-legend")).toHaveCount(0);
});
