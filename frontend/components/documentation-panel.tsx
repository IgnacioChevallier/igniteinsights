import {
  BookOpen,
  CloudSun,
  Flame,
  Layers3,
  MapPinned,
  Mountain,
  Satellite,
  ShieldAlert,
  Trees,
  Wind,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const MAP_GUIDE = [
  {
    icon: MapPinned,
    title: "Partí del perímetro observado",
    description:
      "El contorno gris punteado representa la detección FIRMS usada como entrada en t=0. No es una predicción del modelo.",
  },
  {
    icon: Flame,
    title: "Seguí las isócronas",
    description:
      "Los contornos cálidos muestran la expansión simulada por hora. El frente más claro identifica el avance activo en el instante seleccionado.",
  },
  {
    icon: Wind,
    title: "Leé el tiempo y el viento juntos",
    description:
      "La línea de tiempo permite recorrer la corrida. Las partículas muestran la dirección del viento y el panel indica su velocidad y vigencia.",
  },
  {
    icon: Layers3,
    title: "Compará las capas",
    description:
      "Tiempo de llegada, intensidad y acuerdo del ensamble responden preguntas distintas. Activá una capa por vez y revisá siempre su leyenda.",
  },
];

const LIMITS = [
  "Cada corrida es un escenario condicionado por sus datos de entrada y sus supuestos, no una certeza sobre el comportamiento futuro del incendio.",
  "El GFS tiene una resolución nativa de 0,25°. La interpolación mejora la continuidad visual, pero no incorpora variaciones meteorológicas locales.",
  "Las detecciones satelitales pueden tener latencia y omisiones por nubosidad, humo, horario de pasada o sensibilidad del sensor.",
  "El acuerdo del ensamble expresa la fracción de simulaciones meteorológicas que alcanza cada zona. No es una probabilidad calibrada: muestra propagación potencial y no considera combate ni supresión. Sólo varía la meteorología, por lo que el incendio real puede extenderse fuera de la zona ≥ 0,10.",
  "La simulación no representa tareas de combate, supresión ni cambios del combustible posteriores a la fecha de las capas utilizadas.",
];

const SOURCES = [
  {
    icon: Satellite,
    title: "Focos activos",
    source: "NASA FIRMS, VIIRS NOAA-20",
    detail: "Detecciones satelitales usadas para construir la condición inicial observada.",
  },
  {
    icon: CloudSun,
    title: "Meteorología",
    source: "NOAA Global Forecast System, 0,25°",
    detail: "Viento, temperatura y humedad de la corrida meteorológica seleccionada.",
  },
  {
    icon: Mountain,
    title: "Relieve",
    source: "Copernicus DEM GLO-30",
    detail: "Elevación y derivados topográficos empleados por el modelo de propagación.",
  },
  {
    icon: Trees,
    title: "Combustibles y dosel",
    source: "CCS-BAP, MapBiomas, ESA WorldCover, Hansen GFC y ETH",
    detail: "Cobertura del suelo y estructura de la vegetación transformadas a entradas de ELMFIRE.",
  },
];

export function DocumentationPanel() {
  return (
    <div className="h-full overflow-y-auto bg-muted/30">
      <article className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 md:py-10 lg:px-10">
        <div className="flex items-center gap-2 text-sm font-medium text-orange-700">
          <BookOpen className="h-4 w-4" aria-hidden="true" /> Guía de uso
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Documentación</h1>

        <Tabs defaultValue="introduccion" className="mt-7">
          <TabsList
            aria-label="Contenido de la documentación"
            className="grid h-auto w-full grid-cols-3"
          >
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

          <TabsContent value="introduccion" className="rounded-xl border bg-background p-5 sm:p-7">
            <p className="max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
              Ignite Insights integra detecciones satelitales de focos activos, pronósticos
              meteorológicos, relieve y combustibles para simular escenarios de propagación. El
              mapa ayuda a explorar cuándo y dónde podría avanzar el frente bajo los supuestos de
              cada corrida; no sustituye las observaciones en campo ni las decisiones operativas.
            </p>

            <section className="mt-8">
            <h2 className="text-2xl font-semibold tracking-tight">Cómo leer el mapa</h2>
            <p className="mt-3 max-w-2xl leading-7 text-muted-foreground">
              Empezá por distinguir lo observado de lo simulado y después sumá las capas que
              necesites para responder una pregunta concreta.
            </p>

            <ol className="mt-7 grid gap-x-8 gap-y-7 sm:grid-cols-2">
              {MAP_GUIDE.map((item, index) => (
                <li key={item.title} className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border bg-background text-orange-700 shadow-sm">
                    <item.icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <p className="font-medium">
                      <span className="mr-2 text-sm tabular-nums text-muted-foreground">
                        {index + 1}.
                      </span>
                      {item.title}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
            </section>
          </TabsContent>

          <TabsContent value="limites" className="rounded-xl border bg-background p-5 sm:p-7">
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-6 w-6 text-orange-700" aria-hidden="true" />
              <h2 className="text-2xl font-semibold tracking-tight">Límites del modelo</h2>
            </div>
            <p className="mt-3 max-w-2xl leading-7 text-muted-foreground">
              La lectura responsable del resultado requiere considerar estas condiciones.
            </p>
            <ul className="mt-6 space-y-4">
              {LIMITS.map((limit) => (
                <li key={limit} className="flex gap-3 text-sm leading-6 sm:text-base">
                  <span
                    className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-600"
                    aria-hidden="true"
                  />
                  <span>{limit}</span>
                </li>
              ))}
            </ul>
          </TabsContent>

          <TabsContent value="fuentes" className="rounded-xl border bg-background p-5 sm:p-7">
            <h2 className="text-2xl font-semibold tracking-tight">Fuentes</h2>
            <p className="mt-3 max-w-2xl leading-7 text-muted-foreground">
              Las fuentes dependen de la configuración de cada corrida. Estas son las principales
              familias de datos utilizadas por la aplicación.
            </p>

            <dl className="mt-7 grid gap-4 sm:grid-cols-2">
              {SOURCES.map((item) => (
                <div key={item.title} className="rounded-xl border bg-background p-5 shadow-sm">
                  <div className="flex items-start gap-3">
                    <item.icon
                      className="mt-0.5 h-5 w-5 shrink-0 text-orange-700"
                      aria-hidden="true"
                    />
                    <div>
                      <dt className="font-medium">{item.title}</dt>
                      <dd>
                        <p className="mt-1 text-sm font-medium text-muted-foreground">
                          {item.source}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-muted-foreground">
                          {item.detail}
                        </p>
                      </dd>
                    </div>
                  </div>
                </div>
              ))}
            </dl>
          </TabsContent>
        </Tabs>
      </article>
    </div>
  );
}
