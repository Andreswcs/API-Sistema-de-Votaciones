from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Person, Voter
from app.models.constants import VOTER_ROLE


def create(session: Session, name: str, email: str) -> Voter:
    voter = Voter(person=Person(name=name, email=email, role=VOTER_ROLE))
    session.add(voter)
    session.flush()
    return voter


def get_by_id(session: Session, voter_id: int) -> Voter | None:
    return session.get(Voter, voter_id)


def list_all(session: Session) -> list[Voter]:
    return list(session.scalars(select(Voter).order_by(Voter.person_id)))


def delete(session: Session, voter: Voter) -> None:
    person = voter.person
    session.delete(voter)
    session.flush()
    session.delete(person)
    session.flush()
