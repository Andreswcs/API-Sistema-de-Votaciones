from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Candidate, Vote
from tests.helpers import create_candidate, create_voter


def vote(client: TestClient, voter_id: int, candidate_id: int) -> None:
    response = client.post("/votes", json={"voter_id": voter_id, "candidate_id": candidate_id})
    assert response.status_code == 201, response.text


def test_statistics_without_votes(client: TestClient) -> None:
    create_voter(client)
    candidate = create_candidate(client)

    response = client.get("/votes/statistics")

    assert response.status_code == 200
    assert response.json() == {
        "total_votes": 0,
        "total_voters_who_voted": 0,
        "candidates": [
            {
                "candidate_id": candidate["id"],
                "name": "Luis",
                "party": "Partido Azul",
                "votes": 0,
                "percentage": 0.0,
            }
        ],
    }


def test_statistics_without_candidates(client: TestClient) -> None:
    response = client.get("/votes/statistics")

    assert response.json() == {"total_votes": 0, "total_voters_who_voted": 0, "candidates": []}


def test_statistics_totals_percentages_and_order(client: TestClient) -> None:
    voters = [create_voter(client, name=f"V{i}", email=f"v{i}@mail.com") for i in range(4)]
    luis = create_candidate(client, name="Luis", email="luis@mail.com", party="Partido Azul")
    marta = create_candidate(client, name="Marta", email="marta@mail.com", party=None)
    pablo = create_candidate(client, name="Pablo", email="pablo@mail.com", party="Partido Verde")
    vote(client, voters[0]["id"], marta["id"])
    vote(client, voters[1]["id"], luis["id"])
    vote(client, voters[2]["id"], luis["id"])

    body = client.get("/votes/statistics").json()

    assert body["total_votes"] == 3
    assert body["total_voters_who_voted"] == 3
    assert body["candidates"] == [
        {"candidate_id": luis["id"], "name": "Luis", "party": "Partido Azul", "votes": 2, "percentage": 66.67},
        {"candidate_id": marta["id"], "name": "Marta", "party": None, "votes": 1, "percentage": 33.33},
        {"candidate_id": pablo["id"], "name": "Pablo", "party": "Partido Verde", "votes": 0, "percentage": 0.0},
    ]


def test_statistics_ties_are_ordered_by_name(client: TestClient) -> None:
    voters = [create_voter(client, name=f"V{i}", email=f"v{i}@mail.com") for i in range(2)]
    zoe = create_candidate(client, name="Zoe", email="zoe@mail.com")
    ana = create_candidate(client, name="Ana", email="ana@mail.com")
    vote(client, voters[0]["id"], zoe["id"])
    vote(client, voters[1]["id"], ana["id"])

    names = [row["name"] for row in client.get("/votes/statistics").json()["candidates"]]

    assert names == ["Ana", "Zoe"]


def test_candidate_vote_counter_matches_votes_table(client: TestClient, db_session: Session) -> None:
    voters = [create_voter(client, name=f"V{i}", email=f"v{i}@mail.com") for i in range(5)]
    candidates = [create_candidate(client, name=f"C{i}", email=f"c{i}@mail.com") for i in range(3)]
    for index, voter in enumerate(voters):
        vote(client, voter["id"], candidates[index % 2]["id"])

    counted = dict(
        db_session.execute(
            select(Candidate.person_id, func.count(Vote.id))
            .outerjoin(Vote, Vote.candidate_id == Candidate.person_id)
            .group_by(Candidate.person_id)
        ).all()
    )
    stored = dict(db_session.execute(select(Candidate.person_id, Candidate.votes)).all())
    statistics = client.get("/votes/statistics").json()["candidates"]

    assert stored == counted
    assert {row["candidate_id"]: row["votes"] for row in statistics} == counted
