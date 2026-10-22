from fastapi.testclient import TestClient

from tests.helpers import create_voter


def test_create_voter(client: TestClient) -> None:
    payload = {"name": "  Pepito Pérez  ", "email": "pepito.perez@correo.co"}

    response = client.post("/voters", json=payload)

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "Pepito Pérez",
        "email": "pepito.perez@correo.co",
        "has_voted": False,
    }


def test_create_voter_normalizes_email(client: TestClient) -> None:
    voter = create_voter(client, email="  Pepito.Perez@Correo.CO ")

    assert voter["email"] == "pepito.perez@correo.co"


def test_create_voter_with_duplicate_email_returns_409(client: TestClient) -> None:
    create_voter(client)

    payload = {"name": "Otro Pepito", "email": "PEPITO.PEREZ@correo.co"}
    response = client.post("/voters", json=payload)

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_create_voter_with_invalid_data_returns_422(client: TestClient) -> None:
    email = "pepito.perez@correo.co"
    assert client.post("/voters", json={"name": "Pepito", "email": "mal"}).status_code == 422
    assert client.post("/voters", json={"name": "   ", "email": email}).status_code == 422
    assert client.post("/voters", json={"name": "A" * 101, "email": email}).status_code == 422
    assert client.post("/voters", json={"email": email}).status_code == 422


def test_get_voter(client: TestClient) -> None:
    voter = create_voter(client)

    response = client.get(f"/voters/{voter['id']}")

    assert response.status_code == 200
    assert response.json() == voter


def test_get_missing_voter_returns_404(client: TestClient) -> None:
    response = client.get("/voters/999")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_list_voters(client: TestClient) -> None:
    pepito = create_voter(client)
    leidy = create_voter(client, name="Leidy", email="leidy@correo.co")

    response = client.get("/voters")

    assert response.status_code == 200
    assert response.json() == [pepito, leidy]


def test_delete_voter(client: TestClient) -> None:
    voter = create_voter(client)

    response = client.delete(f"/voters/{voter['id']}")

    assert response.status_code == 204
    assert client.get(f"/voters/{voter['id']}").status_code == 404


def test_delete_voter_frees_email(client: TestClient) -> None:
    voter = create_voter(client)
    client.delete(f"/voters/{voter['id']}")

    create_voter(client)


def test_delete_missing_voter_returns_404(client: TestClient) -> None:
    assert client.delete("/voters/999").status_code == 404
