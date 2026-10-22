from sqlalchemy import func, select, update
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


def mark_as_voted(session: Session, voter_id: int) -> bool:
    # UPDATE condicional: la comprobación y la escritura son una sola sentencia atómica,
    # así dos transacciones no pueden ver has_voted = false a la vez y marcarlo ambas.
    result = session.execute(
        update(Voter)
        .where(Voter.person_id == voter_id, Voter.has_voted.is_(False))
        .values(has_voted=True)
    )
    return result.rowcount == 1


def count_who_voted(session: Session) -> int:
    query = select(func.count()).select_from(Voter).where(Voter.has_voted.is_(True))
    return session.scalar(query) or 0


def delete(session: Session, voter: Voter) -> None:
    person = voter.person
    session.delete(voter)
    session.flush()
    session.delete(person)
    session.flush()
