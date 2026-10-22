# Sistema de Votaciones — Instrucciones para el agente

API RESTful para gestionar votantes, candidatos y votos, con estadísticas de resultados. Es una prueba técnica de 1 día: el resultado debe funcionar a la primera, estar bien organizado y ser fácil de ejecutar para quien lo evalúe.

Lee este archivo completo antes de escribir código. Es la fuente de verdad del proyecto.

---

## 1. Nivel de complejidad

**Media-baja.** No hay lógica de negocio exótica; la dificultad está en hacer bien tres cosas:

| Componente | Complejidad | Por qué |
|---|---|---|
| CRUD de votantes y candidatos | Baja | Patrón repetitivo, pero cada alta toca dos tablas (`persons` + rol) |
| Esquema con FK compuesta | Media | Garantiza en la base de datos que nadie sea votante y candidato a la vez |
| Emisión de voto | **Media-alta** | Una transacción atómica con tres escrituras y protección ante concurrencia |
| Estadísticas | Baja-media | Agregación con `LEFT JOIN`, porcentajes y caso de cero votos |
| Docker + arranque sin pasos manuales | Media | Es lo que más suele fallar al evaluar: "en mi máquina funciona" |

**Regla de oro: simplicidad.** Resuelve exactamente lo pedido, con la estructura más simple que se pueda defender. Nada de sobreingeniería.

---

## 2. Entorno y contexto del usuario

- El usuario trabaja en **Windows con PowerShell y Docker Desktop**. Todo comando que documentes o ejecutes debe funcionar ahí. No dependas de scripts `.sh`; usa Python para scripts auxiliares.
- Ya existen en el repo: `docker-compose.yml` (solo el servicio `db`, con las credenciales del usuario) y `schema.sql` (esquema PostgreSQL probado a mano).
- **Respeta las credenciales y valores que ya están en `docker-compose.yml`.** Amplíalo, no lo reescribas desde cero.
- `schema.sql` es la fuente de verdad del esquema. Muévelo a `db/schema.sql` y no cambies su estructura sin avisar y justificarlo. Si encuentras un error real en él, corrígelo y regístralo en `docs/DECISIONES.md`.
- El usuario quiere **aprender mientras avanza**: la documentación de arquitectura (sección 10) no es opcional.

---

## 3. Stack (fijo, no cambiar)

- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2.x con estilo moderno (`Mapped`, `mapped_column`), **síncrono** (no async)
- PostgreSQL 16 con `psycopg` 3 (`psycopg[binary]`)
- Pydantic v2, `pydantic-settings`, `email-validator`
- pytest + `httpx` (TestClient)
- Dependencias en `requirements.txt` y `requirements-dev.txt`, con versiones fijadas
- Entorno virtual en `.venv` (ya ignorado en git)

No añadas ORMs, frameworks, librerías de utilidades o herramientas que no estén aquí sin preguntar.

---

## 4. Arquitectura en capas

```
app/
  main.py                 # crea la app, registra routers y manejadores de errores
  core/
    config.py             # Settings desde variables de entorno
    database.py           # engine, sesión y dependencia get_db
    exceptions.py         # excepciones de dominio
    error_handlers.py     # traducción de excepciones a respuestas HTTP
  models/                 # SQLAlchemy: Person, Voter, Candidate, Vote
  schemas/                # Pydantic: contratos de entrada y salida
  repositories/           # acceso a datos
  services/               # reglas de negocio y transacciones
  api/routers/            # voters.py, candidates.py, votes.py, health.py
tests/
db/schema.sql
docs/
scripts/
```

### Responsabilidades y reglas de dependencia

Dirección permitida: `routers → services → repositories → models`. Nunca al revés.

| Capa | Hace | NO hace |
|---|---|---|
| Routers | Recibir HTTP, validar con schemas, elegir el código de estado | Reglas de negocio, consultas, `commit` |
| Schemas | Definir y validar los contratos | Acceder a la base de datos |
| Services | Reglas de negocio, orquestar repositories, **controlar la transacción** (commit/rollback) | Importar nada de FastAPI ni conocer HTTP |
| Repositories | Consultas e inserciones, usando la sesión recibida | Reglas de negocio ni `commit` (como mucho `flush`) |
| Models | Mapear tablas | Lógica |

- La sesión de base de datos se inyecta con `Depends` y se pasa a los services; no se crean sesiones globales.
- Los services lanzan **excepciones de dominio** (`AlreadyVotedError`, `EmailAlreadyRegisteredError`, `NotFoundError`, `ResourceInUseError`…) y los manejadores de `core/error_handlers.py` las convierten a HTTP. Los services no devuelven códigos de estado.
- Evita abstracciones genéricas (repositorio base, factorías, patrón unit-of-work formal) salvo que eliminen duplicación real y evidente.

---

## 5. Modelo de datos (ver `db/schema.sql`)

- `persons`: `id`, `name`, `email` (único, siempre en minúsculas), `role` (`VOTER` | `CANDIDATE`).
- `voters`: `person_id` (PK y FK), `role`, `has_voted`.
- `candidates`: `person_id` (PK y FK), `role`, `party` (opcional), `votes` (≥ 0).
- `votes`: `id`, `voter_id` (**UNIQUE**), `candidate_id`, `created_at`.
- `voters` y `candidates` referencian a `persons` mediante una **FK compuesta `(person_id, role)`** con `role` fijo por `CHECK`. Así una persona no puede ser votante y candidato a la vez, y el `UNIQUE` sobre `email` evita duplicados aunque lleguen peticiones simultáneas.
- Todas las FK son `ON DELETE RESTRICT`.
- Los modelos SQLAlchemy deben **reflejar fielmente** el esquema, incluidas la FK compuesta (`ForeignKeyConstraint`) y los `CHECK`.
- **No uses `create_all` para crear tablas.** El esquema lo crea `db/schema.sql` (ver sección 9).

Consecuencias que debes respetar:

- El `id` público de un votante o candidato es su `person_id`. Los ids se comparten entre ambos recursos: `GET /voters/2` devuelve 404 si la persona 2 es candidata.
- Crear un votante o candidato = insertar en `persons` y luego en su tabla de rol, **en una sola transacción**. Borrarlo = borrar primero de la tabla de rol y después de `persons`, también en una transacción.
- El email se normaliza (`strip` + minúsculas) **en el schema de entrada**. La base de datos lo rechaza si llega sin normalizar.

---

## 6. API

Todos los recursos viven bajo la raíz (sin prefijo de versión). Swagger en `/docs`.

### Contratos

| Recurso | Entrada (POST) | Salida |
|---|---|---|
| Votante | `{name, email}` | `{id, name, email, has_voted}` |
| Candidato | `{name, email, party?}` | `{id, name, email, party, votes}` |
| Voto | `{voter_id, candidate_id}` | `{id, voter_id, candidate_id, created_at}` |

- `name`: sin espacios sobrantes, 1 a 100 caracteres. `email`: válido, máximo 255. `party`: máximo 100, opcional.
- Las listas devuelven un **array JSON** y aceptan `limit` (por defecto 50, máximo 100) y `offset`. Votantes admiten filtros `has_voted` y `name` (coincidencia parcial, sin distinguir mayúsculas). Candidatos admiten `party` y `name`.

### Endpoints

| Método y ruta | Éxito | Errores |
|---|---|---|
| `POST /voters` | 201 | 409 email ya registrado (en cualquier rol), 422 datos inválidos |
| `GET /voters` | 200 | 422 parámetros inválidos |
| `GET /voters/{id}` | 200 | 404 |
| `DELETE /voters/{id}` | 204 | 404, 409 si ya votó |
| `POST /candidates` | 201 | 409, 422 |
| `GET /candidates` | 200 | 422 |
| `GET /candidates/{id}` | 200 | 404 |
| `DELETE /candidates/{id}` | 204 | 404, 409 si tiene votos |
| `POST /votes` | 201 | 404 votante o candidato inexistente, 409 votante ya votó, 422 |
| `GET /votes` | 200 | — |
| `GET /votes/statistics` | 200 | — |
| `GET /health` | 200 | — |

### Formato de errores

Los errores de dominio responden `{"detail": "<mensaje en español>", "code": "<CODIGO_ESTABLE>"}`, por ejemplo `ALREADY_VOTED`, `EMAIL_ALREADY_REGISTERED`, `NOT_FOUND`, `RESOURCE_IN_USE`. Los errores de validación de Pydantic (422) se dejan con el formato estándar de FastAPI. Los mensajes de la API van en español.

### Estadísticas (`GET /votes/statistics`)

```json
{
  "total_votes": 3,
  "total_voters_who_voted": 3,
  "candidates": [
    {"candidate_id": 4, "name": "Luis", "party": "Partido Azul", "votes": 2, "percentage": 66.67},
    {"candidate_id": 5, "name": "Marta", "party": null, "votes": 1, "percentage": 33.33},
    {"candidate_id": 6, "name": "Pablo", "party": "Partido Verde", "votes": 0, "percentage": 0.0}
  ]
}
```

- Se calculan **desde la tabla `votes`** (fuente de verdad) con un `LEFT JOIN` desde `candidates`, de modo que los candidatos sin votos aparecen con 0.
- `percentage` = votos del candidato / votos totales × 100, redondeado a 2 decimales. Con 0 votos totales, todos los porcentajes son `0.0` (sin división por cero).
- `total_voters_who_voted` = votantes con `has_voted = true`.
- Orden: votos descendente, luego nombre.

---

## 7. Emisión de voto (la parte crítica)

Todo ocurre en **una sola transacción**; si algo falla, no se guarda nada.

1. Comprobar que el votante existe (404 si no) y que el candidato existe (404 si no).
2. Insertar la fila en `votes`.
3. Marcar al votante con un `UPDATE` condicional (`... SET has_voted = true WHERE person_id = :id AND has_voted = false`). Si no afecta a ninguna fila, el votante ya había votado → `AlreadyVotedError`.
4. Incrementar al candidato con `UPDATE ... SET votes = votes + 1`. **Nunca** leer el valor, sumar en Python y guardar.

Protección ante concurrencia: el `UNIQUE` de `votes.voter_id` es la última barrera. Si salta un `IntegrityError`, tradúcelo según el **nombre de la restricción** (`diag.constraint_name` de psycopg), no analizando el texto del mensaje, y responde 409.

Aplica el mismo criterio a los borrados con `RESTRICT`: traduce el `IntegrityError` por nombre de restricción a un 409 `RESOURCE_IN_USE`.

---

## 8. Reglas de estilo de código

- Identificadores y nombres de archivos en **inglés**. Mensajes de la API y documentación en **español**.
- Tipado completo en funciones públicas. Nombres descriptivos que hagan innecesario el comentario.
- **Comentarios: solo donde la lógica sea compleja o confusa**, y explicando el *porqué*, no el *qué*. Prohibido narrar código obvio (`# crea la sesión`, `# devuelve el resultado`).
- Sin docstrings en funciones triviales. En services complejos, una línea es suficiente.
- Lugares donde un comentario breve **sí** está justificado: la FK compuesta en los modelos, el `UPDATE` condicional del voto, la traducción de `IntegrityError` por nombre de restricción y el cálculo de porcentajes.
- Sin código muerto, sin `print` de depuración, sin `TODO` sin resolver, sin imports sin usar.
- Funciones cortas con una responsabilidad. Si un router tiene lógica, está mal ubicada.
- Nada de valores mágicos repetidos: constantes con nombre para roles y nombres de restricciones.

---

## 9. Docker y arranque

Objetivo: quien evalúe solo necesita Docker y ejecuta:

```
git clone <repo>
cd <repo>
docker compose up --build
```

y abre `http://localhost:8000/docs`. **Cero pasos manuales** y sin crear un `.env`.

- `Dockerfile` en la raíz para la API: imagen de Python slim, instalar `requirements.txt` antes de copiar el código (aprovecha la caché), arrancar con `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- `docker-compose.yml` con dos servicios: `db` y `api`.
  - `db`: añadir `healthcheck` con `pg_isready`, y montar `db/schema.sql` en `/docker-entrypoint-initdb.d/` para que las tablas se creen solas al inicializar el volumen.
  - `api`: `depends_on` con `condition: service_healthy`; `DATABASE_URL` apuntando al host `db`.
  - Valores por defecto en el propio compose; si usas variables, con sintaxis `${VAR:-valor}`.
- Para los tests, la base `votaciones_test` se crea con un script de inicialización adicional en `db/init/`. Los fixtures de pytest aplican `db/schema.sql` sobre ella y limpian las tablas entre tests.
- Se mantiene el flujo de desarrollo local: `docker compose up -d db` + `uvicorn app.main:app --reload` desde la `.venv`, con `.env.example` documentando las variables.
- Nunca subas `.env` ni credenciales reales. `.gitignore` debe cubrir `.venv`, `.env`, `__pycache__`, `.pytest_cache`.
- Verificación obligatoria al final: `docker compose down -v` seguido de `docker compose up --build` desde cero, y comprobar `/health` y `/docs`.

---

## 10. Documentación (entregables)

**`README.md`** (para el evaluador, directo y corto):

1. Descripción del proyecto en dos líneas.
2. Requisitos: solo Docker.
3. Cómo ejecutar (el comando único) y URLs: `/docs` y `/health`.
4. Ejemplos de uso de cada endpoint con `curl`, indicando que en PowerShell se usa `curl.exe` y que Swagger sirve como alternativa.
5. Ejemplo de respuesta de estadísticas y sección para las capturas (`docs/img/`).
6. Cómo ejecutar los tests y cómo trabajar en local sin Docker para la API.
7. Decisiones de diseño y supuestos (resumen; detalle en `docs/DECISIONES.md`).
8. Mejoras futuras posibles (JWT, Alembic, etc.) en pocas líneas.

**`docs/ARQUITECTURA.md`** (para que el usuario estudie): capas y responsabilidades, regla de dependencias, modelo de datos con diagrama Mermaid, flujo de emisión de voto (diagrama de secuencia Mermaid), manejo de errores, y por qué cada decisión importante es la que es.

**`docs/DECISIONES.md`**: registro corto de decisiones (contexto, decisión, alternativa descartada). Debe incluir como mínimo: email obligatorio, tabla `persons` con rol y FK compuesta, `RESTRICT`, normalización a minúsculas, ids compartidos, estadísticas calculadas desde `votes`, esquema por script de inicio en lugar de `create_all`/Alembic, SQLAlchemy síncrono.

**`scripts/seed_demo.py`**: carga datos de demostración llamando a la API (votantes, candidatos y varios votos) e imprime las estadísticas, para que el usuario pueda tomar las capturas. Tú no puedes tomar capturas: deja el hueco indicado en el README y avísale.

---

## 11. Tests

pytest contra una base PostgreSQL real (no SQLite: el esquema usa FK compuestas y `CHECK` que deben probarse de verdad). Cada fase añade sus tests; no los dejes para el final.

Casos mínimos:

- **Votantes y candidatos:** alta correcta, email duplicado (409), email con mayúsculas normalizado, email inválido (422), consulta inexistente (404), borrado correcto, paginación y filtros.
- **Regla de roles:** registrar como candidato un email ya usado por un votante (409) y viceversa.
- **Votos:** voto correcto (verifica `has_voted = true` y `votes + 1`), doble voto (409), votante inexistente (404), candidato inexistente (404), y que un voto fallido **no** deja efectos parciales.
- **Concurrencia:** dos intentos simultáneos del mismo votante producen exactamente un voto.
- **Borrados protegidos:** votante que votó (409), candidato con votos (409), candidato sin votos (204).
- **Estadísticas:** totales y porcentajes correctos, caso de 0 votos, candidato sin votos incluido, y coherencia entre `candidates.votes` y el `COUNT` de `votes`.

---

## 12. Fases de trabajo

Trabaja en este orden. Al terminar cada fase: ejecuta los tests, haz un commit y deja un resumen de **máximo 5 líneas** con lo hecho y cualquier decisión tomada. No esperes aprobación entre fases, salvo que aparezca una duda que este documento no resuelva.

0. **Base:** estructura de carpetas, `.venv`, dependencias, `db/schema.sql`, configuración, sesión de BD, `GET /health`, `.gitignore`.
1. **Núcleo:** modelos, excepciones de dominio y manejadores de errores.
2. **Votantes:** CRUD completo atravesando todas las capas, con tests. Es la plantilla del resto.
3. **Candidatos:** CRUD con la regla de roles, con tests.
4. **Votos y estadísticas:** transacción de voto, concurrencia y estadísticas, con tests.
5. **Paginación y filtros** en votantes y candidatos.
6. **Docker:** `Dockerfile`, compose completo y verificación desde cero (sección 9).
7. **Documentación:** README, `docs/ARQUITECTURA.md`, `docs/DECISIONES.md` y `scripts/seed_demo.py`.
8. **Revisión final:** recorre la lista de la sección 14.

---

## 13. Reglas para el agente

**Haz:**

- Decide por tu cuenta lo que sea razonable y regístralo en `docs/DECISIONES.md`. Pregunta solo si algo contradice este documento o bloquea el avance.
- Commits pequeños y descriptivos, uno por unidad lógica de trabajo.
- Ejecuta el código y los tests antes de afirmar que algo funciona. Reporta lo que realmente ocurrió, incluidos los fallos.
- Si un test falla, arregla la causa. No modifiques ni borres el test para que pase sin explicar por qué.

**No hagas:**

- No hagas `git push` ni configures remotos. Solo commits locales.
- No implementes JWT/autenticación, Alembic ni funcionalidades extra no listadas, salvo que el usuario lo pida expresamente.
- No cambies el stack, la estructura de carpetas ni las decisiones de diseño de este documento sin avisar.
- No instales nada global. Todo dentro de `.venv` o de los contenedores.
- No ejecutes comandos destructivos fuera de este proyecto. `docker compose down -v` solo sobre este proyecto.
- No pongas secretos reales en el repositorio.
- No generes comentarios decorativos, banners ASCII ni documentación redundante.

---

## 14. Definición de terminado

- [ ] `docker compose down -v && docker compose up --build` deja la API funcionando sin pasos adicionales.
- [ ] `/health` responde y `/docs` muestra todos los endpoints con sus esquemas.
- [ ] Todos los endpoints de la sección 6 funcionan con los códigos de estado indicados.
- [ ] Los tests pasan, incluidos el de concurrencia y el de coherencia de estadísticas.
- [ ] Ninguna capa viola la regla de dependencias (revisa imports: los services no importan FastAPI, los routers no tocan la sesión ni hacen `commit`).
- [ ] No quedan comentarios innecesarios, código muerto ni `print`.
- [ ] README, `docs/ARQUITECTURA.md` y `docs/DECISIONES.md` completos y coherentes con el código real.
- [ ] `scripts/seed_demo.py` funciona y el README tiene el hueco para las capturas.
- [ ] El repositorio no contiene `.env`, `.venv` ni credenciales reales.
- [ ] Resumen final para el usuario: qué se hizo, qué decisiones tomaste, qué quedó fuera y qué debe hacer él (capturas, subir a GitHub).
