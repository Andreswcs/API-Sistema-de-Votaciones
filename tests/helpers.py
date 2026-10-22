from fastapi.testclient import TestClient


def create_voter(client: TestClient, name: str = "Ana", email: str = "ana@mail.com") -> dict:
    response = client.post("/voters", json={"name": name, "email": email})
    assert response.status_code == 201, response.text
    return response.json()


def create_candidate(
    client: TestClient,
    name: str = "Luis",
    email: str = "luis@mail.com",
    party: str | None = "Partido Azul",
) -> dict:
    response = client.post("/candidates", json={"name": name, "email": email, "party": party})
    assert response.status_code == 201, response.text
    return response.json()
