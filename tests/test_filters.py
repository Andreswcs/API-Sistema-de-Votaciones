import pytest
from fastapi.testclient import TestClient

from tests.helpers import create_candidate, create_voter

PEOPLE = [
    ("Pepito Pérez", "pepito.perez@correo.co"),
    ("Andrés Salinas", "andres.salinas@correo.co"),
    ("Tengo Sueño", "tengo.sueno@correo.co"),
    ("Leidy", "leidy@correo.co"),
    ("Adriana", "adriana@correo.co"),
]


def names(response_json: list[dict]) -> list[str]:
    return [item["name"] for item in response_json]


@pytest.mark.parametrize("resource", ["/voters", "/candidates"])
def test_pagination(client: TestClient, resource: str) -> None:
    create = create_voter if resource == "/voters" else create_candidate
    for name, email in PEOPLE:
        create(client, name=name, email=email)
    all_names = [name for name, _ in PEOPLE]

    assert names(client.get(resource).json()) == all_names
    assert names(client.get(resource, params={"limit": 2}).json()) == all_names[:2]
    assert names(client.get(resource, params={"limit": 2, "offset": 3}).json()) == all_names[3:]
    assert client.get(resource, params={"offset": 10}).json() == []


def test_default_limit_is_50(client: TestClient) -> None:
    for index in range(55):
        create_voter(client, name=f"Votante {index}", email=f"votante{index}@correo.co")

    assert len(client.get("/voters").json()) == 50
    assert len(client.get("/voters", params={"limit": 100}).json()) == 55


@pytest.mark.parametrize("resource", ["/voters", "/candidates"])
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "x"}])
def test_invalid_pagination_returns_422(client: TestClient, resource: str, params: dict) -> None:
    assert client.get(resource, params=params).status_code == 422


def test_filter_voters_by_has_voted(client: TestClient) -> None:
    pepito = create_voter(client)
    create_voter(client, name="Tengo Sueño", email="tengo.sueno@correo.co")
    candidate = create_candidate(client)
    client.post("/votes", json={"voter_id": pepito["id"], "candidate_id": candidate["id"]})

    assert names(client.get("/voters", params={"has_voted": True}).json()) == ["Pepito Pérez"]
    assert names(client.get("/voters", params={"has_voted": False}).json()) == ["Tengo Sueño"]


def test_filter_voters_by_partial_name_ignoring_case(client: TestClient) -> None:
    create_voter(client, name="Pepito Pérez", email="pepito.perez@correo.co")
    create_voter(client, name="Adriana", email="adriana@correo.co")
    create_voter(client, name="Mónica", email="monica@correo.co")
    create_voter(client, name="Leidy", email="leidy@correo.co")

    assert names(client.get("/voters", params={"name": "PÉREZ"}).json()) == ["Pepito Pérez"]
    assert names(client.get("/voters", params={"name": "A"}).json()) == ["Adriana", "Mónica"]


def test_name_filter_treats_wildcards_literally(client: TestClient) -> None:
    create_voter(client)

    assert client.get("/voters", params={"name": "%"}).json() == []
    assert client.get("/voters", params={"name": "_"}).json() == []


def test_filter_candidates_by_party_and_name(client: TestClient) -> None:
    create_candidate(client)
    create_candidate(client, name="Adriana", email="adriana@correo.co", party="Petroleo")
    create_candidate(client, name="Mónica", email="monica@correo.co", party=None)

    def list_names(**params: str) -> list[str]:
        return names(client.get("/candidates", params=params).json())

    assert list_names(party="patria milagro") == ["Samuelito"]
    assert list_names(party="Patria") == []
    assert list_names(name="SAMU") == ["Samuelito"]
    assert list_names(name="a", party="Petroleo") == ["Adriana"]
