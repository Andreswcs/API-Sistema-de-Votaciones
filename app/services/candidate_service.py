from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegisteredError, NotFoundError, ResourceInUseError
from app.models import Candidate
from app.models.constants import FK_VOTES_CANDIDATE, UQ_PERSONS_EMAIL
from app.repositories import candidate_repository
from app.services.integrity import violated_constraint


def create_candidate(session: Session, name: str, email: str, party: str | None) -> Candidate:
    try:
        candidate = candidate_repository.create(session, name, email, party)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if violated_constraint(error) == UQ_PERSONS_EMAIL:
            raise EmailAlreadyRegisteredError(email) from error
        raise
    return candidate


def get_candidate(session: Session, candidate_id: int) -> Candidate:
    candidate = candidate_repository.get_by_id(session, candidate_id)
    if candidate is None:
        raise NotFoundError(f"Candidato {candidate_id} no encontrado")
    return candidate


def list_candidates(
    session: Session,
    *,
    limit: int,
    offset: int,
    party: str | None = None,
    name: str | None = None,
) -> list[Candidate]:
    return candidate_repository.list_filtered(
        session, limit=limit, offset=offset, party=party, name=name
    )


def delete_candidate(session: Session, candidate_id: int) -> None:
    candidate = get_candidate(session, candidate_id)
    try:
        candidate_repository.delete(session, candidate)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if violated_constraint(error) == FK_VOTES_CANDIDATE:
            raise ResourceInUseError(
                f"El candidato {candidate_id} tiene votos y no puede eliminarse"
            ) from error
        raise
