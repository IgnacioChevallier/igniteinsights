# Ignición antes de la primera pasada VIIRS

> Estado: **fuera de alcance** (2026-10-12). Límite intrínseco del dominio, no de modelo-v0.
> Evidencia: `docs/resultados/DIA-1-PROPUESTA.md` §7.3; `RIESGOS_Y_SUPOSICIONES.md` §2.

## El límite

La app arma la ignición (`phi.tif`) con el perímetro reconstruido de FIRMS
(`app/elmfire/builder/ignition_builder.py`). Antes de la primera pasada VIIRS sobre un incendio
nuevo no hay perímetro observado. El pronóstico recién tiene sentido desde ahí. En los seis
incendios de calibración, esa primera pasada llegó entre 0,1 y 5,8 h después de la ignición.

En esas horas está casi todo el "día 1 explosivo". En Epuyén 2025, a las 4,5 h ya habían ardido
640–1.120 ha (cicatriz dNBR a menos de medio píxel o de un píxel VIIRS de las detecciones). El
modelo, arrancando de la ignición, quemó 9 ha. Desde la primera pasada, el protocolo P-24
pronostica las 24 h siguientes con un sesgo de 1,0–2,7 en cuatro de seis incendios.

**Lo que la tesis afirma:** pronóstico a 12–24 h desde la última pasada VIIRS. **Lo que no:** un
pronóstico desde que se declara el incendio.

## Por qué otros insumos no lo resuelven

Otro insumo permitiría **saber antes dónde está** el incendio, pero no **pronosticar mejor su fase
explosiva**. Arrancar desde una ignición puntual con hora conocida es exactamente la ventana 0 de
modelo-v0, y es ahí donde ELMFIRE 2025.0212 sub-propaga 6–21×: copa bajo dosel que el acople Van
Wagner + Rothermel no enciende (`DIA-1-PROPUESTA.md` §7.4). Un insumo de detección más temprano
sólo achica el tiempo sin perímetro.

## Insumos identificados, por si se retoma

| Insumo | Qué aporta | Por qué no ahora |
|---|---|---|
| GOES-Este ABI, producto FDC (detección de fuego) | Cobertura de Sudamérica cada 10 min | Píxel de 2 km en el nadir, más grande a 42° S: no ve incendios chicos ni da perímetro. Sirve como alerta y hora de inicio, no como `phi` |
| VIIRS NOAA-21 en FIRMS | Más detecciones en la misma API que ya se usa | Pasa cerca de las mismas horas que SNPP y NOAA-20: no achica de forma apreciable el hueco de 2–6 h |
| MODIS y Sentinel-3 SLSTR | Otras órbitas | Píxel de 1 km; MODIS está en retiro |
| Sentinel-2 y Landsat | Perímetro de 10–30 m | Revisita de días: no sirven para las primeras horas |
| Partes oficiales y reportes (SPMF, SNMF, 911) | Hora y lugar de la ignición | Ya se usan para la semilla del benchmark (`semilla_inicial` de cada caso). Llevan a la ventana 0, que es el caso que falla |
| Vuelos infrarrojos o cámaras de vigilancia | Perímetro temprano y preciso | No hay una fuente sistemática en el área de estudio |

## Qué haría falta para reabrirlo

1. Un modelo que reproduzca la fase explosiva desde una ignición puntual (copa con viento abierto,
   pavesas). Con ELMFIRE 2025.0212 fijo, no está disponible (`DIA-1-PROPUESTA.md` §7.6).
2. Sólo entonces, una fuente de detección temprana sistemática. GOES FDC es la candidata natural.
