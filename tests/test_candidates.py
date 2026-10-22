from fastapi.testclient import TestClient

from tests.helpers import create_candidate, create_voter


def test_create_candidate(client: TestClient) -> None:
    response = client.post(
        "/candidates", json={"name": " Luis ", "email": "Luis@Mail.com", "party": " Partido Azul "}
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "Luis",
        "email": "luis@mail.com",
        "party": "Partido Azul",
        "votes": 0,
    }


def test_create_candidate_without_party(client: TestClient) -> None:
    response = client.post("/candidates", json={"name": "Marta", "email": "marta@mail.com"})

    assert response.status_code == 201
    assert response.json()["party"] is None


def test_create_candidate_with_duplicate_email_returns_409(client: TestClient) -> None:
    create_candidate(client)

    response = client.post("/candidates", json={"name": "Otro", "email": "luis@mail.com"})

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_create_candidate_with_invalid_data_returns_422(client: TestClient) -> None:
    assert client.post("/candidates", json={"name": "Luis", "email": "mal"}).status_code == 422
    assert (
        client.post(
            "/candidates", json={"name": "Luis", "email": "luis@mail.com", "party": "P" * 101}
        ).status_code
        == 422
    )


def test_candidate_cannot_use_voter_email(client: TestClient) -> None:
    create_voter(client, email="ana@mail.com")

    response = client.post("/candidates", json={"name": "Ana", "email": "ana@mail.com"})

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_voter_cannot_use_candidate_email(client: TestClient) -> None:
    create_candidate(client, email="luis@mail.com")

    response = client.post("/voters", json={"name": "Luis", "email": "luis@mail.com"})

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
    luis = create_candidate(client)
    marta = create_candidate(client, name="Marta", email="marta@mail.com", party=None)

    response = client.get("/candidates")

    assert response.status_code == 200
    assert response.json() == [luis, marta]


def test_delete_candidate_without_votes(client: TestClient) -> None:
    candidate = create_candidate(client)

    response = client.delete(f"/candidates/{candidate['id']}")

    assert response.status_code == 204
    assert client.get(f"/candidates/{candidate['id']}").status_code == 404


def test_delete_missing_candidate_returns_404(client: TestClient) -> None:
    assert client.delete("/candidates/999").status_code == 404
