from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegisteredError, NotFoundError, ResourceInUseError
from app.models import Voter
from app.models.constants import FK_VOTES_VOTER, UQ_PERSONS_EMAIL
from app.repositories import voter_repository
from app.services.integrity import violated_constraint


def create_voter(session: Session, name: str, email: str) -> Voter:
    try:
        voter = voter_repository.create(session, name, email)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if violated_constraint(error) == UQ_PERSONS_EMAIL:
            raise EmailAlreadyRegisteredError(email) from error
        raise
    return voter


def get_voter(session: Session, voter_id: int) -> Voter:
    voter = voter_repository.get_by_id(session, voter_id)
    if voter is None:
        raise NotFoundError(f"Votante {voter_id} no encontrado")
    return voter


def list_voters(
    session: Session,
    *,
    limit: int,
    offset: int,
    has_voted: bool | None = None,
    name: str | None = None,
) -> list[Voter]:
    return voter_repository.list_filtered(
        session, limit=limit, offset=offset, has_voted=has_voted, name=name
    )


def delete_voter(session: Session, voter_id: int) -> None:
    voter = get_voter(session, voter_id)
    try:
        voter_repository.delete(session, voter)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if violated_constraint(error) == FK_VOTES_VOTER:
            raise ResourceInUseError(
                f"El votante {voter_id} ya votó y no puede eliminarse"
            ) from error
        raise
