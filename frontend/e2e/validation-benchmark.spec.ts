import { expect, test, type Page } from "@playwright/test";

/**
 * Visor del benchmark de validación (IGN-26 §Benchmark): incendio → protocolo → receta.
 *
 * El backend se simula en el navegador: /api/validation/* devuelve una cadena contigua de
 * cuatro ventanas de 24 h con dos recetas, así el test no depende de haber corrido ELMFIRE.
 */

const TILE = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNQ0zIAAAD6AIFm9wynAAAAAElFTkSuQmCC",
  "base64",
);
const PNG = TILE.toString("base64");
const CASO = "los-alerces-2023/cadena-96h";
const INICIO = Date.parse("2023-02-04T18:00:00Z");

const ventanas = [0, 1, 2, 3].map((n) => ({
  n,
  inicio: new Date(INICIO + n * 86_400_000).toISOString(),
  horas: 24,
}));

const metricas = (dice: number) => ({
  dice, iou: dice / (2 - dice), recall: dice, precision: dice, sesgo_area: 1.2,
  alarma_sesgo: false, tp_ha: 100, fp_ha: 20, fn_ha: 30,
});

const receta = (id: string, combustible: string, dice: number) => ({
  receta: id,
  padre: id === "base-001" ? null : "base-001",
  motivo: `motivo de ${id}`,
  factores: { combustible, semilla: "prediccion" },
  git: { sha: "abc1234", sucio: false },
  ventanas_corridas: 4,
  puntuada: true,
  principal: { referencia: "cicatriz", ventana: 3, dice, sesgo_area: 1.2, alarma_sesgo: false },
  agregado_firms: null,
});

/** Cuadrados concéntricos que crecen con la hora: lo mínimo para que el reloj anime. */
function isocronas(): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: Array.from({ length: 96 }, (_, i) => {
      const r = 0.002 * (i + 1);
      const [x, y] = [-71.57, -42.88];
      return {
        type: "Feature",
        properties: { arrival_s: (i + 1) * 3600, arrival_hours: i + 1 },
        geometry: {
          type: "Polygon",
          coordinates: [[[x - r, y - r], [x + r, y - r], [x + r, y + r], [x - r, y + r], [x - r, y - r]]],
        },
      };
    }),
  };
}

const envelope = (data: unknown) => ({ status: "success", data, error: null, meta: {} });

async function setup(page: Page) {
  const errores: string[] = [];
  page.on("pageerror", (e) => errores.push(e.message));
  await page.route(/tile\.openstreetmap\.org|server\.arcgisonline\.com/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: TILE }),
  );
  await page.route(/\/api\/validation\//, (route) => {
    const url = new URL(route.request().url());
    const ruta = url.pathname.replace("/api/validation/", "");
    let data: unknown;
    if (ruta === "fires") {
      data = {
        fires: [{
          incendio: "los-alerces-2023",
          protocolos: [{
            protocolo: "cadena-96h", caso: CASO, descripcion: "Cadena de prueba",
            contiguo: true, referencias: ["cicatriz", "firms"], ventanas,
            recetas: [receta("base-001", "ccsbap2017", 0.41), receta("fuels-worldcover-001", "worldcover2021", 0.22)],
          }],
        }],
        legend: [{ code: 2, label: "Acierto", color: "#16a34a" }],
      };
    } else if (ruta === "compare") {
      data = {
        declarados: { combustible: ["ccsbap2017", "worldcover2021"] },
        no_declarados: [], codigo: null, deltas: [],
      };
    } else if (ruta.endsWith("/isochrones")) {
      data = isocronas();
    } else if (ruta.endsWith("/overlay")) {
      data = {
        image_base64: PNG,
        coordinates: [[-71.6, -42.85], [-71.54, -42.85], [-71.54, -42.91], [-71.6, -42.91]],
      };
    } else {
      const id = ruta.split("/").at(-1)!;
      data = {
        receta: id, linea_de_tiempo: true, principal: null,
        ventanas: ventanas.map((v) => ({
          ...v, semilla_ha: 1, predicho_ha: 250 * (v.n + 1),
          cicatriz: { acumulado: metricas(id === "base-001" ? 0.41 : 0.22) },
        })),
      };
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(envelope(data)) });
  });

  await page.goto("/", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Validación" }).click();
  await expect(page.getByLabel("Hora simulada")).toBeVisible({ timeout: 20_000 });
  return errores;
}

async function fijar(page: Page, horas: number) {
  const pausa = page.getByRole("button", { name: "Pausar animación" });
  if (await pausa.isVisible().catch(() => false)) await pausa.click();
  await page.getByLabel("Hora simulada").evaluate((el, value) => {
    const input = el as HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    setter.call(input, String(value));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }, horas);
}

test("la cadena se anima entera y cambiar de receta conserva el instante", async ({ page }) => {
  const errores = await setup(page);
  const reloj = page.getByLabel("Hora simulada");

  await expect(reloj).toHaveAttribute("max", "96");
  await expect(page.locator("aside table tbody tr")).toHaveCount(4);

  // Las fronteras de ventana llevan el reloj al inicio de cada una.
  await fijar(page, 0);
  await page.getByRole("button", { name: "Ventana 2", exact: true }).click();
  await expect(reloj).toHaveValue("48");

  await fijar(page, 60);
  await page.getByRole("button", { name: /fuels-worldcover-001/ }).click();
  await expect(page.getByText("combustible=worldcover2021 · semilla=prediccion")).toBeVisible();
  await expect(reloj).toHaveValue("60");

  await page.getByRole("combobox", { name: "Comparar con" }).selectOption("base-001");
  await expect(page.getByText("ccsbap2017", { exact: false }).last()).toBeVisible();
  await expect(page.getByText("Ningún cambio sin declarar en los insumos.")).toBeVisible();

  expect(errores, errores.join("\n")).toEqual([]);
});
