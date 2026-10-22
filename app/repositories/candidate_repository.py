from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, contains_eager

from app.models import Candidate, Person
from app.models.constants import CANDIDATE_ROLE


def create(session: Session, name: str, email: str, party: str | None) -> Candidate:
    candidate = Candidate(person=Person(name=name, email=email, role=CANDIDATE_ROLE), party=party)
    session.add(candidate)
    session.flush()
    return candidate


def get_by_id(session: Session, candidate_id: int) -> Candidate | None:
    return session.get(Candidate, candidate_id)


def list_filtered(
    session: Session,
    *,
    limit: int,
    offset: int,
    party: str | None = None,
    name: str | None = None,
) -> list[Candidate]:
    query = select(Candidate).join(Candidate.person).options(contains_eager(Candidate.person))
    if party:
        query = query.where(func.lower(Candidate.party) == party.lower())
    if name:
        query = query.where(Person.name.icontains(name, autoescape=True))
    query = query.order_by(Candidate.person_id).limit(limit).offset(offset)
    return list(session.scalars(query))


def increment_votes(session: Session, candidate_id: int) -> None:
    # El incremento lo hace la base de datos (votes = votes + 1): leer, sumar en Python
    # y guardar perdería votos cuando dos transacciones lo hacen a la vez.
    session.execute(
        update(Candidate)
        .where(Candidate.person_id == candidate_id)
        .values(votes=Candidate.votes + 1)
    )


def delete(session: Session, candidate: Candidate) -> None:
    person = candidate.person
    session.delete(candidate)
    session.flush()
    session.delete(person)
    session.flush()
