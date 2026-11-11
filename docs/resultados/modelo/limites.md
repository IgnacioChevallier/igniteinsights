# Límites del modelo

Estos límites forman parte de la interpretación del producto; no son tareas pendientes.

| Límite | Evidencia | Consecuencia |
|---|---|---|
| Supresión ausente | en reinicios tardíos el modelo continúa creciendo cuando el incendio real se frena | interpretar la salida como propagación potencial sin combate |
| Primer reinicio P-24 | Patriada y Alerces 2024 quedan 2–4,5× por debajo del crecimiento observado | declarar el déficit; no calibrar una física nueva con dos casos |
| Viento regional | GFS/ERA5 no resuelven valle, ladera ni ráfagas locales; el rumbo tiene un error cercano a 60° | la dirección y forma del frente pueden ser incorrectas |
| Forma casi isotrópica | igualar el área no mejora el Dice | el error no se corrige sólo ajustando velocidad |
| Meteorología histórica | Cholila 2015 y Alerces 2016 no tienen un archivo GFS comparable | sus resultados P-24 con ERA5 son evaluaciones retrospectivas |
| Perímetro FIRMS | resolución de 375 m, humo, nubes y frecuencia orbital | la semilla puede incluir margen o perder crecimiento |
| Combustibles estándar | FBFM40 no fue construido con vegetación patagónica | la correspondencia es una analogía regional, no una medición directa |
| Desfase cartográfico | CCS-BAP es de 2017 y dosel proviene de otras épocas | las quemas recientes requieren LYQ-3 y persiste incertidumbre estructural |
| Humedad uniforme | no hay gradiente altitudinal ni medición por especie y hora | se usa un valor global calibrado dentro de evidencia regional |
| Pavesas y estructuras | no están representadas en `modelo-v0` | eventos de salto o interfaz urbano-rural pueden quedar subestimados |
| Transferencia | Dice de prueba 0,191/0,167 | no generalizar el desempeño de calibración |

## Uso permitido

- Comparar escenarios bajo supuestos explícitos.
- Visualizar propagación potencial desde la última observación.
- Comunicar acuerdo entre miembros meteorológicos.

## Uso no respaldado

- Predecir la cicatriz final de un incendio combatido.
- Interpretar el acuerdo GEFS como probabilidad de quema.
- Afirmar exactitud horaria o utilidad operacional causal.
- Extrapolar las métricas a otros ecosistemas sin validación nueva.

## Qué podría reducir la incertidumbre

Perímetros operativos independientes, registros de supresión, estaciones dentro de los valles,
inventarios locales de combustible y dosel, y nuevos incendios reservados para prueba. Ninguno de
estos insumos está disponible con cobertura suficiente en el cierre actual.

La evidencia detallada se conserva en `benchmarks/diagnosticos/e2e/`.

