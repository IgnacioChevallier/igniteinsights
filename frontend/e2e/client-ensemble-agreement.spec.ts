import { expect, test } from "@playwright/test";

/**
 * The client view offers "Acuerdo del ensamble" only on forecasts that have one: the ensemble
 * is computed on a few passes (docs/dashboard-producto.md §8), so a forecast without it shows
 * no checkbox and never asks for the artifact.
 */
test.beforeEach(async ({ page }) => {
  await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
});

test("con ensamble, el cliente lo puede activar", async ({ page }) => {
  await page.goto("/?panel=cliente");
  const agreement = page.getByRole("switch", { name: "Acuerdo del ensamble" });
  await agreement.click();
  await expect(page.getByText("alto acuerdo")).toBeVisible();
});

test("sin ensamble en este pronóstico, no hay casilla ni pedido", async ({ page }) => {
  await page.route("**/api/v1/operativo/estado", async (route) => {
    const body = await (await route.fetch()).json();
    body.data.incendios[0].pronostico.ensamble = false; // the admin flag stays on
    await route.fulfill({ json: body });
  });
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/ensemble-agreement")) requests.push(r.url());
  });

  await page.goto("/?panel=cliente");
  await expect(page.getByText("Meteorología")).toBeVisible();
  await expect(page.getByRole("switch", { name: "Acuerdo del ensamble" })).toHaveCount(0);
  await expect(page.getByText(/Todavía no hay acuerdo|No se pudo leer el acuerdo/)).toHaveCount(0);
  expect(requests).toEqual([]);
});
