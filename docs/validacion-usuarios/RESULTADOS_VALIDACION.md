# Resultados de la validación con usuarios

**Estado:** corte parcial con 3 sesiones. Se actualizará al sumar entrevistas.
**Fecha del análisis:** 6 de noviembre de 2026.
**Instrumento:** [PROTOCOLO_VALIDACION_USUARIOS.md](PROTOCOLO_VALIDACION_USUARIOS.md), diez tareas comunes (T1–T10).
**Fuentes:** tres transcripciones y las notas de la sesión GP-01.

## 1. Resumen

Ninguna de las tres sesiones alcanza el criterio de comprensión (8/10 con todos los conceptos críticos). La conclusión no depende de cómo se traten las desviaciones de administración: los dos operativos quedarían por debajo de 8/10 aun si se les acreditaran todas las tareas no evaluadas, y la persona de público general falló un concepto crítico.

| Código | Perfil | Puntaje del protocolo | Techo (§3) | Críticos demostrados | Facilidad 1–7 | Sesión |
|---|---|---:|---:|---:|---:|---|
| BR-01 | Guardaparque con experiencia como brigadista | 2/10 | 5/10 | 2 de 7 | 6 | Incompleta (3 NE) |
| GP-01 | Guardaparque | 3/10 | 4/10 | 1 de 7 | Sin dato | Incompleta (3 NE) |
| PG-01 | Público general, sin conocimiento previo | 5/10 | 8/10 | 4 de 7 | 7 | Completa, con consignas reformuladas |

Estos puntajes combinan dos causas que hay que leer por separado. Una parte refleja la interfaz; otra refleja que la moderación se apartó del guion, con explicaciones anticipadas y tareas omitidas. Las 6 tareas no evaluables (NE) se deben a la segunda causa.

**Lo que funciona.** Nadie interpretó que avanzar la animación incorpora observaciones nuevas (0 de 2 evaluados). Las tres personas terminaron distinguiendo lo observado de lo previsto, y la facilidad declarada fue alta (6 y 7 de 7).

**Lo que hay que corregir.** Se abrieron tres hallazgos P0:

- El acuerdo 0,80 se leyó como probabilidad en 2 de 3 sesiones.
- Quedar fuera de la zona se leyó como ausencia de riesgo de fuego en 2 de 3 sesiones.
- GP-01 cree que la herramienta usa «satélite en tiempo real» y que no tiene limitaciones, y la imagina como base para decidir evacuaciones.

**Alcance.** Son tres casos sobre una muestra prevista de trece. Los resultados orientan mejoras, pero no permiten generalizar ni habilitan uso operativo.

## 2. Muestra y condiciones

| Código | Cohorte | Modo de sesión | Quién operó la interfaz | Caso de perfil |
|---|---|---|---|---|
| BR-01 | Operativa | Remota; participante en celular, viendo la pantalla compartida por el moderador | Moderador | Brigadista |
| GP-01 | Operativa | Remota; participante con la plataforma abierta y pantalla compartida | Participante | Guardaparque |
| PG-01 | Público general | Sin registro explícito | Participante | No aplicado |

**Avance contra la muestra prevista en el informe.** La cohorte operativa tiene 2 de 3 perfiles (falta coordinador) y público general tiene 1 de 10 personas. BR-01 es un perfil híbrido: trabaja como guardaparque, tiene experiencia en combate y se le aplicó el caso de brigadista.

**Versión evaluada.** Las transcripciones no registran fecha, URL ni versión. El protocolo cita la interfaz observada el 03/11/2026 y el último cambio de frontend es `3c35cc5`, del 01/11/2026, de modo que se asume esa versión hasta confirmarla.

**Registro faltante.** El protocolo pedía datos que no se relevaron en ninguna sesión:

- Tiempo activo por tarea.
- Confianza 1–5 por respuesta.
- Recorrido adicional «cambiar de incendio». PG-01 sí identificó espontáneamente que otra zona correspondía a otro incendio.
- Pregunta de cierre sobre frecuencia de uso y sobre qué cambiar para no abandonar la herramienta.

## 3. Cómo se puntuó

Se aplicó la clave del protocolo: C (completa) suma 1; P (parcial) e I (incorrecta) suman 0. Las transcripciones no separan hablantes, por lo que cada intervención se atribuyó por contexto. Las citas conservan los errores de transcripción. Para resolver casos que el protocolo no contempla se fijaron cuatro reglas:

1. **Respuesta inicial.** Se puntúa la primera respuesta del participante. Lo que corrige después de una repregunta se registra como autocorrección y no cambia el puntaje.
2. **Consigna reformulada.** Vale si conserva el concepto evaluado. Si deja sin preguntar una parte de la clave, la tarea no llega a C.
3. **NE (no evaluable).** Se marca cuando la consigna no se administró, o cuando el moderador dio la respuesta antes de que el participante pudiera producirla. El protocolo reserva NE para fallas técnicas; aquí se extiende porque esas tareas tampoco miden comprensión. Una NE suma 0, mantiene el denominador en 10 y deja la sesión incompleta.
4. **Transcripción sobre notas.** Si las notas y la grabación difieren, prevalece lo dicho literalmente (§8).

El **techo** suma al puntaje las tareas cuya respuesta fue compatible con la clave, pero quedó incompleta por la administración. No es el resultado oficial: indica cuánto del puntaje bajo podría deberse a la moderación y no a la interfaz. No incluye tareas sin evidencia.

## 4. Resultados por tarea

★ = concepto crítico. El superíndice ᵗ marca las tareas que suman en el techo.

| Tarea | Concepto | BR-01 | GP-01 | PG-01 | Correctas | Techo |
|---|---|:---:|:---:|:---:|:---:|:---:|
| T1 ★ | Demo histórica y fecha | I | P | C | 1 de 3 | 1 de 3 |
| T2 ★ | Observado frente a calculado | Pᵗ | C | C | 2 de 3 | 3 de 3 |
| T3 | Última observación y fuente | I | C | C | 2 de 3 | 2 de 3 |
| T4 | Horizonte, líneas y dos controles | NE | C | Pᵗ | 1 de 3 | 2 de 3 |
| T5 ★ | La animación no agrega datos | C | NEᵗ | C | 2 de 3 | 3 de 3 |
| T6 ★ | Sin acciones de combate | NEᵗ | NE | C | 1 de 3 | 2 de 3 |
| T7 ★ | Significado de ≥ 0,80 | P | I | Pᵗ | 0 de 3 | 1 de 3 |
| T8 ★ | Períodos y metadatos del ensamble | NE | NE | Pᵗ | 0 de 3 | 1 de 3 |
| T9 ★ | Fuera de la zona coloreada | C | P | I | 1 de 3 | 1 de 3 |
| T10 | Limitación y fuente | Pᵗ | I | I | 0 de 3 | 1 de 3 |
| **Total** | | **2/10** | **3/10** | **5/10** | | |
| **Techo** | | **5/10** | **4/10** | **8/10** | | |

T7 no tuvo ninguna respuesta completa y T8 no tiene evidencia suficiente de que los metadatos se entiendan. Son las dos tareas sobre el ensamble y coinciden con el hallazgo P0 más repetido. La evidencia por tarea está en el Anexo A.

## 5. Resultado contra los criterios

| Código | Grupo/rol | Correctas/10 | Críticos no demostrados | Navegación independiente / aplicable | Facilidad | Uso concreto identificado | Estado |
|---|---|---:|---|---:|---:|---|---|
| BR-01 | Operativo, brigadista/guardaparque | 2 | T1, T2, T6, T7, T8 | No evaluable | 6 | Contrastar con el terreno, minuto a minuto, para reunir datos hoy dispersos | Incompleta |
| GP-01 | Operativo, guardaparque | 3 | T1, T5, T6, T7, T8, T9 | 4/6 | Sin dato | Planes de evacuación y explicar la situación a visitantes | Incompleta |
| PG-01 | Público general | 5 | T7, T8, T9 | 7/9 | 7 | Ninguno personal; lo ve útil para parques y organismos | Completa |

- **Operativos (8/10 y todos los críticos):** no se cumple. BR-01 llegaría a 7/10 y GP-01 a 6/10 aun sumando al techo todas sus tareas NE restantes.
- **Público general (8 de 10 personas con 8/10):** no aplicable todavía, con 1 sesión de 10. PG-01 no alcanza 8/10 según el protocolo. En el techo llegaría a 8/10, pero sin demostrar T9.

## 6. Hallazgos priorizados

Los cambios son candidatos. El protocolo indica no modificar la interfaz dentro de una misma tanda; si se despliega una versión nueva, sus resultados se informan por separado.

### P0: interpretación peligrosa o sobreconfianza

| Hallazgo | Evidencia literal y tarea | Afectados/evaluados | Cambio candidato | Cómo verificarlo |
|---|---|---|---|---|
| **El acuerdo se lee como probabilidad** | GP-01, T7: «el 0,80 es como que es altamente probable que suceda»; «0,50 […] sería como el escenario que va a suceder». BR-01, T7: «esa es la más probable» | 2 de 3 (1 de 1 guardaparque, 1 de 1 brigadista, 0 de 1 público general) | Mostrar «≥ 80 % de las simulaciones» en la leyenda y revisar la etiqueta «escenario central», que GP-01 leyó casi literalmente como lo que va a suceder | T7 sin mencionar «probable» en la explicación de la banda |
| **Fuera de la zona se lee como sin riesgo de fuego** | PG-01, T9: «no llegaría en la propagación del incendio» (lo matizó al repreguntarle). GP-01, T9: «creo que no habría riesgo»; en el caso de perfil: «está fuera del riesgo del incendio», y sólo advierte por humo y ceniza | 2 de 3 (1 de 1 guardaparque, 1 de 1 público general). BR-01 respondió lo contrario: «no hay zona segura» | Llevar junto a la leyenda el aviso que hoy está sólo en Documentación: el incendio real puede extenderse fuera de la zona ≥ 0,10 | T9 con una razón vinculada al alcance del modelo |
| **Sobreconfianza y vigencia** | GP-01, T10: «limitaciones no tiene ninguna, porque […] si se maneja con un satélite en tiempo real»; «en la predicción a las 24 horas llega a tocar el pueblito, bueno, hay que claramente evacuar». BR-01, T3: «5 de enero, 18.44, esa es la hora actual» (hora animada) | Tiempo real y sin límites: 1 de 3. Hora animada tomada como actual: 1 de 3 | Mostrar antigüedad de la observación y aviso de no uso operativo en el panel, no sólo en el banner; rotular la hora del resumen como simulada | T1, T3 y T10 con personas que no conozcan la herramienta |

BR-01 también dijo que «la predicción a 24 horas nos mantiene seguros de eso» al armar su resumen de equipo, aunque enseguida buscó una vía de escape y exigió contraste con el terreno. No se cuenta como hallazgo separado, pero muestra que incluso con experiencia la predicción puede usarse como respaldo de seguridad.

### P1: bloqueo del recorrido central

| Hallazgo | Evidencia | Afectados/evaluados | Cambio candidato | Cómo verificarlo |
|---|---|---|---|---|
| **El banner de demo no siempre se percibe** | Sólo PG-01 lo citó. A GP-01 algo le tapaba la fecha («Me lo tapaba la ventanita») y BR-01 nunca lo mencionó, con el texto chico en su celular | 2 de 3 no lo reconocieron | Reforzarlo dentro del mapa o del panel | T1 en computadora y celular reales |
| **La fuente de los datos cuesta encontrarla** | GP-01, T3: confundió fuente con lugar («¿Puerto Patriada?»), probó en Límite modelo y llegó a Documentación: «esa parte me está costando». PG-01 fue directo | 1 de 2 con dificultad | Enlazar la fuente desde «Última actualización» | Navegación independiente en T3 |
| **Última y próxima pasada se pueden confundir en pantallas chicas** | BR-01, T3: leyó «6 de enero, 2.30» como última observación; «no lo leí, estaba muy chiquito» | 1 de 3, sobre pantalla compartida en celular | Revisar la jerarquía visual en móvil | T3 en celular operado por el participante |

### P2: esfuerzo o legibilidad

| Hallazgo | Evidencia | Afectados/evaluados | Cambio candidato |
|---|---|---|---|
| **El orden de los colores de las isócronas es ambiguo** | GP-01 dudó: «como que me confundo un poco». El moderador también se confundió (ver abajo) | 1 de 3, más el moderador | Rotular la leyenda con tiempos y separar visualmente el frente activo |
| **Faltan referencias territoriales** | GP-01 se ubicó alejando el mapa hasta reconocer la península de Valdés; la nota lo describe como «todo muy manual». No se comprobó que pudiera identificar senderos | 1 de 1 evaluada | Agregar localidades, caminos y senderos; verificar disponibilidad de datos |
| **Símbolos sin significado evidente** | PG-01: «Los puntos rojos no sabría decirte qué son» | 1 de 3 | Agregar «detecciones satelitales» a la leyenda |
| **Datos pedidos** | BR-01 preguntó por lluvias y destacó vegetación e incendios previos; propuso cargar información de terreno. GP-01 usó el viento como indicio del humo, que el producto no modela | 2 de 2 operativos | Evaluar pedidos; aclarar que el viento no equivale a una predicción de humo |

**Ambigüedad de colores verificada en el código.** La leyenda y el mapa van de amarillo a las 0 h a rojo oscuro en el horizonte (`arrivalRamp` en `frontend/components/fire-map.tsx`). Por lo tanto, GP-01 acertó al decir que más oscuro significa más tiempo, y el moderador se equivocó al responderle: «mientras más clarito es más lejos en el tiempo». La nota de sesión repite ese error. El origen probable de la duda es que el frente activo se dibuja casi blanco (`#fff4c2`) justo en el borde más avanzado, de modo que durante la animación lo más lejano se ve claro.

## 7. Utilidad y casos de uso

**Problema actual.** BR-01 describió información fragmentada durante un incendio grande: focos en una aplicación, viento en otra y datos por radio, que alguien unificaba o cada uno infería. GP-01 afirmó que no existen herramientas así para brigadistas y que tienen muy poco presupuesto.

**Valor percibido.**

- **BR-01:** suma si se contrasta con lo que se ve en el terreno: «esto se evalúa a minuto a minuto». Advirtió que la calidad de los datos determina el resultado. Con el caso de perfil armó un resumen con puntos de ataque, cola del incendio y vía de escape.
- **GP-01:** la considera «recontraútil» para planes de evacuación y para explicar la situación a una persona visitante. Destacó el costo de traer helicópteros. Esa comparación es un dato de utilidad percibida, pero también una señal de alerta: la herramienta no reemplaza la observación aérea.
- **PG-01:** no la usaría porque no vive en la zona, salvo de viaje. La ve útil para parques nacionales y organismos que deben ubicar personal.

**Facilidad.** BR-01 puso 6: «cualquiera involucrado en incendios puede leer esto». PG-01 puso 7: «Con cero conocimiento sobre el tema, me pareció muy fácil». Las dos notas deben leerse con cautela: BR-01 no operó la interfaz, y la facilidad percibida convivió con errores en conceptos críticos. A GP-01 no se le preguntó.

## 8. Limitaciones de este corte

- **Muestra.** Tres personas, sin coordinador y con público general representado por un solo caso. No corresponden porcentajes ni pruebas estadísticas.
- **Moderación.** Se explicaron contenidos antes de medirlos: a BR-01 se le leyeron el límite del modelo y la ayuda del ensamble, y se le dijo «con mayor certeza» al explicar las bandas, lo que pudo reforzar la lectura probabilística. También se validó como correcta su lectura de la hora animada.
- **Condiciones.** BR-01 no pudo operar la interfaz, así que su sesión no mide navegación y su lectura de textos pequeños pudo perjudicar T1 y T3.
- **Sesiones no equivalentes.** Las consignas variaron y el caso de perfil faltó en PG-01, por lo que la comparación entre participantes es sólo orientativa.
- **Discrepancias entre notas y transcripción en GP-01.** Se priorizó la transcripción:

| Tarea | Notas | Transcripción | Decisión |
|---|---|---|---|
| T5 | Entiende que no recibe datos nuevos | La consigna no se hizo; hay evidencia indirecta en T3 | NE, suma en el techo |
| T6 | Registra el uso para evacuación | No se preguntó sobre combate | NE |
| T7 | «Entiende que es el ensamble perfectamente» | «un ensamble entre el pronóstico y el incendio» y 0,80 como «altamente probable» | I |
| T8 | Registra la confusión de colores | No se pidieron miembros, inicio ni vigencia | NE |

## 9. Próximos pasos

1. **Hacer la devolución pendiente a GP-01.** El protocolo pide no cerrar con errores críticos. Conviene aclararle el significado de las bandas, que el fuego puede llegar fuera de la zona, que los datos no son en tiempo real y que sí acertó con los colores.
2. **Reforzar la administración de las próximas sesiones.** Usar la consigna literal, no explicar antes de cerrar cada tarea, y registrar tiempo, confianza y dispositivo. Exigir computadora o que el participante opere la interfaz.
3. **Completar los bloques NE con personas nuevas cuando sea posible.** BR-01 (T4, T6, T8) y GP-01 (T5, T6, T8) ya fueron expuestos a las respuestas, de modo que una repetición debe informarse como tal. También falta la facilidad de GP-01.
4. **Completar la muestra.** Falta un coordinador y nueve personas de público general.
5. **Confirmar los datos de ficha.** Fecha, versión y consentimiento de cada sesión; el de GP-01 no consta en la transcripción.
6. **Decidir cuándo corregir la interfaz.** Los hallazgos P0 son los primeros candidatos; si se cambia antes de cerrar la tanda, las sesiones siguientes se reportan como versión nueva.

## Anexo A. Evidencia por tarea

Navegación: Ind. = independiente; Asist. = asistida; NC = no completada; N/A = no aplica. Los puntos suspensivos indican texto omitido.

### BR-01

La navegación es N/A en todas las tareas, porque operó el moderador.

| ID | Evidencia | Comprensión | Punto | Observación |
|---|---|:---:|:---:|---|
| T1 | No menciona demo ni banner. Ante la pregunta por el momento no queda respuesta grabada y el moderador continúa | I | 0 | La lectura desde el celular pudo influir |
| T2 | «el más grande vendría a ser como el punto en que está»; luego: «A menos que sea una predicción de cómo puede llegar a estar» | P | 0 | Autocorrección espontánea; suma en el techo |
| T3 | «la última observación, 6 de enero, 2.30»; «5 de enero, 18.44, esa es la hora actual» | I | 0 | Toma la próxima pasada y luego la hora animada. El moderador mostró la fuente |
| T4 | Sin consigna ni manipulación de controles | NE | 0 | Sólo describió «tres escalas» |
| T5 | «Y no, sigue siendo lo mismo»; «Cuando vaya transcurriendo el tiempo y a ver si la predicción es igual a lo que sucede» | C | 1 | Consigna inductiva; la segunda frase es espontánea |
| T6 | Tras la lectura del límite: «No, yo diría que no»; «una intervención humana marcaría como una zona por ahí más recta» | NE | 0 | Respuesta adelantada; su inferencia por la forma sugiere comprensión. Suma en el techo |
| T7 | «el programa tira varios intentos, varias predicciones y esa es la más probable»; «no es una certeza porque depende de los factores climáticos» | P | 0 | Capta los múltiples intentos, pero usa «más probable». Se le había leído la ayuda |
| T8 | Sin consigna; no llegó a Ver más | NE | 0 | El moderador leyó el horizonte de 24 h |
| T9 | «todo lo que sea la periferia del incendio va a estar en riesgo porque uno no sabe cómo actúa el incendio»; «no hay zona segura» | C | 1 | Preguntado sobre isócronas a 7 h, no sobre la capa de ensamble |
| T10 | Pregunta por «lluvias»; «La calidad de los datos influye mucho en la calidad y el resultado final del modelo» | P | 0 | Sin búsqueda de límite ni fuente; propone contrastar con terreno. Suma en el techo |

### GP-01

| ID | Evidencia | Comprensión | Punto | Navegación | Observación |
|---|---|:---:|:---:|:---:|---|
| T1 | «imagen satelital con un posible incendio»; «del 5 de enero a las 4 y 20» | P | 0 | Ind. | Da la fecha, pero no dice que sea histórica. El moderador ya había dicho «demostración» |
| T2 | «el perímetro observado del incendio sería todo lo que está como en gris clarito»; lo naranja «sería la predicción» | C | 1 | Ind. | Apoyada en la leyenda y la animación |
| T3 | «la última actualización sería el 5 de enero a las 4 y 20»; «Detecta focos con el satélite VIRS» | C | 1 | Ind. | Llegó a la fuente con dificultad. No cita NASA FIRMS |
| T4 | «mientras más oscuro es cada vez más lejos»; «una te frena la predicción […] y la otra es la extensión de la predicción» | C | 1 | Ind. | Horizonte en 6 h y pausa a 2,5 h. El moderador la corrigió erróneamente (§6) |
| T5 | Sin consigna. En T3: «la próxima actualización, que calculo que sería en base a datos reales» | NE | 0 | N/A | Evidencia indirecta; suma en el techo |
| T6 | Sin consigna. Respondió a una pregunta sobre decisiones: planes de evacuación | NE | 0 | N/A | Nunca se abordó la supresión |
| T7 | «un ensamble entre el pronóstico y el incendio»; «el 0,80 es como que es altamente probable que suceda» | I | 0 | Asist. | Hallazgo P0. El moderador indicó dónde hacer clic |
| T8 | «Sí, se entiende», ante una pregunta cerrada del moderador | NE | 0 | N/A | No se buscaron miembros, inicio ni vigencia |
| T9 | «haría un plan de evacuación, por más que quede fuera»; «creo que no habría riesgo» si está muy lejos | P | 0 | N/A | Conducta prudente por humo y ceniza; no contempla que el fuego llegue |
| T10 | «limitaciones no tiene ninguna, porque […] si se maneja con un satélite en tiempo real» | I | 0 | NC | Hallazgo P0 |

### PG-01

| ID | Evidencia | Comprensión | Punto | Navegación | Observación |
|---|---|:---:|:---:|:---:|---|
| T1 | «hay una alerta que dice modo de demostración»; «no es un incendio en curso»; «supongo que el incendio no está ocurriendo» | C | 1 | Ind. | Espontáneo, antes de la consigna |
| T2 | «lo que está en puntitos, en líneas puntuadas, sería lo que está ocurriendo en el momento»; «lo que va creciendo sería cómo seguiría desarrollando» | C | 1 | Ind. | No sabe qué son los puntos rojos |
| T3 | «última actualización el 5 de enero a las 4 y 20»; «La NASA FIMS»; «VIRS» | C | 1 | Ind. | Fue directo a Documentación y Fuentes |
| T4 | «cada hora que pasa es una nueva área que se va quemando» | P | 0 | Ind. | No se pidió pausa ni diferencia entre controles; suma en el techo |
| T5 | «No, no, no»; señala «perímetro observado» frente a isócronas previstas | C | 1 | Ind. | Consigna reformulada; atribución de hablante incierta en una frase |
| T6 | «no hay una acción de frenado al fuego, como que se está moviendo libremente» | C | 1 | Ind. | Encontró Límites del modelo sin ayuda |
| T7 | «en las zonas más rojas es donde suceden la mayor cantidad de simulaciones» | P | 0 | Asist. | Lectura correcta, pero no interpreta el umbral. No se preguntó qué no puede afirmar; suma en el techo |
| T8 | «Miembros válidos, 31 del 31»; «Arranca el 5 de enero a las 4»; «horizonte, 24 horas» | P | 0 | Ind. | Llegó a Ver más. No se pidió distinguir 6 h de 24 h ni vigencia; suma en el techo |
| T9 | «no llegaría en la propagación del incendio»; luego: «no puedo afirmarlo, pero no sé si es una cuestión personal o del propio modelo» | I | 0 | N/A | Hallazgo P0. Corrigió con repregunta y explicación del moderador |
| T10 | «por ahí extender el horario, pero por ahí en 24 horas ya cae la supervisión» | I | 0 | NC | No identifica un límite. Fragmento confuso: conviene revisar el audio |
