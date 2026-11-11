# Validación del modelo

## Pregunta

¿Cómo evaluar el modelo de forma reproducible, sin fuga temporal y sin ajustar con el conjunto de
prueba?

## Banco de pruebas

El banco de pruebas separa tres objetos inmutables:

- **caso:** incendio, ventanas, semilla y referencias identificadas por hash;
- **receta:** combustible y parámetros declarados;
- **iteración:** aplicación de una receta a un caso.

Los artefactos se almacenan por SHA-256. Una receta con iteraciones ejecutadas no se modifica: se
crea otra con un padre explícito. El ejecutor rechaza cambios no declarados y mapas posteriores al
incendio, salvo controles rotulados como fuga temporal.

## Datos y partición

- Calibración: siete incendios; Las Golondrinas se conserva como caso límite.
- Prueba: cuatro incendios, nunca usados para seleccionar receta o parámetros.
- Referencia espacial: cicatriz dNBR truncada al horizonte mediante detecciones VIIRS.
- Referencia temporal: incrementos FIRMS por ventana.
- Horizonte máximo: 120 h, o antes cuando el incendio deja de crecer o se mezcla con otro.

La semilla se excluye de la puntuación. Las zonas sin observación válida o atribuibles a otro
incendio no cuentan como acierto ni error.

## Métrica principal

Dice contra la cicatriz en la última ventana, acompañado por sesgo de área. Un Dice alto con un
sesgo extremo no se considera un resultado válido. Las definiciones completas están en
[`metricas.md`](metricas.md).

## Resultado vigente

La receta `lw-100-001` fue promovida como `modelo-v0`:

| Conjunto | Dice medio | Dice mediano | Lectura |
|---|---:|---:|---|
| Calibración | 0,439 | 0,501 | sin alarmas salvo el caso límite |
| Validación cruzada | 0,416 | 0,496 | estable dentro de calibración |
| Prueba | 0,191 | 0,167 | transferencia limitada; informativo |

La comparación controlada de combustibles mantiene CCS-BAP en `modelo-v0`; el detalle está en
[`../combustibles/resultados.md`](../combustibles/resultados.md).

## Alcance

El banco de pruebas demuestra reproducibilidad y permite comparar decisiones dentro de este conjunto.
No prueba validez universal, exactitud operativa horaria ni desempeño sobre incendios con
supresión representada.

## Reproducción

```bash
uv run python scripts/benchmark.py modelo modelo-v0
uv run python scripts/benchmark.py verificar <iteracion>
```

Definiciones: `benchmarks/modelos/modelo-v0.json`. Casos, recetas e iteraciones viven bajo
`benchmarks/` y son la fuente canónica de configuración y procedencia.

