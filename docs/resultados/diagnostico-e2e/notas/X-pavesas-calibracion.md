# X · Pavesas fuertes sobre la calibración v6: ¿candidato a modelo-v1?

> 2026-10-23. Sigue a [G §7](G-golondrinas-meteo-observada.md): con el SYNOP observado y pavesas fuertes,
> Las Golondrinas pasa de Dice 0,205 a 0,545. Acá se prueba si esas pavesas sirven como modelo, con la
> misma puerta que cualquier receta. §1 se registró antes de correr.

## 1. Diseño y criterio (registrados antes de correr)

**Receta.** `lw-100-pavx10-001`: es `lw-100-001` con `&SPOTTING`, 10 % de las celdas en copa y 1 % en
superficie lanzan pavesas. Es la variante fuerte del loop L, sin CBH × 0,5, porque v6 ya tiene el CBH de
literatura. Es la misma receta de G §7.2, sin ningún cambio. No se ajusta ningún valor a la vista de
los resultados.

**Casos.** Los 7 de calibración de modelo-v0 (`benchmarks/modelos/modelo-v0.json`): Alerces 2023
(h54), Epuyén 2025, Alerces 2024, Patriada 2026 y Las Golondrinas (GFS); Alerces 2016 y Cholila 2015
(ERA5). Los casos de prueba no se abren salvo que la receta pase la puerta de calibración (§1.3).

**Línea base** (`lw-100-001`, `benchmark.py objetivo calibracion todas` y `validar todas`, antes de
correr):

| | media | mediana | alarmas (sin el caso límite) | fuera de muestra |
|---|---:|---:|---:|---|
| `lw-100-001` | 0,439 | 0,501 | 0 | 0,416 / 0,496 |

Por caso, Dice / sesgo: Alerces 2023 0,528 / 1,86; Epuyén 0,501 / 1,41; Alerces 2024 0,635 / 1,35;
Patriada 0,496 / 0,70; Las Golondrinas 0,012 / 0,02 (límite); Alerces 2016 0,389 / 1,69; Cholila
0,513 / 0,87.

### 1.1 Puerta de calibración (la de la regla de parada y del frente 3)

`lw-100-pavx10-001` pasa sólo si cumple las tres condiciones:
1. Dice medio ≥ 0,459 (+0,02);
2. ninguna alarma de sesgo nueva: sesgo fuera de [0,5, 2] en algún caso que no sea el límite;
3. una validación cruzada (`validar todas`) que no empeore: media fuera de muestra ≥ 0,416.

Si no pasa, las pavesas quedan como limitación declarada y modelo-v0 sigue igual.

### 1.2 La celda de interacción (Las Golondrinas con GFS)

`las-golondrinas-2021/calibracion-v6` es, byte a byte, el control `synop-v6-s0` de G (G §2). Su
corrida con esta receta es la celda que falta para saber si los mecanismos se suman o se necesitan a la
vez:

| | sin pavesas | con pavesas |
|---|---|---|
| GFS | 224 ha, sesgo 0,021 | **esta corrida** |
| SYNOP hasta 03Z | 1.868 ha, sesgo 0,176 | 9.088 ha, sesgo 0,822 |

Lectura fijada:
- con pavesas y GFS, sesgo < 0,05 (×2,5 o menos): **los dos mecanismos son necesarios a la vez**. Las
  pavesas no se encienden sin el viento y el aire seco, y la frase de G «el GFS explica ×10 y las
  pavesas el ×4,7 restante» se corrige;
- sesgo ≥ 0,10: las pavesas aportan solas una parte, y el reparto es en parte aditivo;
- entre 0,05 y 0,10: se informa sin veredicto.

El loop L corrió la variante fuerte con CBH × 0,5 sobre `calibracion-v5` y dio Dice 0,020 y sesgo
0,026. Es otro crosswalk, así que sólo sirve como indicio.

### 1.3 Si pasa la puerta

Se corre la prueba (4 casos), sólo para informar. La promoción a modelo-v1 queda a decisión del
usuario, con el protocolo de `benchmarks/modelos/`.
