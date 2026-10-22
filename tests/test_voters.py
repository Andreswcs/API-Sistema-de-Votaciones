from fastapi.testclient import TestClient

from tests.helpers import create_voter


def test_create_voter(client: TestClient) -> None:
    response = client.post("/voters", json={"name": "  Ana  ", "email": "ana@mail.com"})

    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Ana", "email": "ana@mail.com", "has_voted": False}


def test_create_voter_normalizes_email(client: TestClient) -> None:
    voter = create_voter(client, email="  Ana.Perez@Mail.COM ")

    assert voter["email"] == "ana.perez@mail.com"


def test_create_voter_with_duplicate_email_returns_409(client: TestClient) -> None:
    create_voter(client)

    response = client.post("/voters", json={"name": "Otra Ana", "email": "ANA@mail.com"})

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_create_voter_with_invalid_data_returns_422(client: TestClient) -> None:
    assert client.post("/voters", json={"name": "Ana", "email": "no-es-email"}).status_code == 422
    assert client.post("/voters", json={"name": "   ", "email": "ana@mail.com"}).status_code == 422
    too_long = {"name": "A" * 101, "email": "ana@mail.com"}
    assert client.post("/voters", json=too_long).status_code == 422
    assert client.post("/voters", json={"email": "ana@mail.com"}).status_code == 422


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
    ana = create_voter(client)
    luis = create_voter(client, name="Luis", email="luis@mail.com")

    response = client.get("/voters")

    assert response.status_code == 200
    assert response.json() == [ana, luis]


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
