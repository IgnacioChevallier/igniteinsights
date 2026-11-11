# IgniteInsights

**Ignacio Chevallier Boutell y Manuel Salas Seeber**

IgniteInsights es una plataforma de apoyo para visualizar la propagación potencial de
incendios forestales en el Parque Nacional Los Alerces y su entorno. Integra detecciones
satelitales FIRMS, pronósticos meteorológicos GFS, topografía y cartografía de combustibles
para preparar y ejecutar simulaciones con ELMFIRE. Los resultados se consultan desde una
interfaz web.

Es un prototipo académico: sus resultados representan escenarios modelados y no sustituyen
información oficial ni decisiones operativas.

## Documentación

- [Índice de documentación](docs/README.md)
- [Estado y resultados de la investigación](docs/resultados/modelo/estado.md)
- [Modelo promovido](docs/resultados/modelo/modelo.md)

## Entorno local

Se necesita Docker con Docker Compose. El entorno base incluye la interfaz, la API y
PostgreSQL/PostGIS; el simulador ELMFIRE es opcional y vive en un repositorio separado.

```bash
cp .env.example .env
# Completar FIRMS_MAP_KEY y OPENTOPOGRAPHY_API_KEY en .env

docker compose build api frontend
docker compose up -d db api frontend
docker compose exec api uv run alembic upgrade head

# Crear un usuario local; el comando imprime la contraseña inicial
docker compose exec frontend npm run usuarios -- crear admin@local.test "Admin local" admin
```

La aplicación queda disponible en <http://localhost:3000>. Para desarrollo con recarga
automática, pruebas y simulaciones, consultar la [guía de desarrollo
local](docs/desarrollo.md).
