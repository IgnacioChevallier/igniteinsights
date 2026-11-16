import { expect, test } from "@playwright/test";

// No cookie: the product view is public, everything else still needs a session (middleware.ts).
test.use({ storageState: { cookies: [], origins: [] } });

test("un visitante sin sesión ve el mapa pero no el panel admin", async ({ page, request }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("link", { name: "Ingresar" })).toHaveAttribute("href", "/login");
  await expect(page.getByText(/sin supresión/)).toBeVisible();

  expect((await request.get("/api/v1/operativo/estado")).status()).toBe(200);
  expect((await request.post("/api/playground/run")).status()).toBe(401);

  await page.goto("/cuenta");
  await expect(page).toHaveURL(/\/login\?next=%2Fcuenta$/);
});

test("en mobile los detalles del pronóstico arrancan plegados", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const toggle = page.getByRole("button", { name: "Ver detalles del pronóstico" });
  await expect(toggle).toBeVisible();
  await expect(page.getByText("Meteorología")).toBeHidden();

  await toggle.click();
  await expect(page.getByText("Meteorología")).toBeVisible();
  await page.getByRole("button", { name: "Ocultar detalles" }).click();
  await expect(page.getByText("Meteorología")).toBeHidden();
});
