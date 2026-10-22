from fastapi.testclient import TestClient

from tests.helpers import create_candidate, create_voter


def test_create_candidate(client: TestClient) -> None:
    payload = {
        "name": "samuelito",
        "email": "samu@correo.co",
        "party": " Patria Milagro ",
    }

    response = client.post("/candidates", json=payload)

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "samuelito",
        "email": "samu@correo.co",
        "party": "Patria Milagro",
        "votes": 0,
    }


def test_create_candidate_without_party(client: TestClient) -> None:
    response = client.post("/candidates", json={"name": "Mónica", "email": "monica@correo.co"})

    assert response.status_code == 201
    assert response.json()["party"] is None


def test_create_candidate_with_duplicate_email_returns_409(client: TestClient) -> None:
    create_candidate(client)

    payload = {"name": "Otro Samuelito", "email": "samu@correo.co"}
    response = client.post("/candidates", json=payload)

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_create_candidate_with_invalid_data_returns_422(client: TestClient) -> None:
    name = "Samuelito"
    email = "samu@correo.co"
    assert client.post("/candidates", json={"name": name, "email": "mal"}).status_code == 422
    too_long_party = {"name": name, "email": email, "party": "P" * 101}
    assert client.post("/candidates", json=too_long_party).status_code == 422


def test_candidate_cannot_use_voter_email(client: TestClient) -> None:
    create_voter(client, email="pepito.perez@correo.co")

    payload = {"name": "Pepito Pérez", "email": "pepito.perez@correo.co"}
    response = client.post("/candidates", json=payload)

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_voter_cannot_use_candidate_email(client: TestClient) -> None:
    create_candidate(client, email="samu@correo.co")

    payload = {"name": "Samuelito", "email": "samu@correo.co"}
    response = client.post("/voters", json=payload)

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_ids_are_shared_between_voters_and_candidates(client: TestClient) -> None:
    voter = create_voter(client)
    candidate = create_candidate(client)

    assert client.get(f"/candidates/{voter['id']}").status_code == 404
    assert client.get(f"/voters/{candidate['id']}").status_code == 404
    assert client.delete(f"/voters/{candidate['id']}").status_code == 404


def test_get_candidate(client: TestClient) -> None:
    candidate = create_candidate(client)

    response = client.get(f"/candidates/{candidate['id']}")

    assert response.status_code == 200
    assert response.json() == candidate


def test_get_missing_candidate_returns_404(client: TestClient) -> None:
    response = client.get("/candidates/999")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_list_candidates(client: TestClient) -> None:
    samuelito = create_candidate(client)
    adriana = create_candidate(client, name="Adriana", email="adriana@correo.co", party="Petroleo")

    response = client.get("/candidates")

    assert response.status_code == 200
    assert response.json() == [samuelito, adriana]


def test_delete_candidate_without_votes(client: TestClient) -> None:
    candidate = create_candidate(client)

    response = client.delete(f"/candidates/{candidate['id']}")

    assert response.status_code == 204
    assert client.get(f"/candidates/{candidate['id']}").status_code == 404


def test_delete_missing_candidate_returns_404(client: TestClient) -> None:
    assert client.delete("/candidates/999").status_code == 404
