# Registro de decisiones

Cada entrada: contexto, decisión y alternativa descartada. La explicación detallada está en [ARQUITECTURA.md](ARQUITECTURA.md).

## Modelo de datos

### Email obligatorio y único entre roles

- **Contexto:** hace falta un dato que identifique a una persona para impedir registros duplicados. El nombre no sirve, porque dos personas pueden llamarse igual.
- **Decisión:** el email es obligatorio y tiene `UNIQUE` en `persons`, de modo que el mismo email no puede registrarse como votante y como candidato.
- **Descartado:** email opcional o único solo por tabla. No permitiría garantizar que alguien no sea votante y candidato a la vez.

### Tabla `persons` con rol y FK compuesta `(person_id, role)`

- **Contexto:** una persona no puede ser votante y candidato a la vez, y debe cumplirse aunque lleguen peticiones simultáneas.
- **Decisión:** `persons(id, name, email, role)` con `UNIQUE (id, role)`. `voters` y `candidates` tienen `role` fijado por `CHECK` y una FK `(person_id, role) → persons(id, role)`. Lo garantiza la base de datos.
- **Descartado:** dos tablas independientes y comprobar en Python si el email existe en la otra. Hay una condición de carrera entre la comprobación y el insert.

### `ON DELETE RESTRICT` en todas las FK

- **Contexto:** borrar a un votante que ya votó o a un candidato con votos dejaría resultados incoherentes.
- **Decisión:** `RESTRICT`. El service intenta el borrado y traduce la violación de `fk_votes_voter` o `fk_votes_candidate` a 409 `RESOURCE_IN_USE`, sin consultar antes si hay votos.
- **Descartado:** `CASCADE`, que borraría votos en silencio. También comprobar `has_voted` antes de borrar, porque deja una ventana entre la comprobación y el borrado.

### Email normalizado a minúsculas

- **Contexto:** `Ana@Mail.com` y `ana@mail.com` son, a efectos prácticos, la misma persona.
- **Decisión:** el schema de entrada aplica `strip` y minúsculas antes de validar el email. La base de datos tiene `CHECK (email = lower(email))` como red de seguridad.
- **Descartado:** un índice único sobre `lower(email)` guardando el email original. Funciona, pero entonces la API devolvería emails con mayúsculas distintas para la misma persona.

### Ids compartidos entre votantes y candidatos

- **Contexto:** con `persons` como tabla común, la PK natural de `voters` y `candidates` es `person_id`.
- **Decisión:** el id público es `person_id`. `GET /voters/2` responde 404 si la persona 2 es candidata.
- **Descartado:** ids propios en cada tabla de rol. Añade una columna y un índice sin aportar nada.

### Estadísticas calculadas desde `votes`

- **Contexto:** `candidates.votes` es un contador desnormalizado. Si alguna vez se desincronizara, las estadísticas mentirían.
- **Decisión:** `GET /votes/statistics` cuenta filas de `votes` con un `LEFT JOIN` desde `candidates`. El contador se mantiene con `votes = votes + 1` en la misma transacción que el voto, y un test comprueba que coincide con el `COUNT`.
- **Descartado:** leer `candidates.votes` en las estadísticas. Sería más barato, pero depende de un dato derivado.

### El esquema SQL no se ha modificado

- `db/schema.sql` es el `schema.sql` original movido sin cambios. Al revisarlo no se encontraron errores; los modelos SQLAlchemy lo reflejan con los mismos nombres de restricción, y `tests/test_models.py` lo verifica.

## Persistencia y stack

### Esquema por script de inicio, sin `create_all` ni Alembic

- **Contexto:** el esquema ya existía como SQL probado a mano e incluye FK compuestas y `CHECK` con nombres concretos.
- **Decisión:** `db/schema.sql` se monta en `/docker-entrypoint-initdb.d/` y Postgres lo ejecuta al crear el volumen. Los tests aplican el mismo fichero sobre `votaciones_test`.
- **Descartado:** `Base.metadata.create_all`, porque tendríamos dos definiciones del esquema que podrían divergir. Alembic, porque una prueba técnica sin historial de cambios no necesita migraciones; queda como mejora futura.

### SQLAlchemy síncrono

- **Contexto:** FastAPI admite endpoints síncronos y los ejecuta en un pool de hilos.
- **Decisión:** SQLAlchemy 2.x síncrono con psycopg 3. El código es más simple y la carga esperada no justifica async.
- **Descartado:** `AsyncSession`. Añade complejidad (`await` en todas las capas, cuidado con la carga perezosa) sin beneficio aquí.

### Configuración de la base de datos por componentes, no con `DATABASE_URL`

- **Contexto:** la contraseña local del `.env` contiene caracteres que no son válidos en una URL sin codificar. Interpolar `postgresql://${USER}:${PASSWORD}@...` en el compose rompería la conexión.
- **Decisión:** `Settings` lee `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` y `POSTGRES_DB`, las mismas variables que usa la imagen de Postgres, y construye la URL con `sqlalchemy.URL.create`, que escapa la contraseña. En Docker la API recibe `POSTGRES_HOST=db`.
- **Descartado:** una única variable `DATABASE_URL`. Obliga a duplicar credenciales y a codificarlas a mano.

### `requirements.txt` mínimo y fijado

- **Contexto:** el `requirements.txt` original era un `pip freeze` en UTF-16 de un `venv` con Python 3.10, con paquetes ajenos al proyecto (sentry, opentelemetry, fastapi-cloud-cli).
- **Decisión:** se reemplaza por las dependencias directas del stack, con versión fijada; `requirements-dev.txt` añade pytest y httpx. El entorno virtual es `.venv` con Python 3.12, y la carpeta `venv` antigua queda ignorada en git.
- **Descartado:** congelar todas las dependencias transitivas. Es ruido y ata la imagen a paquetes innecesarios.

## Lógica de negocio

### Emisión de voto: INSERT primero, luego `UPDATE` condicional

- **Contexto:** hay que evitar el doble voto incluso con peticiones simultáneas.
- **Decisión:** en una transacción: comprobar que existen votante y candidato, insertar en `votes`, `UPDATE voters ... WHERE has_voted = false` (si afecta a 0 filas, `AlreadyVotedError`) y `votes = votes + 1`. El `UNIQUE` de `votes.voter_id` bloquea a la segunda transacción concurrente, y su `IntegrityError` se traduce a 409.
- **Descartado:** `SELECT ... FOR UPDATE` sobre el votante. También funciona, pero el `UNIQUE` y el `UPDATE` condicional ya bastan y no añaden bloqueos explícitos.

### `IntegrityError` traducido por nombre de restricción

- **Contexto:** varias restricciones distintas producen la misma excepción.
- **Decisión:** se lee `diag.constraint_name` de psycopg y se compara con constantes de `app/models/constants.py`. Los casos no previstos se relanzan.
- **Descartado:** buscar texto en el mensaje de error, que depende del idioma y la versión de PostgreSQL.

### Filtros de listados

- **Decisión:** `name` busca coincidencia parcial sin distinguir mayúsculas (`ILIKE`, con `%` y `_` escapados para que se traten como literales). `party` exige coincidencia exacta, sin distinguir mayúsculas, porque el partido es una categoría: `party=Partido` no debe devolver `Partido Azul` y `Partido Verde`.
- **Supuesto:** `GET /votes` no se pagina, porque la especificación no le asigna parámetros ni errores 422. Se ordena por `id`.

### Validación de entrada

- **Decisión:** `name` y `party` se recortan; `name` debe tener entre 1 y 100 caracteres y `party`, si se envía, entre 1 y 100. Un `party` vacío da 422 en lugar de convertirse en `null`. email-validator ya limita el email a 254 caracteres, dentro del máximo de 255 de la columna.

## Docker

### Valores por defecto en `docker-compose.yml`

- **Contexto:** el compose original leía `${POSTGRES_USER}` etc. sin valor por defecto, así que sin `.env` no arrancaba.
- **Decisión:** `${VAR:-valor}` con valores de desarrollo (`votaciones`/`votaciones`/`votaciones_db`), definidos una sola vez en un ancla YAML compartida por `db` y `api`. Si existe un `.env` local, sus valores tienen prioridad.
- **Descartado:** exigir al evaluador que cree un `.env`.

### Healthcheck con `pg_isready -h localhost`

- **Contexto:** mientras se ejecutan los scripts de `/docker-entrypoint-initdb.d`, Postgres levanta un servidor temporal que solo escucha por socket Unix.
- **Decisión:** comprobar por TCP (`-h localhost`), para que el servicio no se marque como sano antes de que existan las tablas.
- **Descartado:** `pg_isready` sin host, que puede dar "listo" a mitad de la inicialización.

### `/health` sin consultar la base de datos

- **Decisión:** responde `{"status": "ok"}` si el proceso está vivo. La disponibilidad de la base ya la vigila el healthcheck de Compose, y así el router no hace consultas.
- **Descartado:** un `SELECT 1` en `/health`, que exigiría pasar por un service solo para eso.

### Fin de línea LF en el repositorio

- **Decisión:** `.gitattributes` con `eol=lf`, para que los ficheros montados en el contenedor (`schema.sql`) y el `Dockerfile` no cambien al clonar en Windows con `core.autocrlf`.
