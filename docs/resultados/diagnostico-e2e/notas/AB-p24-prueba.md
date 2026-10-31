# AB · P-24 sobre los 4 casos de prueba

> 2026-10-31. Sigue a [Z](Z-p24-pronostico-gfs.md). §1 se registró antes de empaquetar y de correr
> ELMFIRE: se conocían las cifras de prueba de modelo-v0 (`MODELO-V0.md`) y las de P-24 en
> calibración (Z §4), no ninguna de P-24 sobre prueba.

## 0. Por qué

El 0,191 de prueba de modelo-v0 mide la cadena: 72–120 h desde el punto de ignición reportado y sin
supresión. La app no hace eso. Arranca en la primera detección VIIRS y re-siembra en cada pasada
(P-24; ESTADO §6.1, Día 1 fuera del alcance). P-24 nunca se corrió sobre los cuatro casos de prueba, que
son el holdout del producto. Decisión del usuario (2026-10-31): no se excluye ningún caso.

## 1. Diseño registrado (antes de calcular)

### 1.1 Protocolo

El mismo de la variante P-24 vigente, sin cambios:

- **Reinicios:** `benchmark.py crear-pronostico` sobre el caso de prueba de modelo-v0. Son la
  ventana 0 del caso base (desde la ignición, no se puntúa) y un reinicio de 24 h en cada pasada
  VIIRS SP que deja 24 h dentro del horizonte del base.
- **Semilla:** lo observado por FIRMS hasta el reinicio, acumulado. Con el filtro conexo de v7
  (`filtro_conexo_m` 3000) donde la semilla del caso es un punto: El Turbio, Epuyén 2019 y Alerces
  2015. Puerto Café siembra con `tipo: firms` y el filtro de su caso base (detecciones a ≤ 1 km de la
  cicatriz, `radio_cicatriz_m`), porque el filtro conexo necesita un punto de ignición.
- **Clima:** el de Z donde se puede. El Turbio 2025 y Puerto Café 2025 son GFS, y van con el último
  ciclo publicado en cada reinicio (`pronostico-ciclo-v7`; ciclos verificados en AWS, 337 de 337
  horas). Epuyén 2019 y Alerces 2015 corren con ERA5 en la cadena. Para esas fechas el GFS sólo está
  archivado cada 3 h, en RDA y sin `.idx`, igual que Cholila y Alerces 2016 (Z §2.2). Van con el
  ERA5 del caso base (`pronostico-v7`): es reanálisis, no pronóstico, y se rotula así.
- **Receta:** `lw-100-obs-001`, la de evaluación de P-24 (modelo-v0 re-sembrado con lo observado).
- **Comparador:** la cadena de modelo-v0 (`lw-100-001` sobre el mismo caso base, ya corrida y
  congelada) en las mismas ventanas, y la persistencia.

| Caso | Base | Protocolo P-24 | Reinicios | Clima |
|---|---|---|---:|---|
| El Turbio 2025 | `el-turbio-2025/calibracion-v6` | `pronostico-ciclo-v7` | 8 | GFS, pronóstico |
| Puerto Café 2025 | `puerto-cafe-2025/calibracion-v6s` | `pronostico-ciclo-v7` | 5 | GFS, pronóstico |
| Epuyén 2019 | `epuyen-2019/calibracion-era5-v6` | `pronostico-v7` | 7 | ERA5, reanálisis |
| Alerces 2015 | `los-alerces-2015/calibracion-era5-v6` | `pronostico-v7` | 4 | ERA5, reanálisis |

### 1.2 Métricas

Las de `pronostico.puntuar` y `pronostico.resumir`, sin cambios: Dice del crecimiento contra la
cicatriz ya vista por VIIRS, sin el anillo del reinicio. A 12 y 24 h. Se informa:

- por caso: la media del Dice de los reinicios k ≥ 1 (P-24, cadena, persistencia) y la mediana del
  sesgo de área de esos reinicios;
- entre casos: la mediana del ΔDice P-24 − cadena y en cuántos de los 4 casos gana P-24.

Con n = 4, todo es descriptivo (4 de 4 da p = 0,0625 con la prueba de signos).

### 1.3 Qué se concluye de cada resultado (fijado antes de calcular)

Resultado principal: contra la cadena, a 12 h.

| Resultado | Conclusión |
|---|---|
| Mediana > 0 y gana en ≥ 3 de 4 | **En el holdout, P-24 también mejora a la cadena.** El producto supera al benchmark de la física en casos no usados para nada |
| Gana en 2 de 4 | **Mixto.** Se informa por caso, sin afirmación general sobre prueba |
| Mediana ≤ 0, o gana en ≤ 1 de 4 | **En el holdout, P-24 no mejora a la cadena.** Se informa así, junto al de calibración |

A 24 h se aplica la misma tabla como resultado secundario.

Lo esperado de antemano, para no leerlo después como hallazgo: El Turbio y Epuyén 2019 son los casos
de supresión (RIESGOS §1). Sus reinicios tardíos deberían sobre-propagar (sesgo ≫ 1), como los de
calibración. Puerto Café tiene una fase explosiva que la cadena no reproduce. Si P-24 gana ahí, es por
el reinicio, no por la física.

Sea cual sea el resultado:

- nada se ajusta con esto, modelo-v0 no cambia y no se elige ninguna receta;
- el 0,191 de prueba de la cadena se conserva. En ESTADO van las dos cifras: P-24 como métrica
  principal del producto (propuesta) y la cadena como benchmark de la física.

## 2. Corridas (2026-10-31)

Empaquetado y corrido con `lw-100-obs-001`, un ELMFIRE por vez. La cola esperó 3 min de runner libre
antes de cada caso. 24 reinicios; ELMFIRE tardó 1–8 min por caso.

Controles:

- La ventana 0 de cada caso es la del base. Sólo agrega `vistas_horas.tif`, la referencia por plazo
  de P-24.
- El clima de cada reinicio tiene las bandas que pide `bandas_necesarias`.
- Los ciclos GFS de El Turbio y Puerto Café quedaron en `origen.ciclos`: 00Z o 12Z, f005–f033.

Métricas en `benchmarks/iteraciones/*/{pronostico-ciclo-v7,pronostico-v7}/lw-100-obs-001/pronostico.json`;
resumen en `benchmarks/diagnosticos/pronostico-prueba-lw-100-obs-001.json`; tabla por reinicio en
`data/benchmark/p24/tabla-pronostico-prueba.txt`. No se usó `benchmark.py pronostico` para el
resumen: nombra el archivo por el protocolo del primer caso y habría pisado los diagnósticos v7 de
calibración.

## 3. Resultado

Media por caso de los reinicios k ≥ 1 (Dice del crecimiento) y mediana del sesgo de área de esos
reinicios:

| Caso | Clima | Reinicios | 12 h: P-24 / cadena / persistencia | Sesgo 12 h: P-24 / cadena | 24 h: P-24 / cadena / persistencia | Sesgo 24 h: P-24 / cadena |
|---|---|---:|---|---|---|---|
| El Turbio 2025 | GFS, pronóstico | 8 | 0,085 / 0,000 / 0,123 | 2,13 / 0,29 | 0,144 / 0,020 / 0,129 | 2,54 / 0,43 |
| Puerto Café 2025 | GFS, pronóstico | 5 | 0,084 / 0,000 / 0,041 | 5,47 / 1,60 | 0,226 / 0,000 / 0,111 | 1,87 / 0,27 |
| Epuyén 2019 | ERA5, reanálisis | 7 | 0,073 / 0,036 / 0,068 | 10,8 / 21,0 | 0,112 / 0,081 / 0,142 | 19,4 / 31,5 |
| Alerces 2015 | ERA5, reanálisis | 4 | 0,093 / 0,018 / 0,068 | 1,66 / 0,77 | 0,146 / 0,031 / 0,086 | 4,69 / 1,94 |
| **Mediana** | | | **0,084** / 0,009 | | **0,145** / 0,026 | |

En Epuyén 2019, a 12 h, la persistencia se promedia sobre los reinicios en que existe. Ahí P-24 da
0,085, no 0,073 (igual que en Z, `pronostico.resumir`).

| Plazo | Contra la cadena | Contra la persistencia |
|---|---|---|
| 12 h | **+0,079, gana en 4 de 4** | +0,021, 3 de 4 (pierde El Turbio, −0,038) |
| 24 h | **+0,120, gana en 4 de 4** | +0,038, 3 de 4 (pierde Epuyén 2019, −0,030) |

Por §1.3:

- **12 h: mediana > 0 y gana en 4 de 4. En el holdout, P-24 también mejora a la cadena.**
  Descriptivo, n = 4.
- **24 h: lo mismo** (+0,120, 4 de 4).
- Lo esperado se cumplió. Epuyén 2019 sobre-propaga en todos los reinicios (sesgo mediano 19 a
  24 h): es el caso de supresión. El Turbio se pasa 2–2,5×. P-24 le gana a la cadena ahí porque la
  cadena está en otro lugar (Dice ≤ 0,001 en 7 de 8 reinicios a 24 h), no porque frene el fuego.
- **Puerto Café es donde más gana (+0,226 a 24 h).** El reinicio arranca de lo que la explosión ya
  quemó; la cadena, que no la tuvo, no llega a ese lugar (Dice 0,000 en los 5 reinicios). Es el
  efecto del reinicio, no de la física (§1.3).
- **El nivel absoluto es bajo.** La mediana de P-24 en prueba es 0,084 a 12 h y 0,145 a 24 h. En los
  cuatro incendios GFS de calibración, con el mismo protocolo, es 0,192 y 0,262 (Z §4). La
  diferencia entre calibración y prueba que tenía la cadena (0,439 contra 0,191) sigue en P-24.
- Contra la persistencia, la ventaja de ELMFIRE es chica y no está en los cuatro casos, a diferencia
  de calibración (4 de 4 en los dos plazos).

## 4. Consecuencia

- Se propone en ESTADO §3 que la métrica principal del producto sea P-24: Dice del crecimiento a
  12 y 24 h desde la última pasada, con el pronóstico disponible. La cadena desde la ignición queda
  como benchmark de la física. El 0,191 de prueba se conserva: van las dos.
- modelo-v0 no cambia. Nada de esto elige ni ajusta una receta.
- Epuyén 2019 y Alerces 2015 son reanálisis (ERA5), no pronóstico. El Turbio y Puerto Café son
  pronóstico real.
