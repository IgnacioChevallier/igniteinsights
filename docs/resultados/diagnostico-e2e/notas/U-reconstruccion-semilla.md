# U · Cota sin ELMFIRE de cambiar la reconstrucción de la semilla de P-24 (decisión 2)

> 2026-10-19. Sigue a I, que encontró que el 70 % del crecimiento predicho brota de semilla fuera de la
> cicatriz, y a T, que filtró las detecciones ajenas pero dejó fuera de alcance la regla de
> reconstrucción. Sin ELMFIRE, sólo calibración, sin commit, modelo-v0 intacto.
> Código: `scripts/diagnostico_reconstruccion.py`; test: `tests/test_diagnostico_reconstruccion.py`.
> Datos: `datos/U_*.csv`.

## Diseño (fijado antes de correr)

**Regla de tiempo real, sin la cicatriz.** Las tres variantes parten de las detecciones de la componente
conexa de T, con saltos de 3000 m anclados a ≤ 5 km de la ignición. Esa regla da idéntico al oráculo
de 2000 m y sólo cambia Cholila. Todas mantienen la recursión de `benchmark._pronostico` (previo |
ignición | reconstrucción).

| Variante | Semilla | Qué ataca de T |
|---|---|---|
| `conexa` | La reconstrucción actual (casco cóncavo + buffer de 187,5 m, discos de 375 m en clústeres de < 4) | (a). Es la **referencia** de la comparación |
| `huellas` | La unión de las huellas reales scan × track de cada detección, sin casco | (b) margen y (c) relleno |
| `nucleo_huellas` | El casco sin buffer, unido a las huellas | (b) margen |

**Dos extremos, porque sin ELMFIRE no se sabe cómo crece la semilla chica.** Con la misma física, una
semilla más chica da un TOA más tardío en todas partes. Entonces lo quemado de verdad queda entre:

- `sin_cambio` (pesimista): el frente queda donde estaba, como si la semilla chica llegara al borde
  viejo al instante. Sólo cambia qué se puntúa.
- `voronoi` (optimista): la aproximación de T (`recortar_prediccion`). El crecimiento que brota de
  semilla sacada desaparece.

Las celdas de la variante que caen fuera de la semilla usada (esquinas de huella) se descartan, y se
informan en ha.

**Puntaje.** Es `pronostico.puntuar` sin el anillo, con la semilla de la variante. Por incendio se
toma la media del Dice de P-24 en los reinicios k ≥ 1, y entre incendios la mediana del ΔDice contra
`conexa`. Se informa también contra la cadena y el exceso de flanco + retroceso de I.

**Control.** La variante `actual` (el `phi.tif` guardado) tiene que reproducir +0,096 / +0,131 contra
la cadena.

**Criterios.**

- **Cierre.** Si en el extremo optimista `huellas` y `nucleo_huellas` dan un ΔDice mediano contra
  `conexa` < +0,02 a 12 h y a 24 h, la decisión 2 se cierra: la reconstrucción se mantiene, con el
  filtro conexo de T.
- **Si alguna variante da ≥ +0,02 a algún plazo en el extremo optimista**, se propone, sin correrla
  sin aprobación, la corrida exacta de esa variante. Sería un protocolo `pronostico-v7` (regla de
  semilla en `_pronostico`) con `lw-100-obs-001` tal cual.
  - Criterios de esa corrida: ΔDice mediano ≥ +0,02 contra `conexa` a 12 h y a 24 h, mejora en ≥ 4
    de 6 incendios, ningún incendio peor que −0,02 y P-24 sigue ganando a la cadena en ≥ 5 de 6.
  - Costo: ~34 ventanas, una corrida por vez.

### Agregado 1 (post hoc, después de ver la primera corrida): el extremo `voronoi` no es optimista

El extremo `voronoi` salió peor que `sin_cambio`, porque además del FP borra el crecimiento bueno que
pasa por el margen sacado. Se agregan dos lecturas:

- `oraculo` (techo, usa la cicatriz): de lo que Voronoi saca, sólo lo FP.
- `retraso` (intermedia): lo que brota de un borde sacado llega tarde lo que tarda el frente en
  cruzar lo sacado, a la velocidad mediana del reinicio.

El criterio de cierre se lee sobre las tres (§Resultados).

### Agregado 2 (registrado antes de correrlo): crecer sólo desde el frente activo

Hipótesis, a partir de los resultados de arriba: el exceso de flanco de I no viene del margen de la
semilla sino de que ELMFIRE quema desde **todo** el borde, mientras que el fuego real avanza sólo
desde la parte activa.

- **Variante `frente_activo`.** Es de tiempo real y no usa la cicatriz. La semilla es la usada
  (`phi.tif`). Activo es el borde a ≤ 375 m (un píxel VIIRS) de una detección de la última pasada
  (las ≤ 2 h previas al reinicio, `SEPARACION_PASADAS_H`).
- **Estimación.** Voronoi sobre el borde: se conserva el crecimiento cuyo borde más cercano es activo.
  Es optimista, porque el frente activo también avanza de costado.
- **Comparación.** Contra `actual` (misma semilla y mismo puntaje).
- **Criterio.** Se diseña la implementación exacta si el ΔDice mediano es ≥ +0,02 a 12 h y a 24 h y
  mejora en ≥ 4 de 6 incendios. La implementación sería un anillo no combustible en el perímetro
  inactivo, armado en el empaquetado y no por namelist, y se diseñaría antes de cualquier corrida. Si
  no se cumple, el frente se cierra.

## Resultados

**Control.** `actual` reproduce +0,096 / +0,131 contra la cadena (6/6 y 5/6), y `conexa` reproduce el
T4 de T.

ΔDice mediano entre incendios contra `conexa` (mejoran de 6), 12 h | 24 h:

| Variante | `sin_cambio` | `retraso` | `voronoi` | `oraculo` (techo, usa la cicatriz) |
|---|---|---|---|---|
| `huellas` | +0,001 (3) \| +0,003 (4) | +0,002 (3) \| +0,002 (4) | −0,025 (1) \| −0,064 (1) | +0,074 (6) \| +0,082 (6) |
| `nucleo_huellas` | −0,000 (3) \| +0,002 (5) | +0,000 (3) \| −0,001 (1) | −0,022 (1) \| −0,063 (1) | +0,060 (6) \| +0,073 (6) |

ΔDice mediano contra `actual` (mejoran de 6):

| Variante | 12 h | 24 h |
|---|---|---|
| `frente_activo` (Voronoi sobre el borde) | **+0,026 (5)** | **−0,027 (1)** |

**Lo que se saca es casi todo afuera de la cicatriz, pero es delgado.**

- Sale el 33 % de la semilla con `huellas` y el 16 % con `nucleo_huellas`. De eso, el 84 % y el 94 %
  está fuera de la cicatriz.
- Aun así, la semilla queda un 33–40 % fuera de la cicatriz (contra 42 %). Lo que queda es la huella
  misma del píxel VIIRS, la causa (d) de T, que una regla de tiempo real no puede sacar.
- En Epuyén el margen sacado mide ~120 m. A la velocidad del frente del modelo (45–90 m/h) es un
  retraso de 1,4–2,7 h en ventanas de 12–24 h.
- Por eso las estimaciones físicamente plausibles (`sin_cambio` y `retraso`) quedan en ±0,003. El
  techo de +0,06–0,08 sólo se alcanza borrando con la cicatriz lo que después resulta FP.

**El frente activo funciona a 12 h y no a 24 h.**

- A 12 h, lo que brota del borde inactivo (en mediana, el 64 % del borde) es mayormente FP. El exceso de
  flanco baja de 0,51 a 0,37.
- A 24 h el fuego real también avanza desde ahí, porque los flancos se reactivan, y sacarlo cuesta:
  Alerces 2024 baja de 0,44 a 0,38 y Alerces 2023 de 0,32 a 0,28.

## Veredicto

- **Decisión 2: se cierra.** La reconstrucción de la semilla se mantiene. Sólo queda el filtro conexo de
  3000 m de T para las detecciones ajenas, que es la corrida de 5 ventanas de Cholila que T propuso.
  - El criterio registrado se cumple al pie de la letra (en `voronoi` ninguna variante llega a
    +0,02), pero su premisa (que `voronoi` era optimista) resultó falsa.
  - Leído sobre las estimaciones plausibles el cierre se sostiene: `sin_cambio` y `retraso` dan
    ≤ +0,003.
  - Sólo el techo con la cicatriz supera +0,02, y no es alcanzable en tiempo real.
- **Frente activo: no pasa el criterio registrado** (+0,026 a 12 h, −0,027 a 24 h). No se diseña el
  anillo no combustible.
  - La señal de 12 h es real (5 de 6), pero un pronóstico que gana a 12 h y pierde a 24 h no justifica
    una regla nueva.
  - Si se quisiera explorar, sería con una regla que se apague con el plazo, y eso es una perilla.
- **Qué deja para I.** El 70 % de crecimiento "fuera de la cicatriz" no es un error de reconstrucción
  corregible: es el perímetro inactivo. ELMFIRE quema desde todo el borde y el fuego real avanza desde
  una parte.
  - Ese comportamiento, apagar flancos, es supresión o extinción local, que el modelo no tiene.
  - Queda como límite (la salida "supresión/límite" del frente 2) y no como método.

## Límites

- `retraso` usa una velocidad por reinicio y Voronoi sobre el borde.
- `frente_activo` toma como activo lo que está a un píxel de la última pasada. Una pasada parcial (con
  nubes o en el borde de la franja) marca como inactivo un borde que sí ardía.
- n = 6 incendios correlacionados. Nada de esto reemplaza a ELMFIRE, pero tampoco justifica correrlo.
