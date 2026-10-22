# Registro de decisiones



## Modelo de datos

### Email obligatorio y único entre roles

- **Contexto:** hace falta un dato que identifique a una persona para impedir registros duplicados. El nombre no sirve, porque dos personas pueden llamarse igual.
- **Decisión:** el email es obligatorio y tiene `UNIQUE` en `persons`, de modo que el mismo email no puede registrarse como votante y como candidato.

### Tabla `persons` con rol y FK compuesta `(person_id, role)`

- **Contexto:** una personaa no puede ser votante y candidato a la vez, y debe cumplirse aunque lleguen peticiones simultáneas.
- **Decisión:** `persons(id, name, email, role)` con `UNIQUE (id, role)`. `voters` y `candidates` tienen `role` fijado por `CHECK` y una FK `(person_id, role) → persons(id, role)`. Lo garantiza la base de datos.


### `ON DELETE RESTRICT` en todas las FK

- **Contexto:** borrar a un votante que ya votó o a un candidato con votos dejaría resultados incoherentes.
- **Decisión:** `RESTRICT`. El service intenta el borrado y traduce la violación de `fk_votes_voter` o `fk_votes_candidate` a 409 `RESOURCE_IN_USE`, sin consultar antes si hay votos.

### Email normalizado a minúsculas

- **Contexto:** `Pepito.Perez@Correo.co` y `pepito.perez@correo.co` son, a efectos prácticos, la misma persona.
- **Decisión:** el schema de entrada aplica `strip` y minúsculas antes de validar el email. La base de datos tiene `CHECK (email = lower(email))` como red de seguridad.

### Ids compartidos entre votantes y candidatos

- **Contexto:** con `persons` como tabla común, la PK natural de `voters` y `candidates` es `person_id`.
- **Decisión:** el id público es `person_id`. `GET /voters/2` responde 404 si la persona 2 es candidata.

### Estadísticas calculadas desde `votes`

- **Contexto:** `candidates.votes` es un contador desnormalizado. Si alguna vez se desincronizara, las estadísticas se van a rompeeer
- **Decisión:** `GET /votes/statistics` cuenta filas de `votes` con un `LEFT JOIN` desde `candidates`. El contador se mantiene con `votes = votes + 1` en la misma transacción que el voto, y un test comprueba que coincide con el `COUNT`.

## Persistencia y stack

### Esquema por script de inicio, sin `create_all` ni Alembic

- **Contexto:** el esquema ya existía como SQL probado a mano e incluye FK compuestas y `CHECK` con nombres concretos.
- **Decisión:** `db/schema.sql` se monta en `/docker-entrypoint-initdb.d/` y Postgres lo ejecuta al crear el volumen. Los tests aplican el mismo fichero sobre `votaciones_test`.

### SQLAlchemy síncrono

- **Contexto:** FastAPI admite endpoints síncronos y los ejecuta en un pool de hilos.
- **Decisión:** SQLAlchemy 2.x síncrono con psycopg 3. El código es más simple y la carga esperada no justifica async.

## Lógica de negocio

### Emisión de voto: INSERT primero, luego `UPDATE` condicional

- **Contexto:** hay que evitar el doble voto incluso con peticiones simultáneas.
- **Decisión:** en una transacción: comprobar que existen votante y candidato, insertar en `votes`, `UPDATE voters ... WHERE has_voted = false` (si afecta a 0 filas, `AlreadyVotedError`) y `votes = votes + 1`. El `UNIQUE` de `votes.voter_id` bloquea a la segunda transacción concurrente, y su `IntegrityError` se traduce a 409.

### `IntegrityError` traducido por nombre de restricción

- **Contexto:** varias restricciones distintas producen la misma excepción.
- **Decisión:** se lee `diag.constraint_name` de psycopg y se compara con constantes de `app/models/constants.py`. Los casos no previstos se relanzan.

### Filtros de listados

- **Decisión:** `name` busca coincidencia parcial sin distinguir mayúsculas (`ILIKE`, con `%` y `_` escapados para que se traten como literales). `party` exige coincidencia exacta, sin distinguir mayúsculas, porque el partido es una categoría: `party=Patria` no debe devolver `Patria Milagro`.

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

### Datos de demostración cargados automáticamente

- **Contexto:** con la base vacía, quien evalúa tiene que crear votantes, candidatos y votos a mano antes de ver algo útil en las estadísticas.
- **Decisión:** un servicio `seed` en Compose ejecuta `scripts/seed_demo.py` cuando la API está sana (healthcheck propio de `api`). El script usa la API y no SQL directo, de modo que los datos pasan por las mismas reglas que cualquier cliente. Es idempotente: si el email ya existe reutiliza a la persona, y si el votante ya votó omite el voto. Se puede repetir con `docker compose up seed`.

### Fin de línea LF en el repositorio

- **Decisión:** `.gitattributes` con `eol=lf`, para que los ficheros montados en el contenedor (`schema.sql`) y el `Dockerfile` no cambien al clonar en Windows con `core.autocrlf`.
