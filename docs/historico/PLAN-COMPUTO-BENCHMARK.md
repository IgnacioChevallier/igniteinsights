# Cómputo del benchmark: RAM y paralelismo

> **Histórico.** La cola descrita acá terminó y el hallazgo de la grilla alta fue corregido.
> No usar este plan como lista de pendientes vigente.
>
> Relevamiento del 29-sep-2026, rama `feat/auditoria-fisica`. Pregunta: cómo correr el
> benchmark (`scripts/benchmark.py correr`) sin agotar la RAM de la Mac y si conviene
> paralelizarlo, en local, en Railway o en una VM gratuita o barata.

## 1. Resumen

1. **El cuello es la RAM, no la CPU.** ELMFIRE corre con `mpirun -n 1` (un núcleo de 8) y cada
   trabajo necesita unos 2 GB en la VM de Docker más unos 2 GB en el host para prepararlo.
   El consumo se puede **predecir** a partir del paquete (§3).
2. **El volumen de trabajo es chico.** Una receta sobre los siete casos de calibración v4 tarda
   ~16 min en serie, y la cola pendiente (30 pares caso × receta) ~1,2 h. Paralelizar vale la
   pena para barridos grandes (una grilla de 20 recetas son ~5,5 h), no para la cola de hoy.
3. **Recomendación, en orden:**
   - **A. Local con control de admisión por RAM** (costo cero, ~2× más rápido): un consumidor
     único que lance 2 o 3 corridas a la vez sólo si su RAM estimada entra en el presupuesto.
     Hay que arreglar antes una carrera del almacén (§6.1).
   - **B. Clima en una grilla más gruesa**: es la opción de más impacto. ELMFIRE 2025.0212 ya
     la soporta. Divide por ~9 (a 90 m) la RAM, el disco y la transferencia del clima. Pero
     cambia los insumos: es una decisión de tesis y hace falta un protocolo nuevo (§5).
   - **C. Una VM x86 por horas para barridos grandes**, con la *misma imagen* del runner
     (§6.2): primero los créditos de GCP ($300 por 90 días), si no Hetzner (32 GB por
     ~€0,05/h). Corre el harness completo allá, no sólo el runner.
   - **No conviene Railway para el benchmark** tal como está (§4.3), ni Oracle Always Free,
     GitHub Actions o Colab (§4.4 a §4.6). Railway sigue sirviendo para la app.
4. **Hallazgo lateral, confirmado:** ELMFIRE 2025.0212 acota la *fila* de la grilla de clima
   con la cantidad de *columnas*; con grillas más altas que anchas, la franja norte lee el clima
   de otra fila. En la calibración v4 el efecto medido es despreciable; en la app y en
   `ventanas-firms`, no. Detalle en §7 y en `docs/resultados/AUDITORIA-FISICA.md` (hallazgo 5).

## 2. Diagnóstico medido

**Máquina:** MacBook Intel x86_64, 8 núcleos y 16 GB. Docker Desktop tiene una VM de 7,75 GB
donde viven el runner, la API, la base y el frontend (en reposo, ~0,4 GB entre todos).

**Cómo se reparte una corrida** (`cadena.correr`, ventana por ventana, en serie):

| Fase | Dónde corre | RAM pico medida (Cholila 2015, 2,3 M celdas, 25 bandas) | Tiempo por ventana |
|---|---|---|---|
| `_preparar` (perillas, humedad, `wd`, namelist) | host (`uv run`) | ~2,0 GB RSS | ~30 s |
| `_ejecutar` → ELMFIRE | VM de Docker (runner) | ~2,1 GiB | ~60 s |

Las fases se alternan: con una sola corrida nunca coinciden los dos picos. Muestreado con
`docker stats` y `ps` cada 3 s, sobre una corrida real de la cola.

**Tiempo por receta en los protocolos v4** (mediana de los manifiestos, suma de ventanas):

| Caso | Min/receta |
|---|---|
| cholila-2015/calibracion-era5-v4 | 6,8 |
| puerto-patriada-2026/calibracion-v4 | 3,6 |
| epuyen-2025/calibracion-v4 | 2,3 |
| los-alerces-2024/calibracion-v4 | 1,4 |
| los-alerces-2023/calibracion-v4 | 1,1 |
| las-golondrinas-2021/calibracion-v4 | 0,6 |
| los-alerces-2016/calibracion-era5-v4 | 0,4 |
| **Una receta sobre los siete** | **~16** |

En toda la historia del repo: 397 iteraciones y 22 h de corrida acumulada.

**Qué agotaba la RAM.** Juntar en el mismo momento dos o más de estas cosas:
- una corrida de ELMFIRE (~2 GB en la VM);
- su preparación (~2 GB en el host);
- empaquetados en paralelo (`cola_emp*.sh`, en el host);
- la VM de Docker (7,75 GB reservados);
- el resto de la Mac (IDE, navegador, agentes).

Con 16 GB el margen real para trabajo en el host es de unos 4 GB. En la VM, dos ELMFIRE
grandes (Cholila y Patriada, ~2 GB cada uno) más la base entran; tres empiezan a rozar el
límite, y ahí el kernel mata a ELMFIRE con la señal 9.

**Insumos por ventana: ~1 GB.** Cholila tiene 2,3 M celdas × 25 bandas × 5 variables de clima
× 4 bytes = 1,16 GB, que es justo lo medido. El clima a 30 m es casi todo el peso de cada
ventana y explica que el almacén (`data/benchmark/objetos`) ocupe 202 GB. Sólo los paquetes
v4 suman 38 GB.

## 3. Dónde gasta RAM ELMFIRE (fuente 2025.0212, dentro de la imagen del runner)

`elmfire_init.f90:188-221` reserva cada variable de clima como
`WX_NCOLS × WX_NROWS × WX_NBANDS × 4 bytes`, en ventanas MPI compartidas. Son ocho
(`WS`, `WD`, `M1`, `M10`, `M100`, `MLH`, `MLW`, `MFOL`), más `ERC` e `IGNFAC` si están activas.
O sea:

    RAM_ELMFIRE ≈ 32 B × celdas_clima × bandas  +  ~180 B × celdas_combustible

Con Cholila: 32 × 2,32 M × 25 = 1,73 GiB de clima, más ~0,4 GiB del resto, da 2,1 GiB. Es lo
medido. **El clima es más del 80 % de la RAM de ELMFIRE**, y es la parte que se puede achicar
(§5). La fórmula sirve también para el control de admisión (§4.1): se calcula leyendo sólo
el encabezado de `ws.tif` y `dem.tif` del paquete, sin correr nada.

## 4. Opciones evaluadas

| Opción | Costo | RAM útil | Paralelo real | Esfuerzo | Veredicto |
|---|---|---|---|---|---|
| A. Local + admisión por RAM | $0 | ~6 GB VM / ~4 GB host | 2–3 | bajo | **hacer ya** |
| B. Clima en grilla gruesa | $0 | ÷9 por trabajo | 6–10 local | medio + decisión de tesis | **evaluar** |
| C. VM x86 por horas (GCP trial / Hetzner) | $0 con créditos, o ~€0,05/h | 32 GB+ | 10–14 | medio | **para barridos grandes** |
| D. Railway (runner remoto) | por uso, bajo | hasta 48 GB (Hobby) | sí | alto | no para el benchmark |
| E. Oracle Always Free | $0 | 12 GB, ARM | 3–4 | medio | no (ARM, capacidad) |
| F. GitHub Actions | $0 / 2.000 min | 8 GB privado, 16 GB público | 20 jobs | alto | no (datos, 14 GB de disco) |
| G. Google Colab | $0 | ~12 GB | 1 | alto | no |

### 4.1 A. Local con control de admisión

Hoy `data/benchmark/cola_run2.sh` corre de a uno. La versión mínima es reemplazarlo por un
consumidor en Python (stdlib: `subprocess`, sin dependencias nuevas) que:

1. lea `trabajos.txt` / `trabajos.hechos` igual que hoy;
2. estime la RAM de cada trabajo con la fórmula de §3, leyendo el paquete del caso;
3. lance un `benchmark.py correr` más **sólo si** la suma de lo que está corriendo más lo
   estimado entra en el presupuesto: ~5,5 GiB de VM y ~4 GB de host, con dos corridas como tope
   inicial;
4. marque un trabajo como hecho **sólo si** el manifiesto quedó completo. Hoy una corrida
   fallida (OOM o disco lleno) se marca hecha igual, así que un corte hay que detectarlo a
   mano. Esto cubre el "si falla que no sea un problema": `correr` ya es reanudable por
   ventana; lo que falta es reintentar (una vez, en solitario) en vez de darlo por hecho.

Por qué no hacen falta más cambios:
- **Runner:** ya admite corridas concurrentes: `/simulate` usa `asyncio.to_thread`.
- **Directorios de trabajo:** son por (caso, receta) (`TRABAJO/caso/receta/vN`), así que dos
  corridas no se pisan.
- **Manifiestos:** son por (caso, receta).
- **Registro de las colas:** el aprendizaje de siempre sigue valiendo. Un solo consumidor
  de larga vida; esperar marcadores o archivos, nunca `pgrep`; al matar la cola, matar también
  a sus hijos `benchmark.py correr`.

**Ganancia esperada:** ~2× (dos corridas; la CPU sobra). Una receta sobre los siete pasa de
~16 a ~8–9 min. Hay dos prerrequisitos, en §6.1.

Palanca complementaria: subir la VM de Docker de 7,75 a ~9 GB permite 3 ELMFIRE chicos a la
vez. Pero le quita margen al host, que también prepara, así que conviene sólo junto con B.

### 4.2 B. Clima en una grilla más gruesa

ELMFIRE 2025.0212 lee el clima en **su propia grilla** y la mapea a la de combustible:
- `MAP_FINE_TO_COARSE(WS, ASP, …)` en `elmfire.f90:248`: por defecto, a la celda de clima que
  contiene a cada celda de combustible;
- `WX_BILINEAR_INTERPOLATION`, que vale `.FALSE.` por defecto (`elmfire_namelists.f90:621`),
  interpola en forma bilineal.

Es un mecanismo del fuente, no un keyword nuevo. Detalle en §5.

### 4.3 D. Railway

Precio por uso: $10 por GB·mes de RAM y $20 por vCPU·mes, facturados por minuto; egreso
$0,05/GB. Una hora de barrido con 8 GB y 4 vCPU cuesta ~$0,22, así que el problema no es la
plata. Es la forma del trabajo:

- **Datos:** cada ventana sube ~1 GB de insumos desde casa (el modo
  `elmfire_runner_transfer_files`). Railway exige que el cuerpo de un request termine de
  subirse en **5 minutos** (~27 Mbit/s sostenidos) y corta las conexiones HTTP de más de 15
  min. Además, `/simulate` es síncrono: sin datos durante 5 min, se corta.
- **Réplicas:** el protocolo es de tres requests (`PUT /files`, `POST /simulate`,
  `GET /files`) y el balanceo entre réplicas no es pegajoso: con más de una réplica, el
  `POST` puede caer en otra que no tiene los archivos.
- **Volumen:** en Hobby el volumen es de 5 GB y no entran los 38 GB de paquetes v4. En Pro
  sí (hasta 1 TB, $0,15/GB·mes, unos $6/mes por 40 GB).

Para que Railway sirviera habría que correr **el harness completo** como un worker con volumen
(Pro), subir los paquetes una vez y lanzar corridas por la red privada. Es el mismo trabajo
que la opción C, con menos control (sin `ssh`, límites de proxy, un volumen por servicio). Con
B aplicado, la transferencia baja a decenas de MB por ventana y Railway como runner remoto
pasa a ser razonable. Hasta entonces, Railway queda para la app: una simulación a la vez,
pedida desde el dashboard.

*No pude ver el proyecto: el MCP de Railway está conectado a una cuenta sin proyectos. Si el
plan es Pro, vale lo del volumen de 1 TB; si es Hobby, no entra.*

### 4.4 C. VM x86 por horas

Es la opción buena para barridos grandes. Se levanta, se corre el barrido y se borra.

| Proveedor | Qué da | Condición |
|---|---|---|
| **Google Cloud, Free Trial** | $300 por 90 días, cualquier tipo de máquina sin GPU | cuenta nueva; al final se detiene, no cobra |
| **AWS, Free Plan** | $100 + hasta $100 más, 6 meses | cuenta nueva (desde jul-2025); al agotarse, cierra la cuenta |
| **Azure for Students** | $100 por 12 meses, sin tarjeta | estudiante universitario full-time |
| **Hetzner Cloud** | CX53: 16 vCPU / 32 GB, €0,047/h (€29,49/mes) desde el 15-jun-2026; CX43 16 GB, €0,026/h | pago; facturación por hora |

Con 32 GB entran ~12 corridas como las de hoy, o muchas más con B. Un barrido de 20 recetas
(~5,5 h en serie) baja a ~30 min más la puesta en marcha: con Hetzner, menos de €1.

**Cómo, para que sea reproducible:**
- **Correr el harness completo en la VM**, no sólo el runner: `docker compose` con el runner,
  más `uv run scripts/benchmark.py` y el consumidor de A con un presupuesto mayor.
- **Llevar los datos una vez:** los objetos de los paquetes v4 (38 GB), `benchmarks/` (git) y
  `datasets/` (4 GB) con `rsync`. A 20 Mbit/s de subida son ~4,5 h; a 100 Mbit/s, ~1 h. La
  alternativa es empaquetar en la VM: las descargas de GFS y ERA5 van mucho más rápido desde
  un datacenter.
- **Traer de vuelta** `benchmarks/iteraciones/` (manifiestos) y los objetos de *salidas*
  (chicos). Los objetos de *insumos* (~1 GB por ventana) son la mayor parte de lo que crece el
  almacén. O se traen (lento), o se deja un disco persistente o bucket en la nube y se marca
  la procedencia. Decidirlo antes del primer barrido.
- **La misma imagen del runner.** Ver §6.2.

### 4.5 E. Oracle Cloud Always Free

Hoy son 1.500 OCPU·h y 9.000 GB·h por mes, o sea **2 OCPU y 12 GB** continuos (antes era 4 y
24), con 200 GB de disco. Descartado:
- sólo es gratis en **ARM** (Ampere A1), con un binario distinto al de x86 (§6.2);
- da menos que la Mac;
- Oracle reclama las instancias ociosas (7 días con CPU, red y RAM por debajo del 20 %), y
  crear A1 falla a menudo por falta de capacidad.

### 4.6 F. GitHub Actions y G. Colab

- **GitHub Actions.** En repos privados (este lo es): 2 vCPU, 8 GB y 2.000 min/mes. En
  públicos: 4 vCPU y 16 GB gratis, con matrices de hasta 20 jobs. Pero cada runner tiene
  14 GB de disco y habría que bajarle los paquetes de algún lado en cada job. Sólo tiene
  sentido con B aplicado y con el repo público, que es decisión tuya.
- **Colab** (`colab-mcp` está instalado): ~12 GB, sesiones que se cortan, sin Docker. Habría
  que compilar ELMFIRE en cada sesión. No sirve para algo que se tiene que poder reproducir.

## 5. B en detalle: clima a 90–150 m

**Qué ganás.** La RAM de clima escala con las celdas de clima:

| Grilla del clima | Celdas (Cholila) | RAM ELMFIRE | Insumos por ventana |
|---|---|---|---|
| 30 m (hoy) | 2,32 M | ~2,1 GiB | ~1,2 GB |
| 90 m | 0,26 M | ~0,6 GiB | ~130 MB |
| 150 m | 0,09 M | ~0,45 GiB | ~50 MB |

A 90 m entran 6–8 corridas en la VM local, el almacén crece ~9× más lento y la transferencia
remota deja de ser el cuello (Railway y Actions pasan a ser viables). La preparación en el
host también baja, porque procesa las mismas bandas.

**Qué perdés.** GFS y ERA5 son de 0,25° (~25 km), así que a 30 m el clima ya es una
interpolación y agruparlo a 90 m no pierde información de la fuente. **Pero** hay capas del
repo que sí tienen detalle a escala de terreno:
- el viento del atlas de WindNinja (`atlas_u`/`atlas_v`);
- la humedad que depende del terreno (`app/validation/humedad.py`).

Agruparlas a 90 m suaviza canalizaciones de viento en valles angostos. Además, el mapeo por
defecto es de celda contenedora: el clima queda en bloques de 3×3.

**Cómo decidirlo.**
1. Crear un protocolo nuevo (`-v5`, clima a 90 m) para los siete casos de calibración.
2. Correr `base-001` y la mejor receta.
3. Comparar con `comparar` contra el v4, en Dice y en TOA.

Si la diferencia está dentro del ruido entre recetas, se adopta; si no, se descarta. Es
**decisión de tesis**: cambia lo que recibe ELMFIRE.

**Trampas del fuente, si se hace:**
- No activar `WX_BILINEAR_INTERPOLATION`. `GET_BILINEAR_INTERPOLATE_COEFFS`
  (`elmfire_subs.f90`) calcula `J2 = MAX(MIN(J2 + 1, NROW_WX), 1)` con `J2` sin inicializar;
  debería ser `J1 + 1`.
- La grilla gruesa tiene que cubrir la misma extensión y arrancar en la misma esquina que la
  de combustible.
- Ver §7: el acotamiento de filas también aplica acá.

## 6. Invariantes que no se pueden romper al paralelizar

### 6.1 Prerrequisitos para correr en paralelo en local

1. **Carrera en `almacen.guardar`.** Dos procesos que guardan el mismo objeto a la vez (es
   probable: las capas estáticas del caso son idénticas entre recetas) usan el mismo temporal
   `<sha>.tmp`. El primero lo deja en `0o444`; el segundo falla con `PermissionError` al
   copiar sobre él, o peor, lo pisa a medio escribir. Arreglo de una línea: un temporal único
   por proceso (`tempfile.mkstemp(dir=destino.parent)`) antes del `replace`.
2. **`docker restart igniteinsights-api-1` en los casos `puerto-*`** (`cola_run2.sh:17`).
   Hoy no lastima a nadie, pero con corridas concurrentes conviene entender por qué está y
   sacarlo si ya no hace falta.
3. **Probar la concurrencia de MPI en el mismo contenedor.** Cada ELMFIRE reserva ventanas
   compartidas (`MPI_WIN_ALLOCATE_SHARED`). Correr dos casos chicos a la vez y comparar su TOA
   con el de las corridas en serie (`verificar`).

### 6.2 Reproducibilidad entre máquinas

ELMFIRE se compila con `-O3 -march=native` (`Makefile_elmfire:31`). Una imagen construida en
otra CPU genera otro binario, y el TOA puede diferir en los últimos bits. Entonces `verificar`
("idéntico byte a byte") podría fallar para corridas hechas en la VM remota, sin que haya un
error. Para evitarlo:
- **No reconstruir la imagen en la VM remota.** Publicar la imagen local (`docker push` a
  GHCR, privado) y hacer `pull` allá. Un binario hecho en la Mac Intel usa instrucciones (hasta
  AVX2) que cualquier servidor x86 moderno tiene.
- **Nada de ARM** (Oracle A1, Hetzner CAX, Graviton): otro binario, otros resultados.
- **Registrar en el manifiesto** el digest de la imagen del runner y la CPU (`uname -m` y el
  modelo). Hoy se registra `elmfire` (la versión) y `git`, pero no el binario.
- **Primera corrida remota = `verificar`** de dos iteraciones v4 ya hechas en local. Si da
  idéntico, la VM queda habilitada.

## 7. Hallazgo lateral: filas de clima acotadas por columnas (confirmado)

Pasó a `docs/resultados/AUDITORIA-FISICA.md`, hallazgo 5, con la prueba `pruebas_fisicas.py grilla` y la
medición sobre las 238 iteraciones de los cinco casos afectados. En resumen:
- **Confirmado con ELMFIRE real.** Un fuego en la franja norte con viento de 20 mph avanza 0 m
  (lee la fila en calma), contra 879 m con el clima rellenado al este.
- **Calibración v4: el efecto es despreciable.** El GFS o ERA5 casi no cambia en 4 km
  (|Δws| ≤ 0,12 mph) y el fuego casi no entra en la franja.
- **Pesa en la app** (franja de ~20 km en las grillas del AOI), **en `ventanas-firms`** (la mitad
  del fuego simulado cae en la franja) y en las recetas con atlas o `altura`.
- **Arreglo:** rellenar las columnas del clima en `write_namelist`. Todavía no se aplicó: es un
  protocolo nuevo y la cola v4 está corriendo.

## 8. Plan

1. **Hecho:** §7 confirmado. Falta decidir cuándo se aplica el arreglo (protocolo nuevo).
2. **Local (A):** arreglar la carrera de `almacen.guardar` (§6.1.1), escribir el consumidor
   con admisión por RAM y reintento, y probar la concurrencia con `verificar` (§6.1.3).
   Arrancar con 2 corridas.
3. **Registro:** sumar al manifiesto el digest de la imagen y la CPU (§6.2).
4. **Decisión de tesis (B):** un protocolo `-v5` con clima a 90 m, comparado contra v4. Si pasa,
   se adopta, y el paralelismo local sube a 6–8.
5. **Sólo si hay un barrido grande (> ~3 h en serie):** una VM x86 por horas (C), con la imagen
   publicada, un `verificar` inicial y la regla de qué objetos vuelven. Arrancar por los
   créditos de GCP.

## Fuentes

- Fuente de ELMFIRE 2025.0212 dentro de la imagen del runner (`/opt/elmfire/build/source`):
  `elmfire_init.f90:188-221`, `elmfire.f90:246-248`, `elmfire_subs.f90:276-303` y
  `elmfire_subs.f90` (`GET_BILINEAR_INTERPOLATE_COEFFS`, `WX_*_FROM_ANALYSIS_*`),
  `elmfire_namelists.f90:621`, `build/linux/Makefile_elmfire:31`.
- [Oracle: Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [GitHub: GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
  y [cambios de precio 2026](https://github.com/resources/insights/2026-pricing-changes-for-github-actions)
- [Railway: planes y precios](https://docs.railway.com/reference/pricing/plans) y
  [límites de red pública](https://docs.railway.com/networking/public-networking/specs-and-limits)
- [Google Cloud: Free Trial](https://docs.cloud.google.com/free/docs/free-cloud-features)
- [AWS Free Tier 2026](https://infratally.com/articles/aws-free-tier-2026/)
- [Azure for Students](https://azure.microsoft.com/en-us/free/students)
- [Hetzner: ajuste de precios del 15-jun-2026](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
