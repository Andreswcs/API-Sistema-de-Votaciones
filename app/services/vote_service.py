from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AlreadyVotedError, DomainError, NotFoundError
from app.models import Vote
from app.models.constants import FK_VOTES_CANDIDATE, FK_VOTES_VOTER, UQ_VOTES_VOTER
from app.repositories import candidate_repository, vote_repository, voter_repository
from app.schemas.vote import CandidateStatistics, VoteStatistics
from app.services.integrity import violated_constraint


def cast_vote(session: Session, voter_id: int, candidate_id: int) -> Vote:
    """Registra el voto y actualiza votante y candidato en una sola transacción."""
    try:
        _ensure_participants_exist(session, voter_id, candidate_id)
        vote = vote_repository.create(session, voter_id, candidate_id)
        if not voter_repository.mark_as_voted(session, voter_id):
            raise AlreadyVotedError(voter_id)
        candidate_repository.increment_votes(session, candidate_id)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        domain_error = _translate_vote_integrity_error(error, voter_id, candidate_id)
        if domain_error is None:
            raise
        raise domain_error from error
    except DomainError:
        session.rollback()
        raise
    return vote


def _ensure_participants_exist(session: Session, voter_id: int, candidate_id: int) -> None:
    if voter_repository.get_by_id(session, voter_id) is None:
        raise NotFoundError(f"Votante {voter_id} no encontrado")
    if candidate_repository.get_by_id(session, candidate_id) is None:
        raise NotFoundError(f"Candidato {candidate_id} no encontrado")


def _translate_vote_integrity_error(
    error: IntegrityError, voter_id: int, candidate_id: int
) -> DomainError | None:
    constraint = violated_constraint(error)
    # El UNIQUE de votes.voter_id es la última barrera ante dos votos simultáneos del mismo
    # votante: la segunda transacción espera a la primera y falla cuando esta confirma.
    if constraint == UQ_VOTES_VOTER:
        return AlreadyVotedError(voter_id)
    # Las FK solo saltan si el votante o el candidato se borró tras la comprobación inicial.
    if constraint == FK_VOTES_VOTER:
        return NotFoundError(f"Votante {voter_id} no encontrado")
    if constraint == FK_VOTES_CANDIDATE:
        return NotFoundError(f"Candidato {candidate_id} no encontrado")
    return None


def list_votes(session: Session) -> list[Vote]:
    return vote_repository.list_all(session)


def get_statistics(session: Session) -> VoteStatistics:
    rows = vote_repository.count_votes_per_candidate(session)
    # Cada voto apunta a un candidato: sumar los conteos del LEFT JOIN equivale a COUNT(votes).
    total_votes = sum(row.votes for row in rows)
    candidates = [
        CandidateStatistics(
            candidate_id=row.person_id,
            name=row.name,
            party=row.party,
            votes=row.votes,
            # Sin votos no hay reparto que calcular: 0.0 en lugar de dividir por cero.
            percentage=round(row.votes / total_votes * 100, 2) if total_votes else 0.0,
        )
        for row in rows
    ]
    return VoteStatistics(
        total_votes=total_votes,
        total_voters_who_voted=voter_repository.count_who_voted(session),
        candidates=candidates,
    )
