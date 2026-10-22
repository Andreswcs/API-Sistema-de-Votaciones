from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import AlreadyVotedError
from app.models import Candidate, Vote, Voter
from app.services import vote_service
from tests.helpers import create_candidate, create_voter


def post_vote(client: TestClient, voter_id: int, candidate_id: int) -> Response:
    return client.post("/votes", json={"voter_id": voter_id, "candidate_id": candidate_id})


def cast_vote(client: TestClient, voter_id: int, candidate_id: int) -> dict:
    response = post_vote(client, voter_id, candidate_id)
    assert response.status_code == 201, response.text
    return response.json()


def count_votes(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Vote)) or 0


def test_cast_vote(client: TestClient) -> None:
    voter = create_voter(client)
    candidate = create_candidate(client)

    response = post_vote(client, voter["id"], candidate["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["voter_id"] == voter["id"]
    assert body["candidate_id"] == candidate["id"]
    assert {"id", "created_at"} <= body.keys()
    assert client.get(f"/voters/{voter['id']}").json()["has_voted"] is True
    assert client.get(f"/candidates/{candidate['id']}").json()["votes"] == 1


def test_double_vote_returns_409(client: TestClient) -> None:
    voter = create_voter(client)
    candidate = create_candidate(client)
    cast_vote(client, voter["id"], candidate["id"])

    response = post_vote(client, voter["id"], candidate["id"])

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_VOTED"
    assert client.get(f"/candidates/{candidate['id']}").json()["votes"] == 1


def test_vote_with_missing_voter_returns_404(client: TestClient, db_session: Session) -> None:
    candidate = create_candidate(client)

    response = client.post("/votes", json={"voter_id": 999, "candidate_id": candidate["id"]})

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert count_votes(db_session) == 0


def test_vote_with_missing_candidate_returns_404(client: TestClient, db_session: Session) -> None:
    voter = create_voter(client)

    response = client.post("/votes", json={"voter_id": voter["id"], "candidate_id": 999})

    assert response.status_code == 404
    assert client.get(f"/voters/{voter['id']}").json()["has_voted"] is False
    assert count_votes(db_session) == 0


def test_candidate_cannot_vote(client: TestClient) -> None:
    candidate = create_candidate(client)

    response = post_vote(client, candidate["id"], candidate["id"])

    assert response.status_code == 404


def test_vote_with_invalid_payload_returns_422(client: TestClient) -> None:
    assert client.post("/votes", json={"voter_id": "uno", "candidate_id": 1}).status_code == 422
    assert client.post("/votes", json={"voter_id": 1}).status_code == 422


def test_failed_vote_leaves_no_partial_effects(client: TestClient, db_session: Session) -> None:
    voter = create_voter(client)
    candidate = create_candidate(client)
    # Estado incoherente provocado a propósito: el INSERT en votes funciona,
    # pero el UPDATE condicional falla y debe deshacerlo todo.
    db_session.execute(update(Voter).values(has_voted=True))
    db_session.commit()

    response = post_vote(client, voter["id"], candidate["id"])

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_VOTED"
    assert count_votes(db_session) == 0
    assert client.get(f"/candidates/{candidate['id']}").json()["votes"] == 0


def test_concurrent_votes_from_same_voter_register_exactly_one(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    voter = create_voter(client)
    candidates = [
        create_candidate(client),
        create_candidate(client, name="Adriana", email="adriana@correo.co", party="Petroleo"),
    ]
    attempts = 8
    barrier = Barrier(attempts)

    def attempt(index: int) -> str:
        candidate_id = candidates[index % 2]["id"]
        with session_factory() as session:
            barrier.wait()
            try:
                vote_service.cast_vote(session, voter["id"], candidate_id)
            except AlreadyVotedError:
                return "rejected"
            return "accepted"

    with ThreadPoolExecutor(max_workers=attempts) as executor:
        outcomes = list(executor.map(attempt, range(attempts)))

    assert outcomes.count("accepted") == 1
    assert outcomes.count("rejected") == attempts - 1
    with session_factory() as session:
        assert count_votes(session) == 1
        assert session.scalar(select(func.sum(Candidate.votes))) == 1


def test_list_votes(client: TestClient) -> None:
    pepito = create_voter(client)
    leidy = create_voter(client, name="Leidy", email="leidy@correo.co")
    candidate = create_candidate(client)
    first = cast_vote(client, pepito["id"], candidate["id"])
    second = cast_vote(client, leidy["id"], candidate["id"])

    response = client.get("/votes")

    assert response.status_code == 200
    assert response.json() == [first, second]


def test_delete_voter_who_voted_returns_409(client: TestClient) -> None:
    voter = create_voter(client)
    candidate = create_candidate(client)
    cast_vote(client, voter["id"], candidate["id"])

    response = client.delete(f"/voters/{voter['id']}")

    assert response.status_code == 409
    assert response.json()["code"] == "RESOURCE_IN_USE"
    assert client.get(f"/voters/{voter['id']}").status_code == 200


def test_delete_candidate_with_votes_returns_409(client: TestClient) -> None:
    voter = create_voter(client)
    candidate = create_candidate(client)
    cast_vote(client, voter["id"], candidate["id"])

    response = client.delete(f"/candidates/{candidate['id']}")

    assert response.status_code == 409
    assert response.json()["code"] == "RESOURCE_IN_USE"
    assert client.get(f"/candidates/{candidate['id']}").status_code == 200
