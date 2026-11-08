# AC · La semilla conexa en la app operativa

> 2026-10-31. Sigue a [T-semilla-v7](T-semilla-v7.md) y a la decisión del usuario del mismo día
> (Parte 2, punto c). §1 se registró antes de calcular nada. Se conocía el código de las dos reglas,
> no su resultado sobre los casos.

## 0. Problema

ESTADO §6.3 y PENDING §1 dicen que la app en tiempo real todavía no aplica la semilla conexa de P-24,
porque no tiene punto de ignición. Eso vale para esta rama, pero no para `main`. Desde `b2ea414`
(2026-10-26), `main:app/operativo/servicio.py` agrupa las detecciones con `agrupar`: componentes
conexas por enlace simple, con saltos de hasta 3.000 m (`RADIO_GRUPO_M`, comentado como «el
`filtro_conexo_m` de los casos pronostico-v7») y como mucho 24 h entre las dos detecciones de cada
salto (`VENTANA_GRUPO_H`). No usa ancla. Cada ventana se siembra con las detecciones del grupo hasta
la pasada, y sólo con las de los últimos 7 días (`HISTORIA_DIAS`).

El benchmark (`pronostico-v7`) usa `perimeter_reconstruction.connected_to_anchors`. El salto es el
mismo, 3.000 m, pero no tiene límite de tiempo y se ancla en las detecciones a ≤ 5.000 m del punto
de ignición. La pregunta es si las dos reglas eligen las mismas detecciones.

## 1. Diseño registrado (antes de calcular)

**Casos:** los seis de P-24 de calibración, `*/pronostico-v7`: Cholila 2015, Alerces 2016, Alerces
2023, Epuyén 2025, Alerces 2024 y Patriada 2026. El conjunto de prueba no entra.

**Entrada común:** el `firms.csv` del paquete de cada caso, que es la caja del caso. Se usa la misma
entrada para las dos reglas, así que sólo cambia la regla. La app ve todo el AOI, y eso puede sumar
detecciones de afuera de la caja que este chequeo no ve.

**En cada reinicio k ≥ 1, con inicio `t_k`:**

- **B (benchmark):** `connected_to_anchors` sobre las detecciones con `t ≤ t_k`: salto de 3.000 m y
  ancla de 5.000 m en el punto de ignición del caso.
- **A (app):** el `agrupar` de `main`, tomado del código en `81637c3`, sin copiarlo a mano. Se
  aplica sobre las detecciones con `t_k − 7 d < t ≤ t_k`. El incendio es el grupo con más
  detecciones en común con B, que es el que el usuario elegiría en el mapa.

**Métricas por reinicio:**

- cuántas detecciones hay sólo en A y cuántas sólo en B;
- el área de `reconstruct_burn_polygon` de cada conjunto, que es la reconstrucción de la semilla de
  las dos, y el Jaccard entre los dos polígonos.

**Qué se concluye (fijado antes):**

| Resultado | Conclusión |
|---|---|
| A = B en todos los reinicios | **La app de `main` ya aplica la semilla conexa.** ESTADO §6.3 y PENDING §1 se corrigen y el punto se cierra |
| A ≠ B en algún reinicio, pero Jaccard de los polígonos ≥ 0,95 en todos | **Equivalente a efectos de P-24.** Mismo cierre, con la diferencia declarada |
| Jaccard < 0,95 en algún reinicio | **No equivalente.** Se informa el caso, el reinicio y la causa (corte de 24 h, ventana de 7 días o falta de ancla). La diferencia queda declarada en PENDING §1, y anclar el grupo en su primera detección queda como decisión del autor |

El 0,95 es una convención, como el 0,02 de Z. Variantes de semilla de ese orden no movieron el Dice
de P-24 más de ±0,003 ([U](U-reconstruccion-semilla.md)). No sale de estos casos.

No se corre ELMFIRE. No se cambia `main`, `modelo-v0` ni ninguna receta.

## 2. Resultado (2026-10-31)

`scripts/diagnostico_semilla_app.py`, con `agrupar` leído de `main` en `81637c3`. Tabla por reinicio
en `benchmarks/diagnosticos/e2e/datos/AC-semilla-app.json`.

- **A = B en 33 de los 34 reinicios**: las mismas detecciones y el mismo polígono.
- La excepción es **Cholila k7** (2015-02-20 06:17). B tiene 445 detecciones; A tiene 444. Falta
  una detección de esa misma pasada: sus 8 vecinas a ≤ 3 km son todas de 35 h antes o más, así que
  el corte de 24 h de `agrupar` la deja afuera. Área de la semilla: 10.972 ha contra 10.928 ha,
  **Jaccard 0,996**.
- La ventana de 7 días no saca nada: ningún reinicio cae a más de 7 días de la ignición.

Por §1: **equivalente a efectos de P-24.** La app de `main` ya aplica la semilla conexa sin punto de
ignición: el grupo cumple el papel del ancla. La diferencia queda declarada: el corte de 24 h puede
dejar afuera una detección aislada que llega después de un hueco de observación. En la app, esa
detección abre un «incendio» aparte en la lista, en lugar de sumarse a la semilla.

Lo que el chequeo no ve: las detecciones de fuera de la caja del caso, que la app sí ve en el AOI,
y el cambio de ID de un incendio cuando su primera detección sale de la ventana de 7 días. Este
último es un efecto del producto, no de la semilla.

No se corrió ELMFIRE. No cambió nada en `main`, en `modelo-v0` ni en ninguna receta.
