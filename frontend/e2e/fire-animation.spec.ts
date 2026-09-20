import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * Visual verification of the fire progression animation (VISUALIZACION-ANIMADA.md parte 1).
 *
 * Neither the FastAPI backend nor ELMFIRE is needed: the page is driven against a stub
 * serving the same envelopes, and the basemap tiles are stubbed to a flat colour so a
 * screenshot never depends on a tile server being reachable.
 */

const SHOTS = path.join(__dirname, "..", "playwright-screenshots");

// 1x1 dark-slate PNG standing in for a basemap tile, so contrast against the fire
// layers is the same on every run.
const TILE = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNQ0zIAAAD6AIFm9wynAAAAAElFTkSuQmCC",
  "base64",
);

async function setup(page: Page) {
  fs.mkdirSync(SHOTS, { recursive: true });
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));

  await page.route(/tile\.openstreetmap\.org|server\.arcgisonline\.com/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: TILE }),
  );

  await page.goto("/", { waitUntil: "networkidle" });
  // The controls render only once timed isochrones have arrived.
  await expect(page.getByLabel("Hora simulada")).toBeVisible({ timeout: 20_000 });
  await page.waitForTimeout(1500); // let the basemap and first paint settle
  return errors;
}

/** Pause and park the clock at an exact hour — a screenshot of a running loop is a
 *  screenshot of an arbitrary instant. */
async function freezeAt(page: Page, hours: number) {
  const pause = page.getByRole("button", { name: "Pausar animación" });
  if (await pause.isVisible().catch(() => false)) await pause.click();
  await page.getByLabel("Hora simulada").evaluate((el, value) => {
    const input = el as HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    setter.call(input, String(value));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }, hours);
  await page.waitForTimeout(500);
}

test("progression renders and visibly changes across the clock", async ({ page }) => {
  const errors = await setup(page);
  const map = page.locator(".maplibregl-map").first();
  const canvas = page.locator("canvas.maplibregl-canvas").first();
  const shots: Record<number, Buffer> = {};

  for (const t of [0, 3, 6, 12]) {
    await freezeAt(page, t);
    await expect(page.getByText(`${t},0 h`, { exact: true }).first()).toBeVisible();
    await map.screenshot({ path: path.join(SHOTS, `progression-t${t}.png`) });
    shots[t] = await canvas.screenshot();
  }

  // If the filter were not being applied the four frames would be byte-identical.
  const hours = [0, 3, 6, 12];
  for (let i = 1; i < hours.length; i += 1) {
    expect(
      shots[hours[i]].equals(shots[hours[i - 1]]),
      `t=${hours[i - 1]} and t=${hours[i]} render identically — the clock is not filtering`,
    ).toBe(false);
  }

  // Scrubber dragged to a non-integer hour, mid isochrone step.
  await freezeAt(page, 8.5);
  await map.screenshot({ path: path.join(SHOTS, "progression-scrubbed-t8.5.png") });

  // Controls on their own, to judge legibility and alignment.
  await freezeAt(page, 2);
  await page
    .locator("input[aria-label='Hora simulada']")
    .locator("xpath=ancestor::div[contains(@class,'bg-card')][1]")
    .screenshot({ path: path.join(SHOTS, "controls-closeup.png") });

  await page.screenshot({ path: path.join(SHOTS, "dashboard-full.png") });

  fs.writeFileSync(path.join(SHOTS, "console-errors.txt"), errors.join("\n") || "(ninguno)");
  expect(errors, `errores de consola:\n${errors.join("\n")}`).toEqual([]);
});

test("play, pause and speed controls drive the clock", async ({ page }) => {
  await setup(page);
  const slider = page.getByLabel("Hora simulada");

  await freezeAt(page, 0);
  await expect(slider).toHaveValue("0");

  await page.getByRole("button", { name: "Reproducir animación" }).click();
  await page.getByRole("button", { name: "2×" }).click();
  await page.waitForTimeout(1200);
  const running = Number(await slider.inputValue());
  expect(running, "the clock must advance while playing").toBeGreaterThan(0);

  await page.getByRole("button", { name: "Pausar animación" }).click();
  const paused = Number(await slider.inputValue());
  await page.waitForTimeout(700);
  expect(Number(await slider.inputValue()), "a paused clock must not advance").toBe(paused);
});
