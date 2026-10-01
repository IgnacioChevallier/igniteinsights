# Decisiones pendientes para el director

> Septiembre de 2026. Resume lo que la auditoría física (`AUDITORIA-FISICA.md`) dejó para
> decidir con criterio de dominio: asignaciones del crosswalk, el dosel y dos decisiones de
> método. El detalle y la reproducción de cada número están en ese documento; acá va lo necesario
> para decidir.

## Contexto: qué cambió

La auditoría encontró **cinco errores en la interfaz entre el sistema y ELMFIRE**. Los cinco
estaban en todas las simulaciones anteriores, incluidas las del documento del crosswalk
(`docs/historico/IGN-20B-FINAL-CROSSWALK-CCSBAP.md`) y la calibración de `RESULTADOS-CSS-BAP.md`:

1. El clima quedaba fijo en la primera hora de cada ventana de 24 h: sin ciclo diurno.
2. El frente avanzaba a la mitad de la velocidad que el propio modelo calculaba.
3. La dirección del viento se interpolaba mal entre horas cuando soplaba del sur.
4. En las celdas con cobertura arbórea pero sin altura, el viento no actuaba.
5. En dominios más altos que anchos, la franja norte leía el clima de otra fila.

Los cinco están corregidos y verificados con el modelo real. Con la interfaz corregida:

- **La receta calibrada no necesita el factor de ajuste de velocidad (ADJ):** la única perilla
  que la región pide es la humedad del combustible vivo, en 100 % (antes: 100 % más un ADJ de
  1,15). El ADJ compensaba los errores.
- Sobre los siete incendios de calibración, el Dice medio es **0,381** (mediana 0,451), sin
  incendios con sesgo de área fuera de [0,5×; 2×], salvo el caso límite de Las Golondrinas. Antes
  de la auditoría, el modelo sin calibrar daba 0,312.
- El resultado es mucho menos sensible a errores en el punto y la hora de ignición.

Las decisiones que siguen son las que ahora más mueven el resultado y que no se pueden resolver
calibrando.

## 1. Ñire bajo, lenga achaparrada y arbustal nativo: ¿con dosel o sin dosel?

**Situación.** El crosswalk asigna ñire bajo y lenga achaparrada a SH8, y el arbustal nativo a
SH4: modelos de **matorral abierto**, con el lecho de combustible expuesto al viento. Pero el
dosel (cobertura de Hansen, altura de ETH) les asigna, dentro de las cicatrices, cobertura de
bosque cerrado: mediana de 78 a 91 % y 13 a 18 m. ELMFIRE combina las dos cosas y les aplica la
reducción de viento de un bosque: al combustible le llega el **8 % del viento a 6 m** en lugar
del 46 % que le llegaría a un matorral abierto.

**Cuánto pesa.**
- En Alerces 2024, dos tercios del matorral quemado es ñire bajo, y el 90 % tiene cobertura
  de Hansen de 50 % o más. En Patriada, el 59 % del arbustal nativo quemado también.
- Probando el modelo sin dosel en los combustibles de pastizal y matorral (como hace LANDFIRE),
  el Dice sube en Patriada (+0,10) y Alerces 2024 (+0,06) y baja en Alerces 2016 (−0,12) y
  Alerces 2023 (−0,08). La media no cambia.

**Opciones.**
- **(a) Sin dosel.** Son combustible arbustivo expuesto al viento, como dice el modelo asignado.
  El dosel de Hansen/ETH sobre esas clases se ignora.
- **(b) Con dosel.** Son sotobosque bajo un dosel real. Entonces el modelo de superficie
  apropiado sería de la familia TU (bosque con sotobosque), no SH, y la asignación del
  crosswalk cambia.
- **(c) Depende de la clase:** por ejemplo, ñire bajo sin dosel y lenga achaparrada con dosel,
  según la estructura real.

Hoy el sistema hace (b) en el dosel y (a) en el combustible, que es incoherente.

## 2. La altura de la base de copa

**Situación.** No hay datos de altura de base de copa (CBH) para la región. El sistema la deriva
de la altura y la cobertura del dosel: CBH = altura × (0,20 + 0,30 × cobertura), o sea 5 a 10 m
en los bosques de la zona. Con esas alturas, el fuego de copas prácticamente no se enciende:
menos del 2 % de las celdas con dosel alcanzan la intensidad crítica.

**Cuánto pesa.** Con la base de copa a un cuarto (2 a 3 m), la copa sí se enciende:
- Cholila pasa de 0,255 a **0,528**, y Alerces 2024 de 0,556 a 0,614.
- Alerces 2016 y 2023 se pasan de área, y Epuyén y Patriada no cambian.

Es, por lejos, el insumo que más mueve el resultado entre los que quedan.

**Qué haría falta.** Un valor con fundamento por tipo de bosque: un inventario forestal, la
relación de Cruz, Alexander y Wakimoto (2003) con datos de estructura, o valores de literatura
para lenga, coihue, ciprés y plantaciones de pino. No se calibra: la tesis no fundamenta el
dosel.

## 3. La antigüedad del dosel

La cobertura arbórea es la de Hansen para el año **2000**: 15 a 26 años antes de los incendios
del benchmark (2015–2026). Donde hubo fuegos o cambios en ese intervalo, el sistema ve un bosque
que ya no está.

**Ejemplo.** En El Turbio 2025, el 83 % de la cicatriz figura como bosque cerrado, donde CCS-BAP
2017 ve el rebrote de la cicatriz de 2015 ("Remanente de disturbio reciente").

**Opciones.** Descontar la pérdida posterior con la capa de pérdida anual de Hansen, o usar un
producto de cobertura más reciente. Cualquiera de las dos es un cambio de insumo que requiere
volver a preparar los datos.

## 4. Remanente de disturbio reciente → GS3

El crosswalk asigna el remanente de disturbio a GS3 (pastizal-arbustal), con la regeneración de
ñire post-fuego de la PT-37 como análogo. En El Turbio 2025 el incendio volvió a quemar ese
rebrote diez años después: ardió lento (latente, diez días hasta 2.000 ha, combatido), y el
modelo lo recorre como pastizal-arbustal, con cinco veces el área observada. La asignación
describe bien un disturbio de dos años, pero con un mapa de 2017 envejece.

**A decidir:** ¿con qué modelo pasa el remanente a la clase de su vegetación actual, y a partir
de cuántos años?

## 5. Plantaciones de pino → TL8

Las plantaciones ("Forest") se asignan a TL8, hojarasca de pino. En Epuyén 2025 la ignición cae
en una plantación, y el incendio real ardió en copa desde el principio: 1.120 ha en 6 h. Con TL8
y la base de copa derivada, el modelo queda contenido en la plantación el primer día.

**Cuánto pesa.** En la calibración anterior, modelar las plantaciones como TU5 subía el Dice de
Epuyén de 0,291 a 0,344. Con la interfaz corregida casi no cambia nada: 0,500 → 0,503, y a las
24 h quema 176 ha en vez de 172, contra 1.730 observadas. El efecto anterior venía de que el
frente, a media velocidad, quedaba atrapado más tiempo en la plantación.

**A decidir:** con el modelo de superficie solo no se reproduce el primer día. Lo que decide si
una plantación densa sin podar arde como en Epuyén es su base de copa (punto 2). La asignación
TL8 se puede mantener mientras se resuelve eso.

## 6. El sesgo declarado del arbustal (paso 4 del crosswalk)

El documento del crosswalk declara que SH8, SH4 y GS3 subestiman la propagación "5 a 11 veces"
frente a la quema experimental de la PT-37. Esa cifra salió con el frente a la mitad de
velocidad. Corregida:

| Modelo | Propagación con viento sostenido | Con ráfaga | Llama | Observado |
|---|---|---|---|---|
| SH8 (ñire bajo, lenga achaparrada) | 739 m/h | 1.785 m/h | 3,5–5,6 m | 4.800 m/h, 3–4 m |
| SH4 (arbustal nativo) | 888 m/h | 2.445 m/h | 2,2–3,7 m | |
| GS3 (estepa arbustiva, remanente) | 1.098 m/h | 2.896 m/h | 2,8–4,5 m | |

SH8 sigue por debajo, pero 2,7 a 6,5 veces. **SH4 y GS3, con ráfaga, llegan al 51–60 % de la
propagación observada con la llama medida.** La conclusión "ningún modelo de arbustal reproduce
propagación y llama a la vez" ya no vale tal cual: el sesgo existe, pero es la mitad de grande.

## 7. Dos decisiones de método para validar

**Humedad del combustible vivo en 100 %.** Bianchi y Defossé (2015) midieron 110–220 % en
temporada de fuego y ubican en 110 % el umbral por debajo del cual ocurren los grandes
incendios. El sistema usaba 110 % (el borde húmedo); la calibración elige 100 %, el valor más
seco que no hace sobre-propagar a ningún incendio (el intervalo aceptable es 97–110 %).
¿Es defendible 100 % para días de gran incendio?

**Horizonte de Alerces 2023 en 54 h.** La regla es puntuar hasta que el área detectada por
satélite deja de crecer. En Alerces 2023 eso pasa a las 54 h (1.055 ha a las 54 h, 1.056 a las
72 h), pero se puntuaba a las 72 h para usar ventanas de 24 h. Con el modelo a su velocidad real,
esas 18 h extra lo castigan por fuego que el combate detuvo. Se aplicó la regla tal cual (54 h),
y se reportan las dos cifras.

## Límites que ninguna de estas decisiones resuelve

- **Supresión.** Los incendios combatidos cerca de poblados (El Turbio, Epuyén 2019)
  sobre-propagan 5 a 16 veces. ELMFIRE tiene un módulo de supresión que hoy no se usa.
- **El primer día explosivo.** En cuatro de los siete incendios de calibración el modelo va 8 a
  30 veces por debajo en las primeras 24 h. La copa (punto 2) explica una parte; faltan las
  pavesas y las ráfagas de valle, que el pronóstico de 25 km no resuelve.
- **La dirección del viento de superficie.** El frente real corre en promedio unos 40° más al
  sur que el empuje del viento del pronóstico, en valles que el pronóstico no resuelve.
