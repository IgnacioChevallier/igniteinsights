# Protocolo de evaluación de transparencia del acuerdo del ensamble

> Estado: instrumento preparado; **evaluación con personas reales pendiente**. No se registran
> participantes ni resultados hasta ejecutar el protocolo. Los criterios de éxito están
> congelados antes de observar respuestas.

## 1. Condiciones de ejecución

- Evaluación individual, sin capacitación previa ni explicación oral de la interfaz.
- La persona usa únicamente la información visible en el producto.
- El facilitador lee las consignas literalmente y no corrige ni orienta durante las tareas.
- Después de entregar todas las respuestas se permite una entrevista breve para comprender
  errores; esas aclaraciones no cambian la puntuación inicial.
- Se registra la versión de la interfaz, el caso mostrado, el ciclo meteorológico, el inicio,
  el horizonte y la vigencia del artefacto.
- Las cohortes operativa y general se analizan por separado. No se calcula un promedio común.

## 2. Cohortes previstas

### Usuarios operativos

Tres personas, reportadas individualmente:

1. un/a brigadista;
2. un/a guardaparque;
3. un/a coordinador/a.

### Público general

Diez personas sin necesidad de experiencia previa en incendios forestales o simulación.

## 3. Tareas comunes

Cada participante debe realizar estas tareas sobre el mismo escenario congelado:

1. Identificar qué parte del mapa corresponde a observación y cuál a simulación.
2. Indicar la hora y la fuente de la última observación mostrada.
3. Explicar con palabras propias qué representan las isócronas.
4. Leer el inicio, el horizonte y la vigencia del pronóstico.
5. Activar **Acuerdo del ensamble** y explicar “acuerdo entre simulaciones”.
6. Identificar miembros válidos y esperados, y el ciclo meteorológico.
7. Comparar `≥ 0,10`, `≥ 0,50` y `≥ 0,80` sin llamar probabilidad a las bandas.
8. Indicar si la simulación considera combate o supresión.
9. Describir qué significa “propagación potencial”.
10. Desactivar la capa y comprobar que las isócronas continúan visibles.
11. Responder si el incendio real puede llegar fuera de la zona `≥ 0,10`. Respuesta esperada:
    sí; la capa sólo varía la meteorología. Se agregó el 2026-10-17, antes de cualquier
    participante, porque el consolidado de 23 backtests mostró crecimiento observado fuera de
    la envolvente (ver `ENSAMBLE-BACKTESTS-CONSOLIDADO.md`). Es complementaria: se registra
    aparte y no entra en el porcentaje ni en los criterios de §5.

Las respuestas críticas son las tareas 1, 4, 5 y 8: diferencia observación/simulación,
horizonte y vigencia, acuerdo frente a probabilidad, y ausencia de supresión.

## 4. Tareas específicas por rol operativo

### Brigadista

- Señalar una zona alcanzada por la envolvente `≥ 0,10` pero fuera del escenario central
  `≥ 0,50` y describirla como posibilidad que requiere atención, no como resultado seguro.
- Identificar una limitación que impide usar la capa como instrucción táctica autónoma.
- Explicar por qué el mapa no representa el efecto de líneas, medios aéreos ni ataque directo.

### Guardaparque

- Identificar un sector de propagación potencial relevante para acceso o evacuación.
- Distinguir el perímetro observado vigente de la extensión simulada a 12/24 horas.
- Explicar qué información adicional buscaría antes de comunicar el escenario al público.

### Coordinador

- Comparar escenario central, alto acuerdo y propagación posible como insumos de planificación.
- Verificar si el producto está vigente a la hora hipotética indicada por el facilitador.
- Explicar por qué 31/31 miembros válidos mejora la trazabilidad pero no convierte el acuerdo
  en una probabilidad calibrada.

## 5. Criterios de éxito congelados

### Cohorte operativa

- Cada persona debe resolver correctamente al menos el 80 % de sus tareas.
- Las tres personas deben responder correctamente los cuatro conceptos críticos.
- Los resultados se reportan por persona y por rol; con `n=3` no se generalizan a toda la
  población operativa.

### Público general

- Al menos 8 de 10 personas deben resolver correctamente un mínimo del 80 % de las tareas
  comunes.
- Se informa además cuántas personas respondieron correctamente cada concepto crítico.

Una respuesta se considera correcta sólo si no contradice el copy visible. En particular,
“probabilidad de que se queme” es incorrecto para el acuerdo, y afirmar que el modelo incorpora
supresión es incorrecto.

## 6. Formulario de respuestas

### Identificación de sesión

- Código anónimo de participante:
- Cohorte y rol (si corresponde):
- Fecha/hora:
- Versión o commit de la interfaz:
- Caso y reinicio mostrados:
- Ciclo meteorológico:
- Inicio / horizonte / vigencia:
- Resolución de pantalla y dispositivo:

### Registro por tarea

| Tarea | Respuesta literal | Correcta (sí/no) | Tiempo (s) | Ayuda solicitada | Observación |
|---:|---|---|---:|---|---|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |
| 4 |  |  |  |  |  |
| 5 |  |  |  |  |  |
| 6 |  |  |  |  |  |
| 7 |  |  |  |  |  |
| 8 |  |  |  |  |  |
| 9 |  |  |  |  |  |
| 10 |  |  |  |  |  |
| 11 (complementaria) |  |  |  |  |  |

Para la cohorte operativa se agregan tres filas con las tareas específicas del rol.

### Entrevista posterior no puntuable

- ¿Qué elemento resultó más difícil de interpretar?
- ¿Qué frase o símbolo produjo esa dificultad?
- ¿Qué decisión creyó que la capa permitía tomar?
- ¿Qué información adicional esperaba encontrar?
- ¿Cambiaría alguna palabra sin alterar el significado científico?

## 7. Plantilla de resultados por cohorte

### Operativa

| Código | Rol | Correctas/total | Porcentaje | Críticos 4/4 | Cumple | Nota cualitativa |
|---|---|---:|---:|---|---|---|
| pendiente | brigadista |  |  |  |  |  |
| pendiente | guardaparque |  |  |  |  |  |
| pendiente | coordinador/a |  |  |  |  |  |

### Público general

| Código | Correctas/10 | Porcentaje | Críticos 4/4 | Cumple 80 % | Nota cualitativa |
|---|---:|---:|---|---|---|
| P01 |  |  |  |  |  |
| P02 |  |  |  |  |  |
| P03 |  |  |  |  |  |
| P04 |  |  |  |  |  |
| P05 |  |  |  |  |  |
| P06 |  |  |  |  |  |
| P07 |  |  |  |  |  |
| P08 |  |  |  |  |  |
| P09 |  |  |  |  |  |
| P10 |  |  |  |  |  |

Resumen a completar después de la ejecución:

- personas con al menos 80 %: `__/10`;
- personas con los cuatro conceptos críticos: `__/10`;
- errores por tarea: pendiente;
- hallazgos cualitativos: pendiente;
- cambios de copy posteriores, si correspondieran: pendiente y versionados.

## 8. Datos que no deben fabricarse

Hasta realizar sesiones reales permanecen vacíos los códigos de participantes, tiempos,
respuestas, porcentajes, observaciones y conclusiones de usabilidad. Una demostración interna o
un test automatizado de UI no cuenta como participante.
