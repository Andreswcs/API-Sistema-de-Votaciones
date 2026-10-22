from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, Person
from app.models.constants import CANDIDATE_ROLE


def create(session: Session, name: str, email: str, party: str | None) -> Candidate:
    candidate = Candidate(person=Person(name=name, email=email, role=CANDIDATE_ROLE), party=party)
    session.add(candidate)
    session.flush()
    return candidate


def get_by_id(session: Session, candidate_id: int) -> Candidate | None:
    return session.get(Candidate, candidate_id)


def list_all(session: Session) -> list[Candidate]:
    return list(session.scalars(select(Candidate).order_by(Candidate.person_id)))


def delete(session: Session, candidate: Candidate) -> None:
    person = candidate.person
    session.delete(candidate)
    session.flush()
    session.delete(person)
    session.flush()
