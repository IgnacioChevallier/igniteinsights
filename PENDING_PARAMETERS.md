# Registro de decisiones y pendientes del modelo

> Corte: 2026-10-04. Este archivo reemplaza la lista histórica de parámetros sin criterio.
> El estado canónico del research está en `docs/resultados/ESTADO-RESEARCH.md` y el snapshot
> promovido en `benchmarks/modelos/modelo-v0.json`.

La convención vigente es:

- **receta:** configuración experimental aplicada a un caso;
- **iteración:** receta × caso;
- **modelo:** receta y conjunto de evidencia que pasaron el gate productivo.

`modelo-v0` promueve la receta `lw-100-001` sobre los protocolos v6. Los valores resueltos no
se vuelven a calibrar con el conjunto de prueba. Sólo se reabre el modelo por un error físico o
por evidencia externa nueva.

## 1. Congelado en modelo-v0

| Entrada | Valor | Estado y criterio |
|---|---:|---|
| Fuente principal de combustible | CCS-BAP anterior al fuego | Crosswalk final aprobado técnicamente; años 2013/2017 evitan fuga temporal |
| Humedad viva leñosa, LW | 100 % | Calibrada; 110 % es el umbral húmedo de grandes incendios, no el valor de un día extremo |
| ADJ | 1,0 | Sin ajuste; el ADJ anterior compensaba errores de interfaz |
| Humedad viva herbácea, LH | 30 % | Convención de pasto curado de Scott & Burgan |
| Humedad muerta m1 | Nelson sobre GFS/ERA5 | El delta uniforme −6 no tiene soporte en estaciones |
| `dt_s` / `dtmax_s` | 30 / 300 s | Convergencia verificada con el paso a la mitad |
| Rugosidad `z0` | 0,22 m | El ráster por dosel duplica el WAF de ELMFIRE y empeora el objetivo |
| Horizonte Alerces 2023 | 54 h | El área FIRMS deja de crecer; extenderlo mide fuego sin supresión |
| Estepa CCS-BAP | GR2; >1.300 m → NB9 | Decisión del loop L; GR1 queda como sensibilidad no adoptada |
| Remanente de disturbio | SH3 | Representa mejor un rebrote de 6–15 años que GS3 |
| CBH | Por tipo de bosque | Valores de literatura; baja a media confianza salvo pino |
| CBD del pino | 0,16 kg/m³ | Medido en plantaciones patagónicas |
| Pérdida previa Hansen | Sin dosel | Sólo pérdidas anteriores al año del incendio |

## 2. Abierto, pero no bloquea el modelo

| Tema | Estado | Qué permitiría reabrirlo |
|---|---|---|
| m10/m100 | Los offsets +2/+5 no tienen fundamento físico, pero el benchmark es insensible | Serie meteorológica previa y mediciones de humedad de combustibles |
| Viento de superficie | ERA5 y GFS no resuelven bien los valles | Estación cercana a Alerces 2016 o Cholila durante el incendio |
| CBH de bosque nativo | Valores indirectos de literatura | Inventario regional de estructura vertical |
| Reconstrucción de perímetro FIRMS | No participa en la calibración de ignición puntual | Sensibilidad específica para el modo operativo con semilla observada |
| Rugosidad regional | Valor convencional, no medido en el AOI | Medición o producto regional independiente |

Estos puntos son incertidumbres de entrada. No justifican otra búsqueda de perillas con los
mismos once incendios.

## 3. Límites declarados

- **Día 1 explosivo:** faltan ráfagas subhorarias, pavesas o propagación de copa que el clima y
  la configuración actuales no resuelven.
- **Supresión:** la regla disponible de ELMFIRE fue implementada y probada; empeora la
  calibración y no contiene los incendios que más sobre-propagan.
- **Las Golondrinas:** la ráfaga nocturna no está representada en GFS; es un caso límite y no
  participa del gate de sesgo.
- **Transferencia:** el conjunto de prueba tiene cuatro incendios, Dice 0,191/0,167 y dos
  alarmas. `modelo-v0` es un baseline productivo auditable, no una afirmación de generalización
  universal.
- **Datos históricos en la app:** la ingesta FIRMS NRT no reemplaza las fuentes SP necesarias
  para reconstruir incendios antiguos.

## 4. Próximo trabajo

1. Incorporar al texto de tesis la comparación final cerrada en
   `docs/resultados/COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`.
2. Obtener aprobación formal del director para las decisiones de
   `docs/crosswalk/DECISIONES-MODELO-V0.md`.
3. Incorporar viento medido sólo si aparece una fuente independiente adecuada.

No quedan barridos de receta pendientes con los datos actuales.
