# P-24 con el pronóstico GFS disponible

Fecha de corte: 2026-10-23.

## Pregunta

Los casos `pronostico-v7` validan P-24 con análisis GFS encadenados de ciclos posteriores al
inicio de cada ventana. Eso separa el error del modelo de fuego del error meteorológico, pero es
un *hindcast*: no representa lo que una persona habría podido ver en ese momento.

`pronostico-gfs-v7` repite cada ventana con el último ciclo GFS que ya estaba publicado cuando
FIRMS hacía visible la pasada VIIRS. Semilla, estáticos, parámetros, referencias y receta
`lw-100-obs-001` quedan congelados. Sólo cambia la meteorología.

El archivo GFS 0,25° comienza en 2021. Por eso la comparación alcanza cuatro de los seis casos:
Los Alerces 2023, Los Alerces 2024, Epuyén 2025 y Puerto Patriada 2026. Cholila 2015 y Los
Alerces 2016 no tienen un pronóstico GFS contemporáneo recuperable por este camino.

## Resultado

Dice medio del crecimiento para los reinicios `k >= 1`:

| Incendio | 12 h hindcast | 12 h pronóstico | Δ | 24 h hindcast | 24 h pronóstico | Δ |
|---|---:|---:|---:|---:|---:|---:|
| Epuyén 2025 | 0,1223 | 0,1230 | +0,0008 | 0,1889 | 0,1917 | +0,0028 |
| Los Alerces 2023 | 0,2387 | 0,2382 | −0,0005 | 0,3235 | 0,3216 | −0,0019 |
| Los Alerces 2024 | 0,3415 | 0,3400 | −0,0015 | 0,4427 | 0,4427 | −0,0000 |
| Puerto Patriada 2026 | 0,1486 | 0,1466 | −0,0020 | 0,2084 | 0,2067 | −0,0017 |

En estos cuatro casos el cambio absoluto del Dice medio no supera 0,003. El resultado principal
de P-24 tampoco cambia:

- a 12 h, mediana de `ΔDice = +0,117` contra la cadena y mejora en 4 de 4 incendios;
- a 24 h, mediana de `ΔDice = +0,153` contra la cadena y mejora en 3 de 4 incendios;
- contra persistencia, mejora en 4 de 4 a ambos horizontes.

## Interpretación y límite

Para estos eventos y ventanas, sustituir el análisis encadenado por el pronóstico que existía en
ese momento casi no altera la habilidad espacial medida. Esto elimina el riesgo de que la
ventaja observada de P-24 dependa de información meteorológica futura en los cuatro incendios
con archivo disponible.

No demuestra que el error meteorológico sea despreciable en general: el conjunto es pequeño,
excluye los dos eventos anteriores a 2021 y GFS sigue sin resolver fenómenos locales como el
viento observado en Las Golondrinas. El producto operativo usa siempre el pronóstico disponible,
y la vista cliente declara ese límite.

## Reproducción

```bash
uv run python scripts/benchmark.py pronostico lw-100-obs-001 \
  epuyen-2025/pronostico-gfs-v7 \
  los-alerces-2023/pronostico-gfs-v7 \
  los-alerces-2024/pronostico-gfs-v7 \
  puerto-patriada-2026/pronostico-gfs-v7
```

Los detalles por ventana quedan en `benchmarks/iteraciones/*/pronostico-gfs-v7/` y los
resúmenes agregados en `benchmarks/diagnosticos/pronostico-gfs-v7-*.json`.
