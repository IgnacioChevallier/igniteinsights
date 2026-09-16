# Visualización animada — progresión del fuego y campo de viento

> **ARCHIVADO el 2026-09-15: implementado.** El encabezado decía "planificado" cuando la
> animación ya existía (`frontend/components/fire-animation-controls.tsx`, la progresión en
> `fire-map.tsx`) y el viento también (`frontend/lib/wind-particles`, el campo en
> `map-panel.tsx` y el endpoint de viento por banda horaria). Se conserva como registro de
> las decisiones de diseño.
> Referencia visual: partículas de viento de Windy.com

## Objetivo

Dos cosas separadas, con costos muy distintos:

1. **Progresión del fuego**: en vez de isócronas estáticas superpuestas, un bucle de ~10 s que
   colorea el avance hora a hora y se repite.
2. **Campo de viento**: flechas sobre el mapa que indican dirección y cuya longitud codifica
   velocidad, animadas al estilo Windy.

**La respuesta corta a "¿sería muy difícil?": la primera es fácil y no toca el backend. La
segunda tiene tres niveles y el más ambicioso es un proyecto en sí mismo.**

---

# Parte 1 · Progresión del fuego

## Por qué es barato

Las isócronas **ya traen el tiempo de llegada por feature**. `gdal_contour -a arrival_s` en el
microservicio escribe `arrival_s` en cada contorno, e `isochrone_converter` deriva
`arrival_hours` (`app/postprocessing/isochrone_converter.py:38-58`). El GeoJSON que hoy se
dibuja de una vez ya contiene toda la información temporal.

El mapa es **MapLibre GL 4.7** usado directamente (`frontend/components/fire-map.tsx:4`), con
las isócronas en una fuente GeoJSON. MapLibre filtra por expresión sobre propiedades del
feature, así que animar es mover un umbral:

```js
map.setFilter(FILL_LAYER, ["<=", ["get", "arrival_hours"], t]);
```

**No hace falta ningún cambio de backend, ni endpoint nuevo, ni volver a correr nada.** Es un
reloj y un filtro.

## Paso a paso

### A1 · Reloj de animación

Hook `useFireClock` en `frontend/`:

- Estado: `t` en horas simuladas, `playing`, `speed`.
- `requestAnimationFrame` con delta real, no contador de frames — si el navegador tironea, el
  tiempo simulado no se deforma.
- Mapeo: **10 s reales = horizonte completo de la simulación**, configurable. Con horizonte de
  12 h son 1,2 h simuladas por segundo.
- Al llegar al final, pausa breve (~1 s) y reinicio. El corte seco confunde sobre dónde
  termina.

### A2 · Capas

Tres capas sobre la misma fuente, para que el frente se lea:

| Capa | Filtro | Rol |
|---|---|---|
| Quemado | `arrival_hours <= t` | Relleno acumulado, opacidad baja |
| Frente activo | `t - Δ < arrival_hours <= t` | Borde brillante: dónde avanza *ahora* |
| Pendiente | `arrival_hours > t` | Oculta, o contorno tenue como "sombra" del resultado final |

`Δ` es un paso de isócrona (`DTDUMP`). El frente activo es lo que da sensación de avance.

Rampa de color sobre `arrival_hours` para que el interior conserve la lectura temporal:
```js
["interpolate", ["linear"], ["get", "arrival_hours"], 0, colorInicio, horizonte, colorFin]
```

### A3 · Controles

- Play/pausa, y **scrubber** para arrastrar a una hora concreta. El bucle automático es lindo,
  pero para analizar hace falta parar en un instante.
- Etiqueta de hora simulada y, si hay `ignition_datetime`, la marca temporal real.
- Velocidad: 0,5× / 1× / 2×.

### A4 · Interacción con el perímetro de ignición

El audit (§1) advierte que **el 84 % de lo que la corrida reporta como quemado es la semilla
FIRMS**. Hoy se dibuja sin distinción, y el mapa aparenta una predicción mucho mejor de la que
es.

La animación lo arregla sola si se hace bien: el perímetro de ignición se dibuja **en t=0, con
estilo propio y etiqueta "perímetro FIRMS observado"**, y sólo lo que aparece después es
predicción. Es honestidad visual gratis, y responde al hallazgo #2 del audit.

### A5 · Casos borde

- **Features sin `arrival_s`.** El converter deja `arrival_s = None` a propósito en lugar de
  adivinar. Decidir: excluirlas de la animación o mostrarlas siempre. Recomendado excluirlas y
  contarlas en un aviso.
- **Isócronas vacías.** Mostrar el perímetro de ignición y un mensaje, no un mapa en blanco.
- **`prefers-reduced-motion`.** Respetarlo: arrancar pausado en el estado final.
- **Playground.** Un caso base de 5,5 h con la misma animación es más didáctico que el mapa
  estático. Sale gratis: es el mismo componente.

**Esfuerzo estimado: bajo.** Frontend puro, un hook y tres capas.

---

# Parte 2 · Campo de viento

## Qué hay disponible

`ws.tif` y `wd.tif` están en el directorio de inputs, **multibanda: una banda por paso de
`DT_METEOROLOGY`** (arreglado en el segundo pase del audit, §11b). O sea que ya existe
velocidad y dirección por hora sobre la grilla del dominio. Nadie las expone todavía.

Unidades a verificar antes de dibujar nada: `wd` es **la dirección de donde viene el viento**
en grados desde el norte, convención meteorológica. Una flecha que apunta hacia donde sopla
necesita `wd + 180`. Es el error clásico y hay que fijarlo con un test.

## Los tres niveles

| Nivel | Qué se ve | Costo | Veredicto |
|---|---|---|---|
| **1 · Flechas estáticas** | Grilla de flechas rotadas por dirección, longitud por velocidad | Bajo | Punto de partida |
| **2 · Flechas que derivan** | Las flechas avanzan siguiendo el campo y reaparecen | Medio | **Recomendado** — es lo que se pidió |
| **3 · Trazas de partículas WebGL** | Estelas continuas como Windy | Alto | Sólo si el nivel 2 no alcanza |

El nivel 3 es lo que hace Windy de verdad: una capa personalizada con shaders que avanza
miles de partículas contra una textura de viento y acumula estelas en un framebuffer. En
MapLibre es una `CustomLayerInterface` con GLSL propio. **Es un proyecto en sí mismo y no
aporta nada a la tesis** que el nivel 2 no dé.

## Paso a paso

### B1 · Endpoint de viento

```
GET /api/v1/simulations/{id}/wind?hour=N&stride=M
```

Devuelve un `FeatureCollection` de puntos con `ws` y `wd` por punto, submuestreado cada
`stride` celdas.

- Reusar el patrón de lectura de `app/postprocessing/raster_overlay.py`.
- Reproyectar de EPSG:32719 a EPSG:4326 para el mapa.
- `stride` por defecto tal que salgan del orden de **20×20 a 40×40 puntos**. Sobre 2463×3148
  celdas eso es un stride de ~80-120. Una flecha por celda son millones de features: inútil
  visualmente e imposible de renderizar.
- Incluir en la respuesta el rango de `ws` del recorte, para escalar la longitud sin un
  segundo viaje.

### B2 · Nivel 1 — flechas estáticas

1. Generar el ícono de flecha en un canvas y registrarlo con `map.addImage()`. Evita agregar
   un sprite al build.
2. Capa `symbol` con `icon-rotate: ["get", "wd_to"]` e `icon-size` interpolado sobre `ws`.
3. `icon-rotation-alignment: "map"` para que rote con el mapa, no con la pantalla.
4. Color por velocidad, con la misma rampa que use la leyenda.

Con esto ya se cumple *"mayor longitud, mayor velocidad, indicando dirección"*. Lo que falta
es el movimiento.

### B3 · Nivel 2 — flechas que derivan

1. Sembrar N partículas en posiciones aleatorias dentro del recorte visible (N ≈ 300-600).
2. Cada frame: interpolar el viento en la posición de cada partícula (bilineal sobre la grilla
   del endpoint), avanzarla `v · dt · escala`, y reducir su vida.
3. Cuando una partícula muere o sale del recorte, resembrarla en una posición aleatoria.
   **Vidas escalonadas al sembrar**, si no todas desaparecen a la vez y se ve un parpadeo.
4. Actualizar la fuente GeoJSON con `setData()` una vez por frame.
5. Ejecutar a **~20-30 fps, no 60**. El viento cambia despacio; el costo se reduce a la mitad
   o menos y no se nota.

Presupuesto de rendimiento a medir: `setData()` con ~500 puntos por frame. MapLibre lo
soporta, pero hay que medirlo antes de dar por buena la cifra, y en un notebook, no en una
máquina de escritorio.

Un factor de escala del desplazamiento visible por configuración: la velocidad *real* del
viento en pantalla es demasiado lenta o demasiado rápida según el zoom. Es un parámetro de
calibración visual, no físico, y hay que dejarlo declarado como tal.

### B4 · Acoplamiento con el reloj del fuego

El viento es **por hora**, y la animación del fuego corre en horas simuladas. Deben compartir
el mismo reloj: al avanzar el fuego a la hora 5, el campo de viento pasa a la banda 5.

Eso es lo que hace la visualización explicativa en vez de decorativa: se ve el frente
alargarse en la dirección en que las flechas ya estaban apuntando.

Interpolar el campo entre horas para que no salte. Interpolación lineal de las **componentes
u y v**, nunca de `wd` directamente: promediar 350° y 10° da 180°, exactamente el viento
opuesto. Es un error silencioso y hay que fijarlo con un test.

### B5 · Leyenda y honestidad

- Escala de velocidad con unidades explícitas. Verificar si ELMFIRE espera mph (el tutorial
  usa mph) y decidir qué se muestra al usuario.
- Aclarar que es **viento del pronóstico GFS a 10 m interpolado a la grilla**, no observación,
  y que ELMFIRE aplica reducción a media llama internamente vía `adj` y la cobertura de copa.
  La flecha en pantalla no es el viento que empuja la llama.

---

## Orden recomendado

1. **A1-A3** — progresión del fuego. Esfuerzo bajo, cero backend, es el mayor salto visual.
2. **A4** — separar el perímetro de ignición. Corrige un problema real de honestidad que ya
   está anotado en el audit.
3. **B1-B2** — endpoint de viento y flechas estáticas. Útil por sí solo.
4. **B3-B4** — deriva y acople al reloj.
5. **B5** — leyenda y aclaraciones.

Los pasos 1 y 2 se pueden hacer hoy. El 3 en adelante necesita el endpoint.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| `wd` dibujado 180° al revés | Test explícito de la convención: viento del norte apunta hacia el sur |
| Interpolar `wd` entre horas cruzando el 0/360 | Interpolar u y v, nunca el ángulo. Test con 350°→10° |
| `setData()` cada frame degrada el mapa | Medir con ~500 partículas a 20 fps en un equipo modesto antes de fijar N |
| La animación tapa el análisis | Scrubber y pausa desde el primer día; el bucle no puede ser el único modo |
| Se lee el viento en pantalla como el que empuja la llama | Aclaración explícita en la leyenda (B5) |

## Fuera de alcance

- Trazas de partículas WebGL (nivel 3).
- Exportar la animación a video o GIF.
- Viento en 3D o en altura: sólo tenemos 10 m.

## Fuentes

- `app/postprocessing/isochrone_converter.py` — `arrival_s` / `arrival_hours` por feature
- `frontend/components/fire-map.tsx` — MapLibre GL 4.7, fuentes GeoJSON existentes
- `docs/historico/SIMULATION_AUDIT.md` §1 (84 % del área dibujada es la semilla FIRMS), §11b
- ELMFIRE 2025.0212, `tutorials/01-constant-wind/01-run.sh` — unidades de `ws` en mph
- MapLibre GL JS: expresiones de filtro, `addImage`, `CustomLayerInterface`
