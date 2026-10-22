from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.models import Candidate, Person, Vote


def create(session: Session, voter_id: int, candidate_id: int) -> Vote:
    vote = Vote(voter_id=voter_id, candidate_id=candidate_id)
    session.add(vote)
    session.flush()
    return vote


def list_all(session: Session) -> list[Vote]:
    return list(session.scalars(select(Vote).order_by(Vote.id)))


def count_votes_per_candidate(session: Session) -> list[Row[tuple[int, str, str | None, int]]]:
    vote_count = func.count(Vote.id).label("votes")
    query = (
        select(Candidate.person_id, Person.name, Candidate.party, vote_count)
        .join(Person, Person.id == Candidate.person_id)
        .outerjoin(Vote, Vote.candidate_id == Candidate.person_id)
        .group_by(Candidate.person_id, Person.name, Candidate.party)
        .order_by(vote_count.desc(), Person.name)
    )
    return list(session.execute(query))
