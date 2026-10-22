from fastapi.testclient import TestClient


def create_voter(
    client: TestClient, name: str = "Pepito Pérez", email: str = "pepito.perez@correo.co"
) -> dict:
    response = client.post("/voters", json={"name": name, "email": email})
    assert response.status_code == 201, response.text
    return response.json()


def create_candidate(
    client: TestClient,
    name: str = "Samuelito",
    email: str = "samu@correo.co",
    party: str | None = "Patria Milagro",
) -> dict:
    response = client.post("/candidates", json={"name": name, "email": email, "party": party})
    assert response.status_code == 201, response.text
    return response.json()
