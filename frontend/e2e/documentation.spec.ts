import { expect, test } from "@playwright/test";

test.describe("documentación", () => {
  test("organiza la guía en tres pestañas", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Documentación" }).click();

    await expect(page.getByRole("heading", { name: "Documentación" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Cómo leer el mapa" })).toBeVisible();
    await page.getByRole("tab", { name: "Límites del modelo" }).click();
    await expect(page.getByRole("heading", { name: "Límites del modelo" })).toBeVisible();
    await page.getByRole("tab", { name: "Fuentes" }).click();
    await expect(page.getByRole("heading", { name: "Fuentes" })).toBeVisible();
    await page.getByRole("tab", { name: "Introducción" }).click();
    await expect(page.getByText(/no sustituye las observaciones en campo/i)).toBeVisible();
  });

  test("mantiene la navegación y el contenido utilizables en mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    const mainNavigation = page.getByRole("navigation", { name: "Secciones principales" });
    await expect(mainNavigation).toBeVisible();
    await mainNavigation.getByRole("button", { name: "Documentación" }).click();

    await expect(page.getByRole("heading", { name: "Documentación" })).toBeVisible();
    await expect(page.getByRole("tablist", { name: "Contenido de la documentación" })).toBeVisible();
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(390);
  });
});
