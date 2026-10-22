"""Carga datos de demostración a través de la API e imprime las estadísticas.

Uso: python scripts/seed_demo.py [URL_BASE]   (por defecto http://localhost:8000)
Se puede ejecutar varias veces: reutiliza las personas existentes y omite los votos repetidos.
"""

import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"

VOTERS = [
    ("Ana Gómez", "ana@demo.com"),
    ("Beto Ruiz", "beto@demo.com"),
    ("Carla Díaz", "carla@demo.com"),
    ("Diego Torres", "diego@demo.com"),
    ("Elena Vargas", "elena@demo.com"),
    ("Fernando Ríos", "fernando@demo.com"),
]
CANDIDATES = [
    ("Luis Martínez", "luis@demo.com", "Partido Azul"),
    ("Marta López", "marta@demo.com", None),
    ("Pablo Herrera", "pablo@demo.com", "Partido Verde"),
]
# Fernando no vota, y Pablo no recibe votos: así se ven ambos casos en las estadísticas.
VOTES = [
    ("ana@demo.com", "luis@demo.com"),
    ("beto@demo.com", "luis@demo.com"),
    ("carla@demo.com", "luis@demo.com"),
    ("diego@demo.com", "marta@demo.com"),
    ("elena@demo.com", "marta@demo.com"),
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
