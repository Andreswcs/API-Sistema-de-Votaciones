# Sistema de Votaciones

Una API para gestionar una votación: registrar a las personas que votan (votantes) y a quienes se presentan (candidatos), recibir los votos y consultar quién va ganando.

El sistema cuida las reglas básicas de una elección:

- Cada votante puede votar **una sola vez**.
- Nadie puede ser votante y candidato al mismo tiempo.
- No se puede borrar a alguien que ya votó ni a un candidato que ya tiene votos.

Está hecha con Python (FastAPI) y una base de datos PostgreSQL, y todo se ejecuta dentro de Docker.

## Requerimientos

Solo **Docker Desktop** instalado y abierto. No hace falta instalar Python, ni la base de datos, ni configurar nada más, very easy 

## Cómo ejecutarlo

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
docker compose up --build
```

La primera vez tarda un poco, porque descarga y prepara todo. Cuando termine, ya puedes usarlo:

- **<http://localhost:8000/docs>**: una página web donde ves todas las operaciones de la API y puedes probarlas con el botón *Try it out*, sin escribir código.
- **<http://localhost:8000/health>**: si responde `{"status":"ok"}`, la API está funcionando.

Para pararlo, pulsa `Ctrl + C` en la terminal. Si prefieres que se ejecute en segundo plano, añade `-d`: `docker compose up --build -d`.

## Datos de ejemplo

Al arrancar, el sistema **carga solo unos datos de ejemplo**, para que no lo encuentres vacío:

- **12 votantes**: Pepito Pérez, Tengo Sueño, Leidy, Mónica, Brayan Stiven, Yuliana, Kevin Andrés, Marleny, Wilmer, Luz Dary, Ferney y Dayana.
- **4 candidatos**: Samuelito y Andrés Salinas (partido *Patria Milagro*), Adriana (partido *Petroleo*) y Jhon Fredy (sin partido).
- **10 votos**. Mónica y Ferney todavía no han votado.

Si arrancas varias veces, los datos no se duplican: lo que ya existe se deja como está.

Así se ven los resultados en <http://localhost:8000/votes/statistics>:

Los candidatos aparecen de más a menos votos. Si dos empatan, se ordenan por nombre. Los porcentajes se calculan sobre el total de votos.

Los datos de ejemplo están en [`scripts/seed_demo.py`](scripts/seed_demo.py). Si quiere cambiarlos, edita ese archivo y reinicia desde cero (ver más abajo).

### Capturas

| Página de pruebas (Swagger) | Estadísticas |
|---|---|
| ![Swagger](docs/img/swagger.png) | ![Estadísticas](docs/img/estadisticas.png) |

## Qué se puede hacer

| Acción | Operación |
|---|---|
| Registrar un votante (nombre y email) | `POST /voters` |
| Ver votantes (con filtros por nombre y por si ya votó) | `GET /voters` |
| Ver un votante | `GET /voters/{id}` |
| Borrar un votante (solo si no ha votado) | `DELETE /voters/{id}` |
| Registrar un candidato (nombre, email y partido opcional) | `POST /candidates` |
| Ver candidatos (con filtros por nombre y partido) | `GET /candidates` |
| Ver un candidato | `GET /candidates/{id}` |
| Borrar un candidato (solo si no tiene votos) | `DELETE /candidates/{id}` |
| Votar | `POST /votes` |
| Ver todos los votos | `GET /votes` |
| Ver los resultados | `GET /votes/statistics` |

Las listas muestran 50 resultados por defecto. Puedes pedir más (hasta 100) con `limit` y saltar resultados con `offset`.

Cuando algo no se puede hacer, la API lo explica con un mensaje y un código fijo. Por ejemplo, si un votante intenta votar dos veces:

```json
{"detail": "El votante 1 ya ha votado", "code": "ALREADY_VOTED"}
```

## Parar, reiniciar y empezar de cero

Todos los comandos se ejecutan en una terminal abierta en la carpeta del proyecto.

### Empezar completamente de cero

Usa esto si quieres borrar todo lo que has hecho y volver al estado inicial:

```bash
docker compose down -v
docker compose up --build
```

- `docker compose down -v` apaga todo y **borra la base de datos con todos sus datos**. La `-v` es la que borra los datos; sin ella se conservan.
- `docker compose up --build` vuelve a prepararlo todo: crea la base vacía, arranca la API y carga otra vez los datos de ejemplo.

## Pruebas automáticas (tests)

El proyecto incluye 60 pruebas que comprueban que todo funcionaaaaaaaaa.

Para ejecutarlas necesitas Python 3.12. En PowerShell:

```powershell
docker compose up -d db
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

## Trabajar en el código sin Docker para la API

Si vas a modificar el código y quieres ver los cambios al instante, deja solo la base de datos en Docker y ejecuta la API en tu equipo (con el entorno de Python activado como en el apartado anterior):

```powershell
docker compose up -d db
docker compose stop api
uvicorn app.main:app --reload
```

La configuración (usuario, contraseña y nombre de la base de datos) funciona sin tocar nada. Si necesitas cambiarla, copia [`.env.example`](.env.example) como `.env` y edita los valores.

## Cómo está construido y por qué

Esta guía es un resumen. La explicación completa está en dos documentos:

- **[`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)** explica cómo está organizado el código, cómo es la base de datos (con diagramas), qué pasa paso a paso cuando alguien vota y cómo se manejan los errores.
- **[`docs/DECISIONES.md`](docs/DECISIONES.md)** recoge cada decisión de diseño importante, por qué se tomó y qué alternativa se descartó.

Las ideas principales:

- **Una persona, un rol.** Votantes y candidatos comparten una tabla de personas con email único. La propia base de datos impide que alguien se registre dos veces o tenga los dos roles. Por eso los números de id se comparten: si el 13 es un candidato, no existe un votante 13.
- **El voto es todo o nada.** Guardar el voto, marcar al votante como "ya votó" y sumar el voto al candidato ocurre de una sola vez. Si algo falla, no se guarda nada.
- **A prueba de votos simultáneos.** Si llegan dos votos del mismo votante al mismo tiempo, la base de datos solo acepta uno.
- **Resultados fiables.** Las estadísticas se calculan contando los votos reales, no a partir de un contador que podría desajustarse.
- **El email se guarda en minúsculas**, para que `Pepito@Correo.co` y `pepito@correo.co` cuenten como la misma persona.

MUCHAS GRACIAS COMPAÑEROS DE NEW INNTECH
