import { expect, test } from "@playwright/test";

/**
 * The wind the run was actually driven by, animated over the map the way the playground
 * animates a scenario's. Read from the run's own ws/wd rasters, so it cannot disagree with
 * what ELMFIRE was given, and it follows the clock: GFS carries one band per hour.
 */
test("el mapa anima el viento real de la corrida", async ({ page }) => {
  await page.route(/tile\.openstreetmap|arcgisonline/, (r) =>
    r.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Mapa" }).click();

  const aside = page.locator("aside").first();
  // Says the direction in words, because an animation says nothing in a screenshot.
  await expect(aside.getByText(/viento .* mph hacia el/)).toBeVisible({ timeout: 20_000 });
  await expect(aside.getByText(/GFS 0,25°/)).toBeVisible();
  await expect(aside.getByText(/entrada de ELMFIRE/)).toBeVisible();

  const surfaceToggle = aside.getByRole("checkbox", { name: "Velocidad del viento" });
  const particles = page.getByTestId("wind-particle-canvas");
  await expect(surfaceToggle).not.toBeChecked();
  await surfaceToggle.check();
  await expect(particles).toHaveAttribute("data-wind-surface-visible", "true");

  await page.waitForTimeout(2500); // let the particle trails build
  await expect
    .poll(async () =>
      particles.evaluate((canvas: HTMLCanvasElement) => {
        const context = canvas.getContext("2d");
        if (!context) return false;
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        for (let index = 3; index < pixels.length; index += 64) {
          if (pixels[index] > 0) return true;
        }
        return false;
      }),
    )
    .toBe(true);

  const box = await particles.boundingBox();
  if (!box) throw new Error("wind canvas has no layout box");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page.getByTestId("wind-hover-readout")).toContainText(/mph · hacia el/);

  await page.screenshot({ path: "../playwright-screenshots/map-wind.png" });

  // Zooming out shrinks the projected wind domain, so its screen-space population must
  // fall with it instead of packing the same number of streaks into a smaller footprint.
  // The canvas must also keep advancing while MapLibre animates.
  const countBeforeZoom = Number(await particles.getAttribute("data-particle-count"));
  await page.getByRole("button", { name: "Zoom out" }).click();
  await page.waitForTimeout(60);
  const firstZoomFrame = await particles.evaluate((canvas: HTMLCanvasElement) =>
    canvas.toDataURL(),
  );
  await page.waitForTimeout(100);
  const secondZoomFrame = await particles.evaluate((canvas: HTMLCanvasElement) =>
    canvas.toDataURL(),
  );
  expect(secondZoomFrame).not.toBe(firstZoomFrame);
  await expect
    .poll(async () => Number(await particles.getAttribute("data-particle-count")))
    .toBeLessThan(countBeforeZoom);

  const horizontalCentroid = () =>
    particles.evaluate((canvas: HTMLCanvasElement) => {
      const pixels = canvas.getContext("2d")?.getImageData(0, 0, canvas.width, canvas.height).data;
      if (!pixels) return 0;
      let weightedX = 0;
      let alpha = 0;
      for (let offset = 3; offset < pixels.length; offset += 4) {
        const value = pixels[offset];
        if (!value) continue;
        weightedX += ((offset - 3) / 4 % canvas.width) * value;
        alpha += value;
      }
      return alpha ? weightedX / alpha : 0;
    });

  await page.waitForTimeout(300);
  const centroidBeforePan = await horizontalCentroid();
  await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.35);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.35 + 120, box.y + box.height * 0.35, {
    steps: 8,
  });
  await page.mouse.up();
  await page.waitForTimeout(80);
  const centroidAfterPan = await horizontalCentroid();
  expect(centroidAfterPan).toBeGreaterThan(centroidBeforePan + 20);
});

test("movimiento reducido conserva una lectura estática del viento", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Mapa" }).click();

  const canvas = page.getByTestId("wind-particle-canvas");
  await expect(canvas).toBeVisible({ timeout: 20_000 });
  await page.waitForTimeout(500);
  const first = await canvas.evaluate((node: HTMLCanvasElement) => node.toDataURL());
  await page.waitForTimeout(500);
  const second = await canvas.evaluate((node: HTMLCanvasElement) => node.toDataURL());
  expect(second).toBe(first);
});

test("interpola componentes entre horas sin cruzar el rumbo opuesto", async ({ page }) => {
  const component = (azimuth: number) => {
    const radians = (azimuth * Math.PI) / 180;
    return { u: Math.sin(radians) * 10, v: Math.cos(radians) * 10 };
  };
  const first = component(350);
  const second = component(10);
  const band = (hour: number, vector: { u: number; v: number }) => ({
    hour,
    u_mph: Array(16).fill(vector.u),
    v_mph: Array(16).fill(vector.v),
    speed_min_mph: 10,
    speed_max_mph: 10,
    speed_mph: 10,
    blows_to_deg: hour ? 10 : 350,
    direction_consistency: 1,
    label: "viento 10,0 mph hacia el N",
  });
  const data = {
    schema_version: 2,
    bounds: [-71.9, -42.82, -71.7, -42.58],
    ring: [
      [-71.9, -42.58], [-71.7, -42.58], [-71.7, -42.82],
      [-71.9, -42.82], [-71.9, -42.58],
    ],
    width: 4,
    height: 4,
    unit: "mph",
    basis: "elmfire_20ft",
    height_m: 6.096,
    source_model: "GFS 0.25°",
    forecast_start: null,
    forecast_cycle: null,
    step_hours: 1,
    bands: [band(0, first), band(1, second)],
  };
  await page.route("**/api/simulations/*/wind", (route) =>
    route.fulfill({
      json: {
        status: "success",
        data,
        error: null,
        meta: { timestamp: "2026-09-21T00:00:00Z" },
      },
    }),
  );
  await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Mapa" }).click();
  await page.getByRole("button", { name: "Pausar animación" }).click();
  await page.getByLabel("Hora simulada").evaluate((input: HTMLInputElement) => {
    input.value = "0.5";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  const canvas = page.getByTestId("wind-particle-canvas");
  const box = await canvas.boundingBox();
  if (!box) throw new Error("wind canvas has no layout box");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page.getByTestId("wind-hover-readout")).toContainText("hacia el N");
});
