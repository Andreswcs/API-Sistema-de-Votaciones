# Registro de decisiones

Cada entrada: contexto, decisión y alternativa descartada.

## Configuración de la base de datos por componentes, no con `DATABASE_URL`

- **Contexto:** la contraseña local del `.env` contiene caracteres que no son válidos en una URL sin codificar. Interpolar `postgresql://${USER}:${PASSWORD}@...` en el compose rompería la conexión.
- **Decisión:** `Settings` lee `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` y `POSTGRES_DB` (las mismas variables que usa la imagen de Postgres) y construye la URL con `sqlalchemy.URL.create`, que escapa la contraseña. En Docker la API recibe `POSTGRES_HOST=db`.
- **Descartado:** una única variable `DATABASE_URL`. Obliga a duplicar credenciales y a codificarlas a mano.

## `requirements.txt` mínimo y fijado

- **Contexto:** el `requirements.txt` original era un `pip freeze` en UTF-16 de un `venv` con Python 3.10, con paquetes ajenos al proyecto (sentry, opentelemetry, fastapi-cloud-cli).
- **Decisión:** se reemplaza por las dependencias directas del stack con versión fijada, y `requirements-dev.txt` añade pytest y httpx. El entorno virtual es `.venv` con Python 3.12. La carpeta `venv` antigua queda ignorada en git.
- **Descartado:** congelar todas las dependencias transitivas; es ruido y ata la imagen a paquetes innecesarios.

## Valores por defecto en `docker-compose.yml`

- **Contexto:** el compose original leía `${POSTGRES_USER}` etc. sin valor por defecto, así que sin `.env` no arrancaba.
- **Decisión:** `${VAR:-valor}` con valores de desarrollo (`votaciones`/`votaciones`/`votaciones_db`). Si existe un `.env` local, sus valores tienen prioridad.
- **Descartado:** exigir al evaluador crear un `.env`.

## Healthcheck con `pg_isready -h localhost`

- **Contexto:** durante la ejecución de los scripts de `/docker-entrypoint-initdb.d`, Postgres levanta un servidor temporal que solo escucha por socket Unix.
- **Decisión:** comprobar por TCP (`-h localhost`) para que el servicio no se marque como sano antes de que existan las tablas.
- **Descartado:** `pg_isready` sin host, que puede dar "listo" a mitad de la inicialización.
