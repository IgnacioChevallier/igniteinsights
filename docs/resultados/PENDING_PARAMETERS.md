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
| Humedad viva leñosa, LW | 100 % | Calibrada; 110 % es el umbral húmedo de grandes incendios, no el valor de un día extremo. Un LW por especie (`MLW_FILENAME`) aleja la ROS de lo observado (`docs/resultados/diagnostico-e2e/notas/V-humedad-viva.md`) |
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
| Semilla FIRMS de P-24 (`pronostico-v7`) | Detecciones conectadas a la ignición: saltos ≤ 3.000 m, ancla ≤ 5.000 m | Saca otros incendios de la caja; sólo cambia Cholila (`docs/resultados/diagnostico-e2e/notas/T-semilla-v7.md`). La app en tiempo real todavía no la aplica, porque no tiene punto de ignición |

## 2. Abierto, pero no bloquea el modelo

| Tema | Estado | Qué permitiría reabrirlo |
|---|---|---|
| CBH de bosque nativo | Valores indirectos de literatura | Inventario regional de estructura vertical |
| Rugosidad regional | Valor convencional, no medido en el AOI | Medición o producto regional independiente |

Estos puntos son incertidumbres de entrada. No justifican otra búsqueda de perillas con los
mismos once incendios.

## 3. Límites declarados

- **Día 1, residuo después de la primera pasada VIIRS:** el primer reinicio de P-24 queda 2–4,5×
  por debajo en Patriada y Alerces 2024, compatible con copa que ELMFIRE 2025.0212 no enciende bajo
  dosel (`docs/resultados/DIA-1-PROPUESTA.md` §7.3–7.6). Es el límite del día 1 dentro del alcance:
  el pronóstico operativo arranca en la última pasada (protocolo P-24).
- **Supresión:** la regla disponible de ELMFIRE fue implementada y probada; empeora la
  calibración y no contiene los incendios que más sobre-propagan.
- **Las Golondrinas:** la ráfaga nocturna no está representada en GFS; es un caso límite y no
  participa del gate de sesgo.
- **Transferencia:** el conjunto de prueba tiene cuatro incendios, Dice 0,191/0,167 y dos
  alarmas. Con P-24, la mediana es 0,084 / 0,145 a 12 / 24 h, y le gana a la cadena en 4 de 4
  (`docs/resultados/diagnostico-e2e/notas/AB-p24-prueba.md`). `modelo-v0` es un baseline productivo
  auditable, no una afirmación de generalización universal.
- **P-24 con reanálisis** en Cholila 2015, Alerces 2016, Epuyén 2019 y Alerces 2015: el GFS de esas
  fechas sólo está archivado cada 3 h, así que corren con ERA5 y no son pronóstico (notas Z y AB).
  No se baja ese archivo (decisión del usuario, 2026-10-31).
- **Reconstrucción del perímetro FIRMS** (cerrado el 2026-10-31, decisión del usuario): no participa
  en la calibración de ignición puntual. En P-24 (`docs/resultados/DIA-1-PROPUESTA.md` §7.3) da
  pronósticos casi iguales a los de arrancar desde la cicatriz real. Sólo la reabre un perímetro
  operativo independiente (vuelo IR, partes).
- **Islas en la referencia truncada:** con `hasta_horizonte`, la cicatriz no vista se excluye, pero
  las islas sin quemar no vistas dentro del perímetro final siguen contando como negativos. Eso da un
  techo de Dice de 0,85 en Patriada y 0,86 en Cholila. Excluirlas (variante C) vale ≤ 0,005 en
  calibración y ≤ 0,01 en P-24, y no cambia la receta ni ninguna conclusión. No se adopta (decisión
  del 2026-10-23); se declara como límite (`docs/resultados/diagnostico-e2e/notas/T-truncado.md`).
- **m10/m100** (cerrado el 2026-10-31): los offsets +2/+5 no tienen fundamento físico, pero el
  benchmark es insensible. No se buscan mediciones.
- **Viento de superficie** (cerrado el 2026-10-31): ERA5 y GFS no resuelven bien los valles. Las
  series de estación pedidas al INTA y a Bosques de Chubut no llegaron y el pedido se canceló; ya
  no reabre ninguna decisión.
- **Pavesas** (`docs/resultados/diagnostico-e2e/notas/Y-pavesas-condicionadas.md`): no se usan ni
  globales ni condicionadas a una regla previa. Sólo las reabre una prueba independiente de la
  regla d1 registrada en Y §4.

## 4. Estado de cierre (2026-10-31)

**Fuera del alcance**

- Las 2–6 h anteriores a la primera pasada VIIRS. La app arranca en la primera detección VIIRS
  (decisión del usuario, 2026-10-31). Ahí está casi todo el déficit del día 1, y sólo aparece porque
  el benchmark de cadena arranca en el punto de ignición reportado.
- El ensamble paramétrico (`docs/out-of-scope/ENSAMBLE-PARAMETRICO.md`).

**Límites declarados (cerrados)**

Los de §3. Se reabren sólo por un bug físico o por evidencia externa nueva. La ingesta histórica de
FIRMS, que figuraba acá, se resolvió el 2026-10-12: la app pide las fuentes SP y las NRT
(`docs/resultados/LO-YA-QUEMADO-PROPUESTA.md` §8).

**Pendiente**

1. La evaluación con usuarios de la capa de acuerdo del ensamble
   (`docs/resultados/PROTOCOLO-EVALUACION-ACUERDO-ENSAMBLE.md`), que hace el autor con personas
   reales.
2. Llevar los resultados al informe (`../informe`), incluida la comparación final de mapas
   (`docs/resultados/COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`).

Abiertos: los dos puntos de §2, que siguen abiertos por decisión del autor (2026-10-31); del
ensamble, CPU/RSS del runner y la latencia (el mínimo operativo de 24/31 se ratificó el 2026-10-31);
y la semilla conexa en la app en tiempo real (§1).

No quedan barridos de receta pendientes con los datos actuales.
