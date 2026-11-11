# Producto

## Propósito

IgniteInsights es una demostración académica con forma de producto final. Una persona inicia
sesión, ve los incendios activos dentro del área de estudio y consulta su propagación potencial
durante las próximas 24 horas.

No es un sistema oficial de alerta. La salida representa propagación bajo condiciones modeladas,
sin acciones de combate o contención.

## Roles

- **Administrador:** controla el reloj de demostración, ejecuta procesos y decide qué resultados
  están disponibles.
- **Cliente:** consulta el mapa, la documentación y su cuenta. Ninguna acción del cliente inicia
  cálculos.

La autenticación usa Better Auth con correo y contraseña. El registro público está deshabilitado.
La interfaz Next.js aplica autorización; FastAPI sólo debe estar disponible en la red privada.

## Reloj

El sistema tiene dos modos:

- `demo`: reloj congelado en `operativo.reloj`, avanzado por el administrador pasada a pasada;
- `vivo`: hora real, actualizada por la tarea programada.

Una pasada se vuelve visible cuando FIRMS podría haberla publicado: última detección más tres
horas de latencia. Todas las personas ven el mismo instante.

## Pronóstico operativo

`app/operativo/servicio.py` contiene el flujo común para demostración y modo vivo.
`tick(ahora)`:

1. obtiene las detecciones visibles;
2. las agrupa en incendios;
3. identifica la última pasada de cada incendio;
4. ejecuta una ventana P-24 si todavía no existe un pronóstico para esa pasada.

La demostración precalcula ese mismo flujo. Durante la defensa sólo se recorren resultados ya
guardados.

### Insumos

| Insumo | Procedencia |
|---|---|
| `dem`, `slp`, `asp`, `adj`, `fbfm40`, `cc`, `ch`, `cbh`, `cbd` | preparación estática para el año del incendio |
| `ws`, `wd`, `m1`, `m10`, `m100` | último ciclo GFS disponible cuando la pasada se hizo visible |
| `phi.tif`, `ignicion.shp` | detecciones acumuladas del incendio hasta la pasada |
| `elmfire.data` | `write_namelist`, horizonte de 24 h, `LH=30 %`, `LW=100 %` |

El ciclo se resuelve con `pronostico.ciclo_disponible`: pasada + latencia FIRMS − latencia de
publicación GFS, redondeada al ciclo anterior. Así no se utiliza información meteorológica
posterior al instante simulado.

## Agrupación y dominio

Se aceptan detecciones FIRMS de confianza nominal o alta. Dos detecciones se conectan cuando
están a menos de 3 km y separadas por no más de 24 horas. Un grupo permanece activo si tuvo una
detección durante las últimas 24 horas.

Cada simulación usa una caja alrededor del incendio con 15 km de margen, recortada al área de
estudio. No se simula todo el AOI: una ventana similar a Puerto Patriada ya utiliza cerca de
5,6 GB de la máquina Docker.

## Interfaz

`frontend/components/client-map.tsx` muestra:

- detecciones FIRMS recientes;
- perímetro observado;
- isócronas animadas;
- viento y relieve 3D;
- resumen de crecimiento;
- acuerdo del ensamble, sólo cuando existe y el administrador lo habilitó.

El acuerdo del ensamble está apagado por defecto y se describe como acuerdo entre simulaciones,
no como probabilidad. Tiempo de llegada e intensidad de línea permanecen en las vistas de
administración.

La sección `/documentacion` presenta fuentes, vigencia, límites y el aviso académico. Debe
mantenerse alineada con [`resultados/modelo/limites.md`](resultados/modelo/limites.md).

## Demostración

La reproducción comienza con la primera pasada de Puerto Patriada del 5 de enero de 2026 a las
19:20 UTC. `scripts/demo_operativo.py` es reanudable: completa sólo los pronósticos faltantes y
deja el reloj en el primer resultado.

El identificador del incendio se deriva de su primera detección y desempata por posición para no
depender del orden de las filas en la base.

El ensamble GEFS se precalcula sólo para tres pasos representativos mediante
`scripts/demo_ensamble.py`; ejecutar 31 miembros para cada pasada llevaría unas once horas.

```bash
uv run python scripts/demo_ensamble.py --sin-correr  # mostrar selección
uv run python scripts/demo_ensamble.py               # ejecutar los tres pasos
```

## Modo vivo

Una tarea programada consulta FIRMS cada 30 minutos durante las ventanas habituales de pasada.
ELMFIRE sólo se ejecuta cuando aparece una pasada nueva. Si GFS o el ejecutor fallan, el intento
se repite y el cliente conserva el último resultado válido.

Railway no calcula el ensamble GEFS. Se ejecuta localmente y sólo se registra
`ensemble_agreement.json`, con un mínimo de 24/31 miembros válidos.

## Despliegue

- **API:** sin dominio público; accesible desde Next.js mediante
  `http://api.railway.internal:8000`.
- **Interfaz:** requiere `DATABASE_URL`, `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL` y
  `API_BASE_URL`.
- **Base:** las migraciones se aplican con `alembic upgrade head`.
- **Tarea programada:** invoca `/api/v1/operativo/tick` sólo en modo vivo.

Las cuentas se crean por script y la contraseña inicial se cambia al primer ingreso:

```bash
cd frontend
npm run usuarios -- crear correo@ejemplo.com "Nombre" client
```

