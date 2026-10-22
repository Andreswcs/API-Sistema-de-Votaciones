"""Carga datos de demostración a través de la API e imprime las estadísticas.

Docker Compose lo ejecuta automáticamente (servicio `seed`) cuando la API está lista.
Uso manual: python scripts/seed_demo.py [URL_BASE]   (por defecto http://localhost:8000)
Se puede ejecutar varias veces: reutiliza las personas existentes y omite los votos repetidos.
"""

import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"

VOTERS = [
    ("Pepito Pérez", "pepito.perez@correo.co"),
    ("Tengo Sueño", "tengo.sueno@correo.co"),
    ("Leidy", "leidy@correo.co"),
    ("Mónica", "monica@correo.co"),
    ("Brayan Stiven", "brayan.stiven@correo.co"),
    ("Yuliana", "yuliana@correo.co"),
    ("Kevin Andrés", "kevin.andres@correo.co"),
    ("Marleny", "marleny@correo.co"),
    ("Wilmer", "wilmer@correo.co"),
    ("Luz Dary", "luz.dary@correo.co"),
    ("Ferney", "ferney@correo.co"),
    ("Dayana", "dayana@correo.co"),
]
CANDIDATES = [
    ("Samuelito", "samu@correo.co", "Patria Milagro"),
    ("Adriana", "adriana@correo.co", "Petroleo"),
    ("Andrés Salinas", "andres.salinas@correo.co", "Patria Milagro"),
    ("Jhon Fredy", "jhon.fredy@correo.co", None),
]
# Mónica y Ferney no votan, Adriana y Andrés empatan y Jhon Fredy no recibe votos:
# así las estadísticas muestran todos los casos interesantes.
VOTES = [
    ("pepito.perez@correo.co", "samu@correo.co"),
    ("tengo.sueno@correo.co", "samu@correo.co"),
    ("brayan.stiven@correo.co", "samu@correo.co"),
    ("marleny@correo.co", "samu@correo.co"),
    ("leidy@correo.co", "adriana@correo.co"),
    ("yuliana@correo.co", "adriana@correo.co"),
    ("luz.dary@correo.co", "adriana@correo.co"),
    ("kevin.andres@correo.co", "andres.salinas@correo.co"),
    ("wilmer@correo.co", "andres.salinas@correo.co"),
    ("dayana@correo.co", "andres.salinas@correo.co"),
]


def call(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    request = Request(
        f"{BASE_URL}{path}", data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urlopen(request) as response:
            return response.status, json.loads(response.read() or b"null")
    except HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def get_or_create(resource: str, payload: dict) -> int:
    status, body = call("POST", f"/{resource}", payload)
    if status == 201:
        print(f"  creado id {body['id']}: {payload['name']}")
        return body["id"]
    if status == 409:
        _, existing = call("GET", f"/{resource}?limit=100")
        match = next(item for item in existing if item["email"] == payload["email"])
        print(f"  ya existía id {match['id']}: {payload['name']}")
        return match["id"]
    raise RuntimeError(f"POST /{resource} devolvió {status}: {body}")


def main() -> None:
    status, _ = call("GET", "/health")
    if status != 200:
        sys.exit(f"La API no responde en {BASE_URL}. ¿Está levantada con docker compose up?")

    print("Votantes:")
    voter_ids = {
        email: get_or_create("voters", {"name": name, "email": email}) for name, email in VOTERS
    }
    print("Candidatos:")
    candidate_ids = {
        email: get_or_create("candidates", {"name": name, "email": email, "party": party})
        for name, email, party in CANDIDATES
    }

    print("Votos:")
    for voter_email, candidate_email in VOTES:
        status, body = call(
            "POST",
            "/votes",
            {"voter_id": voter_ids[voter_email], "candidate_id": candidate_ids[candidate_email]},
        )
        print(f"  {voter_email} -> {candidate_email}: {status} {body.get('code', 'OK')}")

    _, statistics = call("GET", "/votes/statistics")
    print("\nEstadísticas:")
    print(json.dumps(statistics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
