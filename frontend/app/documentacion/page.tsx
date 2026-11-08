import { headers } from "next/headers";
import { ClientHeader } from "@/components/client-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { auth } from "@/lib/auth";

/**
 * What a client must know before reading the map (docs/producto.md §6): the
 * model's limits in plain language — the same ones documented in docs/resultados/modelo/limites.md
 * and RIESGOS_Y_SUPOSICIONES.md record — and every data source with its attribution.
 * Keep it in step with those documents when they change.
 */
const LIMITES: { titulo: string; texto: string }[] = [
  {
    titulo: "Es propagación potencial, sin supresión",
    texto:
      "El modelo no incluye el combate: brigadas, medios aéreos, cortafuegos ni líneas de defensa. Muestra hacia dónde y cuánto podría avanzar el fuego si nadie lo frenara.",
  },
  {
    titulo: "No predice el perímetro exacto",
    texto:
      "Las isócronas indican la tendencia del frente (dirección, velocidad, zonas expuestas). El borde real puede quedar adentro o afuera de lo dibujado.",
  },
  {
    titulo: "Horizonte de 24 h desde la última pasada satelital",
    texto:
      "Cada pronóstico arranca de lo que vio el satélite VIIRS en su última pasada y mira hasta 24 h hacia adelante. Sobre la zona hay dos tandas de pasadas por día (madrugada y tarde); entre una y otra el pronóstico no se actualiza.",
  },
  {
    titulo: "Los datos satelitales llegan con demora",
    texto:
      "NASA FIRMS publica las detecciones unas 3 h después de la pasada, sin garantía (a veces más). Por eso, parte de la ventana seleccionada ya transcurrió cuando el producto está disponible.",
  },
  {
    titulo: "La meteorología es un pronóstico",
    texto:
      "Viento, temperatura y humedad salen del pronóstico GFS (NOAA), de celdas de ~25 km. Su error se suma al del modelo de fuego.",
  },
  {
    titulo: "Sin pavesas",
    texto:
      "El modelo no simula pavesas (brasas que el viento lleva y encienden focos adelante del frente).",
  },
  {
    titulo: "Combustibles de 2017",
    texto:
      "La vegetación sale del mapa CCS-BAP (2017), traducido a modelos de combustible. Las quemas posteriores se corrigen con datos de pérdida de bosque, pero otros cambios de la vegetación no están.",
  },
  {
    titulo: "Acuerdo del ensamble: no es una probabilidad",
    texto:
      "Indica en qué fracción de 31 escenarios meteorológicos (ensamble GEFS) se quema cada celda. Comunica cuánto depende el pronóstico del tiempo; no es la probabilidad de que el fuego llegue.",
  },
];

const FUENTES: { dato: string; fuente: string; atribucion: string }[] = [
  {
    dato: "Detecciones de fuego",
    fuente: "NASA FIRMS, VIIRS 375 m (S-NPP, NOAA-20, NOAA-21)",
    atribucion:
      "We acknowledge the use of data from NASA's Fire Information for Resource Management System (FIRMS), part of NASA's Earth Science Data and Information System (ESDIS).",
  },
  {
    dato: "Meteorología",
    fuente: "NOAA NCEP GFS 0,25° (pronóstico) y GEFS (ensamble)",
    atribucion: "Datos de dominio público de NOAA, vía NOAA Open Data Dissemination.",
  },
  {
    dato: "Relieve",
    fuente: "Copernicus DEM GLO-30, vía OpenTopography",
    atribucion:
      "© DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, provisto bajo COPERNICUS por la Unión Europea y la ESA; todos los derechos reservados.",
  },
  {
    dato: "Vegetación (combustibles)",
    fuente:
      "Clasificación de Tipos Forestales y Cobertura del Suelo de la Región Bosque Andino Patagónico (CCS-BAP, 2017)",
    atribucion:
      "Mohr-Bell D, Díaz G, Príncipe R, Gonzalez C, Bono J, Ciuffoli L, Strada M, Parmuchi G, Chomnalez F, Montenegro C, Loguercio G, Bava J, 2019. Monitoreo de la Superficie de Bosque Nativo de la República Argentina, Región Forestal Bosque Andino Patagónico. Tomo I Informe. Secretaría de Ambiente y Desarrollo Sustentable de la Nación. Esquel (Chubut), Argentina. 87 pp. Uso autorizado por CIEFAP.",
  },
  {
    dato: "Relleno de vegetación en el límite internacional",
    fuente: "ESA WorldCover 2021 v200",
    atribucion: "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021). CC BY 4.0.",
  },
  {
    dato: "Cobertura y pérdida de bosque",
    fuente: "Hansen et al. (2013), Global Forest Change v1.13",
    atribucion: "University of Maryland. CC BY 4.0.",
  },
  {
    dato: "Altura del dosel",
    fuente: "ETH Global Canopy Height 2020 (Lang et al., 2023)",
    atribucion: "ETH Zürich. CC BY 4.0.",
  },
  {
    dato: "Modelo de propagación",
    fuente: "ELMFIRE 2025.0212 (Lautenberger)",
    atribucion: "Eclipse Public License 2.0.",
  },
  {
    dato: "Mapas base",
    fuente: "OpenStreetMap; Esri World Imagery",
    atribucion: "© OpenStreetMap contributors. Teselas © Esri — Esri, Maxar, Earthstar Geographics.",
  },
];

export default async function DocumentacionPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const { tab } = await searchParams;
  const session = await auth.api.getSession({ headers: await headers() });
  return (
    <div className="flex min-h-screen flex-col">
      <ClientHeader active="documentacion" isAdmin={session?.user.role === "admin"} />
      <main className="mx-auto w-full max-w-4xl px-4 py-6 text-sm leading-relaxed sm:py-10">
        <h1 className="text-2xl font-semibold">Documentación</h1>
        <Tabs defaultValue={tab === "limites" || tab === "fuentes" ? tab : "introduccion"} className="mt-5">
          <TabsList className="grid h-auto w-full grid-cols-3">
            <TabsTrigger value="introduccion" className="h-full whitespace-normal px-2 text-xs sm:text-sm">
              Introducción
            </TabsTrigger>
            <TabsTrigger value="limites" className="h-full whitespace-normal px-2 text-xs sm:text-sm">
              Límites del modelo
            </TabsTrigger>
            <TabsTrigger value="fuentes" className="h-full whitespace-normal px-2 text-xs sm:text-sm">
              Fuentes
            </TabsTrigger>
          </TabsList>

          <TabsContent value="introduccion" className="rounded-xl border bg-card p-5 sm:p-7">
            <p className="text-muted-foreground">
              Ignite Insights es una herramienta experimental de apoyo informativo; sus escenarios no incorporan acciones de combate ni reemplazan protocolos, autoridades, observaciones de campo o criterio profesional. La ausencia de una zona en una simulación no demuestra ausencia de riesgo.
              A alto nivel, Ignite Insights detecta focos con el satélite VIIRS y, para cada uno, simula con ELMFIRE
              cómo podría propagarse hasta 24 h sobre el relieve, la vegetación y el pronóstico del
              tiempo. Es una herramienta académica, desarrollada como tesis de grado: no es un
              sistema oficial de alerta.
            </p>
            <h2 className="mt-7 text-lg font-semibold">Cómo leer el mapa</h2>
            <ul className="mt-3 list-disc space-y-2 pl-5">
              <li><strong>Puntos:</strong> detecciones satelitales de las últimas 24 h.</li>
              <li><strong>Perímetro inicial:</strong> lo que el satélite ya vio quemado; es dato observado, no pronóstico.</li>
              <li><strong>Isócronas:</strong> hasta dónde llegaría el frente en cada hora del pronóstico. La animación las recorre.</li>
              <li><strong>Viento:</strong> el viento pronosticado que usa la simulación, hora por hora.</li>
              <li><strong>3D:</strong> el relieve, que ayuda a ver por qué el fuego sube laderas más rápido.</li>
            </ul>
          </TabsContent>

          <TabsContent value="limites" className="rounded-xl border bg-card p-5 sm:p-7">
            <h2 className="text-lg font-semibold">Límites del modelo</h2>
            <dl className="mt-4 flex flex-col gap-5">
              {LIMITES.map((l) => (
                <div key={l.titulo}>
                  <dt className="font-medium">{l.titulo}</dt>
                  <dd className="mt-1 text-muted-foreground">{l.texto}</dd>
                </div>
              ))}
            </dl>
          </TabsContent>

          <TabsContent value="fuentes" className="rounded-xl border bg-card p-4 sm:p-7">
            <h2 className="text-lg font-semibold">Fuentes</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[36rem] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b">
                    <th className="py-2 pr-3 font-medium">Dato</th>
                    <th className="py-2 pr-3 font-medium">Fuente</th>
                    <th className="py-2 font-medium">Atribución y licencia</th>
                  </tr>
                </thead>
                <tbody>
                  {FUENTES.map((f) => (
                    <tr key={f.dato} className="border-b align-top">
                      <td className="py-2 pr-3 font-medium">{f.dato}</td>
                      <td className="py-2 pr-3">{f.fuente}</td>
                      <td className="py-2 text-muted-foreground">{f.atribucion}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
