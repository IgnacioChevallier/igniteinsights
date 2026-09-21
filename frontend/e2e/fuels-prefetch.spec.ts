import { expect, test } from "@playwright/test";

const TILE =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNQ0zIAAAD6AIFm9wynAAAAAElFTkSuQmCC";
const SOURCES = ["ccsbap", "mapbiomas", "worldcover"] as const;

test("precarga los mapas estaticos y reutiliza la cache al abrir la pestaña", async ({ page }) => {
  const requested: string[] = [];

  await page.route(/tile\.openstreetmap|arcgisonline/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: Buffer.alloc(0) }),
  );
  await page.route("**/api/fuels?source=*", async (route) => {
    const source = new URL(route.request().url()).searchParams.get("source")!;
    requested.push(source);
    await route.fulfill({
      json: {
        status: "success",
        data: {
          source_id: source,
          source: `${source} → Scott & Burgan FBFM40`,
          available_sources: SOURCES,
          classes: [],
          total_area_ha: 0,
          image_base64: TILE,
          coordinates: [
            [-71.8, -42.6],
            [-71.7, -42.6],
            [-71.7, -42.7],
            [-71.8, -42.7],
          ],
        },
        error: null,
      },
    });
  });

  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect.poll(() => requested, { timeout: 10_000 }).toEqual([...SOURCES]);

  const requestCount = requested.length;
  await page.getByRole("button", { name: "Combustibles" }).click();
  await expect(page.getByRole("heading", { name: "Mapa de combustibles" })).toBeVisible();
  await expect(page.getByText("ccsbap → Scott & Burgan FBFM40")).toBeVisible();

  await page.getByRole("button", { name: "MapBiomas" }).click();
  await expect(page.getByText("mapbiomas → Scott & Burgan FBFM40")).toBeVisible();
  await page.getByRole("button", { name: "WorldCover" }).click();
  await expect(page.getByText("worldcover → Scott & Burgan FBFM40")).toBeVisible();

  await page.waitForTimeout(250);
  expect(requested).toHaveLength(requestCount);
});
