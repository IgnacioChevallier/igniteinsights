import { expect, test } from "@playwright/test";

const EMPTY_COLLECTION = { type: "FeatureCollection", features: [] };
const ISOCHRONES = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { arrival_s: 3600, arrival_hours: 1 },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-71.72, -42.62],
            [-71.7, -42.62],
            [-71.7, -42.6],
            [-71.72, -42.6],
            [-71.72, -42.62],
          ],
        ],
      },
    },
  ],
};

const envelope = (data: unknown) => ({
  status: "success",
  data,
  error: null,
  meta: { timestamp: "2026-09-20T00:00:00Z" },
});

test.beforeEach(async ({ page }) => {
  await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
});

test("prioriza las isocronas y explica la espera antes de cargar el viento", async ({ page }) => {
  let releaseIsochrones!: () => void;
  const isochronesReleased = new Promise<void>((resolve) => {
    releaseIsochrones = resolve;
  });
  const requests: string[] = [];

  await page.route("**/api/simulations/*/isochrones", async (route) => {
    requests.push("isochrones");
    await isochronesReleased;
    await route.fulfill({ json: envelope(ISOCHRONES) });
  });
  await page.route("**/api/simulations/*/ignition", async (route) => {
    requests.push("ignition");
    await route.fulfill({ json: envelope(EMPTY_COLLECTION) });
  });
  await page.route("**/api/simulations/*/stats", async (route) => {
    requests.push("stats");
    await route.fulfill({ json: envelope({ simulation_id: "test", rows: [] }) });
  });
  await page.route("**/api/simulations/*/wind", async (route) => {
    requests.push("wind");
    await route.fulfill({ json: envelope(null) });
  });

  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("status").filter({ hasText: "Procesando resultado" })).toBeVisible();
  await expect.poll(() => requests.length).toBe(1);
  expect(requests).toEqual(["isochrones"]);

  releaseIsochrones();
  await expect(page.getByRole("status").filter({ hasText: "Procesando resultado" })).toBeHidden();
  await expect.poll(() => requests.includes("wind")).toBe(true);
  expect(requests[0]).toBe("isochrones");
  expect(requests.indexOf("wind")).toBeGreaterThan(requests.indexOf("ignition"));
  expect(requests.indexOf("wind")).toBeGreaterThan(requests.indexOf("stats"));
});

test("muestra el error del mapa y permite reintentar", async ({ page }) => {
  let attempts = 0;
  await page.route("**/api/simulations/*/isochrones", async (route) => {
    attempts += 1;
    if (attempts === 1) {
      await route.fulfill({ status: 503, json: { detail: "Postprocesamiento no disponible" } });
      return;
    }
    await route.fulfill({ json: envelope(ISOCHRONES) });
  });
  await page.route("**/api/simulations/*/ignition", (route) =>
    route.fulfill({ json: envelope(EMPTY_COLLECTION) }),
  );
  await page.route("**/api/simulations/*/stats", (route) =>
    route.fulfill({ json: envelope({ simulation_id: "test", rows: [] }) }),
  );
  await page.route("**/api/simulations/*/wind", (route) =>
    route.fulfill({ json: envelope(null) }),
  );

  await page.goto("/", { waitUntil: "domcontentloaded" });
  const alert = page.getByRole("alert").filter({ hasText: "No se pudo cargar el resultado" });
  await expect(alert).toContainText("Postprocesamiento no disponible");

  await alert.getByRole("button", { name: "Reintentar" }).click();
  await expect(alert).toBeHidden();
  await expect(page.getByLabel("Hora simulada")).toBeVisible();
  expect(attempts).toBe(2);
});
