from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Candidate, Vote
from tests.helpers import create_candidate, create_voter


def vote(client: TestClient, voter_id: int, candidate_id: int) -> None:
    response = client.post("/votes", json={"voter_id": voter_id, "candidate_id": candidate_id})
    assert response.status_code == 201, response.text


def create_voters(client: TestClient) -> list[dict]:
    return [
        create_voter(client, name="Pepito Pérez", email="pepito.perez@correo.co"),
        create_voter(client, name="Tengo Sueño", email="tengo.sueno@correo.co"),
        create_voter(client, name="Leidy", email="leidy@correo.co"),
    ]


def statistics_of(candidate: dict) -> dict:
    return {"candidate_id": candidate["id"], "name": candidate["name"], "party": candidate["party"]}


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
                "name": "Samuelito",
                "party": "Patria Milagro",
                "votes": 0,
                "percentage": 0.0,
            }
        ],
    }


def test_statistics_without_candidates(client: TestClient) -> None:
    response = client.get("/votes/statistics")

    assert response.json() == {"total_votes": 0, "total_voters_who_voted": 0, "candidates": []}


def test_statistics_totals_percentages_and_order(client: TestClient) -> None:
    pepito, tengo_sueno, leidy = create_voters(client)
    samuelito = create_candidate(client)
    monica = create_candidate(client, name="Mónica", email="monica@correo.co", party=None)
    adriana = create_candidate(client, name="Adriana", email="adriana@correo.co", party="Petroleo")
    vote(client, pepito["id"], monica["id"])
    vote(client, tengo_sueno["id"], samuelito["id"])
    vote(client, leidy["id"], samuelito["id"])

    body = client.get("/votes/statistics").json()

    assert body["total_votes"] == 3
    assert body["total_voters_who_voted"] == 3
    assert body["candidates"] == [
        {**statistics_of(samuelito), "votes": 2, "percentage": 66.67},
        {**statistics_of(monica), "votes": 1, "percentage": 33.33},
        {**statistics_of(adriana), "votes": 0, "percentage": 0.0},
    ]


def test_statistics_ties_are_ordered_by_name(client: TestClient) -> None:
    pepito, leidy, _ = create_voters(client)
    monica = create_candidate(client, name="Mónica", email="monica@correo.co")
    adriana = create_candidate(client, name="Adriana", email="adriana@correo.co")
    vote(client, pepito["id"], monica["id"])
    vote(client, leidy["id"], adriana["id"])

    names = [row["name"] for row in client.get("/votes/statistics").json()["candidates"]]

    assert names == ["Adriana", "Mónica"]


def test_candidate_vote_counter_matches_votes_table(
    client: TestClient, db_session: Session
) -> None:
    voters = [
        create_voter(client, name=f"Votante {i}", email=f"votante{i}@correo.co") for i in range(5)
    ]
    candidates = [
        create_candidate(client, name=f"Candidato {i}", email=f"candidato{i}@correo.co")
        for i in range(3)
    ]
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
