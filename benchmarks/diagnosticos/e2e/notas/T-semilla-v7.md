# T · Filtro de semilla conexa preparado (D-referencia §5, bug 4)

> 2026-10-19. Sigue a [T-semilla.md](T-semilla.md) §2.2. Implementado y empaquetado sin tocar ningún caso
> -v6. **Corrido el 2026-10-22** (§4).

## 1. Dónde se arma la semilla desde FIRMS

| Lugar | Qué siembra | ¿Conoce la ignición? |
|---|---|---|
| `app/preparation/service.py:320` → `ignition_builder.build_ignition_layer` | La app en tiempo real: todas las detecciones del AOI en la ventana pedida | No |
| `scripts/benchmark.py` `_firms_gfs` → `_mascara` → `build_ignition_layer` | Calibración: la semilla FIRMS de las ventanas n ≥ 1 (sólo la usan las recetas `observacion`) | Sí (`semilla_inicial`) |
| `scripts/benchmark.py` `_pronostico` → `_mascara` → `build_ignition_layer` | P-24: la semilla FIRMS acumulada de cada reinicio | Sí |

`build_ignition_layer` también se llama en `scripts/harness_a.py` y `scripts/pruebas_fisicas.py`, que son
legado y pruebas físicas, no siembras con FIRMS de un caso.

**Punto común:** `app/elmfire/builder/perimeter_reconstruction.connected_to_anchors`. Es una función pura
sobre coordenadas proyectadas, al lado del clustering que ya usa la reconstrucción. Toma las
componentes de enlace simple con saltos de ≤ `link_m` que contienen alguna detección a ≤ `anchor_m`
(5000 m por defecto) de un punto de ignición. No toca `phi.tif` ni el namelist: la semilla sigue
siendo el mismo campo ±1, construido igual, sólo que con menos puntos. Consulté la skill `elmfire`;
nada de la interfaz cambia.

- El benchmark la llama desde `benchmark._semilla_conexa`, que usan `_firms_gfs` y `_pronostico` antes
  de `_mascara`. Sólo filtra la semilla. Las referencias (`vistas_horas`, `ref_firms_horas`, cicatriz)
  y `alcance` siguen con todas las detecciones, así que el puntaje es comparable con v6.
- La app **no la llama todavía**. `run_preparation` no tiene punto de ignición: simula todos los
  incendios del AOI, y ahí un incendio vecino no es un error. Cuando la app permita elegir un incendio
  objetivo, el filtro es una línea antes de `build_ignition_layer`.
- La opción del caso es `semilla_inicial.filtro_conexo_m` (el salto, en metros). Exige `tipo` `punto` o
  `puntos`. Con `tipo: firms` falla, porque no hay ancla.
- Test: `tests/test_semilla_conexa.py` (la función de la app y el helper del benchmark).

## 2. Caso `cholila-2015/pronostico-v7`

Es v6 más `"filtro_conexo_m": 3000`. Se empaquetó offline, porque `_pronostico` sólo lee el almacén
local: estáticos, clima y FIRMS del caso base. Tardó 26 min y no bajó nada. Verificación contra v6 y
contra `T2_semilla_filtros.csv` (variante `conexo_3000`):

| Ventana | Archivos distintos de v6 | Detecciones usadas | Semilla v6 → v7 (ha) | Sacado = T2 (a) |
|---|---|---:|---:|---|
| 0-2 | ninguno | todas (0, 1, 4) | igual | sí (0) |
| 3 | `phi.tif`, `ref_firms.tif` | 24 / 26 | 493 → 416 | sí (77) |
| 4 | ídem | 225 / 345 | 11.398 → 7.564 | sí (3.834) |
| 5 | ídem | 346 / 508 | 12.742 → 8.699 | sí (4.043) |
| 6 | ídem | 380 / 552 | 13.780 → 9.616 | sí (4.164) |
| 7 | ídem | 445 / 642 | 15.257 → 10.972 | sí (4.285) |

- La semilla v7 está contenida en la de v6 en todas las ventanas.
- `ref_firms.tif` cambia porque es "detecciones nuevas fuera de la semilla". Sólo entra en el recall
  FIRMS, no en el Dice contra la cicatriz.
- Las ventanas 0-2 son idénticas byte a byte (paquete y clima), así que **alcanzan 5 corridas**.

## 3. Corrida (no ejecutada)

Receta `lw-100-obs-001` sin cambios, con un ELMFIRE por vez (`correr` corre las ventanas en serie).

```bash
# 1. Las ventanas 0-2 de v7 son las de v6: se copian del manifiesto, tras verificar el paquete
uv run python -c "
from app.validation import cadena, definiciones as d
v6, v7 = (d.Caso.cargar(f'cholila-2015/pronostico-{v}') for v in ('v6', 'v7'))
r = d.Receta.cargar('lw-100-obs-001')
p6, p7 = v6.paquete(), v7.paquete()
assert p6['comunes'] == p7['comunes'] and p6['ventanas'][:3] == p7['ventanas'][:3]
assert v6.ventanas[:3] == v7.ventanas[:3]
cadena._escribir_manifiesto(v7, r, d.cargar_manifiesto(v6.id, r.id)['ventanas'][:3])"

# 2. Las 5 ventanas que cambian (3-7)
make dev-simulation        # o: docker compose up -d elmfire-runner
uv run python scripts/benchmark.py correr cholila-2015/pronostico-v7 lw-100-obs-001

# 3. P-24 con Cholila v7 en lugar de v6
uv run python scripts/benchmark.py pronostico lw-100-obs-001 \
  los-alerces-2023/pronostico-v6 epuyen-2025/pronostico-v6 los-alerces-2024/pronostico-v6 \
  puerto-patriada-2026/pronostico-v6 los-alerces-2016/pronostico-v6 cholila-2015/pronostico-v7
```

Si no se quiere reusar el manifiesto de v6, se omite el paso 1 y `correr` hace las 8 ventanas. Las 3
primeras reproducen v6.

**Lo esperado** según la aproximación de T-semilla §2.3 (sin anillo, como el `pronostico.puntuar`
actual):

- Dice de Cholila ≈ 0,078 a 12 h y ≈ 0,33 a 24 h (hoy 0,070 / 0,262).
- Sesgo medio de Cholila a 24 h de 3,66 a ≈ 2,1.
- Las medianas entre incendios no se mueven: +0,096 / +0,131 contra la cadena.

La aproximación no ve que el frente legítimo llegue en 12-24 h a lo que se sacó. En Cholila eso está a
más de 2 km, así que el error esperado es chico.

## 4. Resultado (2026-10-22)

Se corrieron los pasos 1-3 de §3. Los `assert` del paso 1 pasaron, y además se verificó que las
ventanas 3-7 difieren de v6. Fueron 5 corridas en serie, sin errores. Tabla completa en
`data/benchmark/p24/tabla-pronostico-v7.md`.

Cholila, media de los reinicios k ≥ 1:

| | Dice 12 h | Dice 24 h | Sesgo medio 24 h |
|---|---:|---:|---:|
| v6 | 0,070 | 0,262 | 3,66 |
| v7 | **0,078** | **0,327** | **2,12** |
| Aproximación de T-semilla §2.3 | 0,078 | 0,327 | 2,12 |

- La corrida exacta coincide con la aproximación al tercer decimal: el frente legítimo no llega a lo
  que se sacó.
- A 24 h, lo que más sube son los reinicios con la semilla más recortada: k = 4 (0,269 → 0,419),
  k = 6 (0,236 → 0,368) y k = 7 (0,296 → 0,454). k = 5 sigue en ≈ 0,02.
- Las filas de los otros 5 incendios son idénticas a `tabla-pronostico-v6.md`. Las medianas entre
  incendios no cambian (+0,096 / +0,131 contra la cadena), salvo la de la persistencia a 12 h, que va
  de +0,060 a +0,063.

Bug 4 cerrado: el filtro corrige Cholila y nada más.

**Adoptado (2026-10-22).** P-24 pasa a `*/pronostico-v7` en los 6 incendios. Los otros 5 casos v7 son
v6 + `filtro_conexo_m`. Se empaquetaron offline y quedaron idénticos a v6 en todas las ventanas
(verificado con `assert`), así que se copió el manifiesto de v6 sin correr ELMFIRE. La puntuación con
los 6 casos v7 reproduce la tabla de arriba. La referencia (C) de [T-truncado.md](T-truncado.md) es un cambio
independiente. El usuario decidió no adoptarla (2026-10-23), porque obligaría a renumerar todo
modelo-v0 para ganar +0,001, y queda como límite declarado en `PENDING_PARAMETERS.md` §3.
