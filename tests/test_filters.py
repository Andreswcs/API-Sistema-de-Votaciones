import pytest
from fastapi.testclient import TestClient

from tests.helpers import create_candidate, create_voter


def names(response_json: list[dict]) -> list[str]:
    return [item["name"] for item in response_json]


@pytest.mark.parametrize("resource", ["/voters", "/candidates"])
def test_pagination(client: TestClient, resource: str) -> None:
    create = create_voter if resource == "/voters" else create_candidate
    for index in range(5):
        create(client, name=f"P{index}", email=f"p{index}@mail.com")

    assert names(client.get(resource).json()) == ["P0", "P1", "P2", "P3", "P4"]
    assert names(client.get(resource, params={"limit": 2}).json()) == ["P0", "P1"]
    assert names(client.get(resource, params={"limit": 2, "offset": 3}).json()) == ["P3", "P4"]
    assert client.get(resource, params={"offset": 10}).json() == []


def test_default_limit_is_50(client: TestClient) -> None:
    for index in range(55):
        create_voter(client, name=f"V{index}", email=f"v{index}@mail.com")

    assert len(client.get("/voters").json()) == 50
    assert len(client.get("/voters", params={"limit": 100}).json()) == 55


@pytest.mark.parametrize("resource", ["/voters", "/candidates"])
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "x"}])
def test_invalid_pagination_returns_422(client: TestClient, resource: str, params: dict) -> None:
    assert client.get(resource, params=params).status_code == 422


def test_filter_voters_by_has_voted(client: TestClient) -> None:
    ana = create_voter(client)
    create_voter(client, name="Beto", email="beto@mail.com")
    candidate = create_candidate(client)
    client.post("/votes", json={"voter_id": ana["id"], "candidate_id": candidate["id"]})

    assert names(client.get("/voters", params={"has_voted": True}).json()) == ["Ana"]
    assert names(client.get("/voters", params={"has_voted": False}).json()) == ["Beto"]


def test_filter_voters_by_partial_name_ignoring_case(client: TestClient) -> None:
    create_voter(client, name="Ana María", email="ana@mail.com")
    create_voter(client, name="Mariana", email="mariana@mail.com")
    create_voter(client, name="Beto", email="beto@mail.com")

    assert names(client.get("/voters", params={"name": "MARÍA"}).json()) == ["Ana María"]
    assert names(client.get("/voters", params={"name": "ana"}).json()) == ["Ana María", "Mariana"]


def test_name_filter_treats_wildcards_literally(client: TestClient) -> None:
    create_voter(client, name="Ana", email="ana@mail.com")

    assert client.get("/voters", params={"name": "%"}).json() == []
    assert client.get("/voters", params={"name": "_"}).json() == []


def test_filter_candidates_by_party_and_name(client: TestClient) -> None:
    create_candidate(client, name="Luis", email="luis@mail.com", party="Partido Azul")
    create_candidate(client, name="Lucía", email="lucia@mail.com", party="Partido Verde")
    create_candidate(client, name="Marta", email="marta@mail.com", party=None)

    assert names(client.get("/candidates", params={"party": "partido azul"}).json()) == ["Luis"]
    assert client.get("/candidates", params={"party": "Partido"}).json() == []
    assert names(client.get("/candidates", params={"name": "lu"}).json()) == ["Luis", "Lucía"]
    assert (
        names(client.get("/candidates", params={"name": "lu", "party": "Partido Verde"}).json())
        == ["Lucía"]
    )
