# Comparación final de mapas condicionada a modelo-v0

> Protocolo congelado el 2026-10-04, antes de ejecutar las nuevas iteraciones. Ejecutado y
> cerrado el mismo día. Los resultados están en
> `docs/resultados/COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`; el documento v5 permanece como
> antecedente.

## 1. Pregunta

¿Qué cambia al sustituir únicamente el ráster de combustible superficial de modelo-v0 por el de
WorldCover o MapBiomas, manteniendo iguales todos los demás insumos y parámetros?

La comparación mide el **efecto controlado del mapa de combustible dentro de modelo-v0**. No
compara tres pipelines completos ni recalibra cada producto por separado.

## 2. Invariantes

- Casos y ventanas: los once casos congelados en `benchmarks/modelos/modelo-v0.json`.
- Resúmenes principales: diez casos; Las Golondrinas se reporta aparte como límite.
- Receta base: `lw-100-001` — LW 100 %, ADJ 1, semilla por predicción.
- Protocolos: copias v6 con mapas adicionales, identificadas con sufijo `-v6m`.
- Clima, ignición, topografía, dosel, humedad, namelist y referencias: idénticos por hash.
- Único archivo que puede cambiar entre mapas: `fbfm40.tif`.
- Año del mapa: el último publicado anterior al incendio.
- WorldCover sin año anterior: se permite sólo como fuga declarada y se resume aparte.

El dosel permanece igual al de modelo-v0, incluso al sustituir el mapa superficial. Esto aísla
`fbfm40.tif`, pero implica que el CBH/CBD fue construido con la clasificación CCS-BAP. Se declara
como condición del experimento; derivar un dosel distinto para cada producto compararía sistemas
completos y confundiría la atribución al mapa.

## 3. Recetas

- CCS-BAP: `lw-100-001`, la receta promovida.
- WorldCover: receta hija de `lw-100-001`; sólo cambia `combustible.fuente`.
- MapBiomas: receta hija de `lw-100-001`; sólo cambia `combustible.fuente`.

Las recetas comparadoras se crearán al construir los paquetes v6m. No se ajustan LW, ADJ ni
ningún parámetro por mapa.

## 4. Métricas predefinidas

Primaria:

- Dice contra la cicatriz en la última ventana, con sesgo de área al lado.

Secundarias:

- IoU, precisión y recall;
- Dice a área igualada, para separar forma de velocidad;
- Dice y sesgo del día 1 contra el incremento FIRMS;
- TP/FP/FN por grupo de combustible;
- diferencias apareadas por incendio y test de signos exacto.

Se informan por separado:

1. calibración y prueba;
2. incendios 2021+ con WorldCover anterior al fuego;
3. incendios 2015–2019 donde WorldCover tiene fuga temporal;
4. GFS y ERA5, porque período y fuente meteorológica están confundidos.

## 5. Regla de interpretación

- “CCS-BAP supera a WorldCover” exige ventaja consistente en los casos sin fuga temporal, no en
  el agregado contaminado por mapas posteriores al fuego.
- “CCS-BAP supera a MapBiomas” exige una ventaja apareada consistente en Dice y que no desaparezca
  a área igualada.
- Una ventaja exclusiva del día 1 se informa como velocidad temprana, no como mejor forma final.
- Los resultados de prueba no modifican modelo-v0.
- Si el orden v5 no se reproduce, manda el experimento modelo-v0.

## 6. Condición de cierre

La comparación queda cerrada cuando:

1. los paquetes v6m reproducen por hash la iteración CCS-BAP de modelo-v0;
2. las tres recetas completan los once casos;
3. ninguna comparación contiene cambios no declarados fuera de `fbfm40.tif` y la semilla heredada;
4. las tablas se regeneran desde los manifiestos;
5. la conclusión respeta las reglas anteriores.

Las cinco condiciones se cumplieron. Los 11 controles CCS-BAP reprodujeron byte a byte las
salidas de modelo-v0 y las 33 combinaciones quedaron registradas.
