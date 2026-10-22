from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import DbSession
from app.api.pagination import DEFAULT_LIMIT, Limit, NameFilter, Offset
from app.schemas.candidate import CandidateCreate, CandidateRead
from app.schemas.error import ErrorResponse
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
)
def create_candidate(payload: CandidateCreate, db: DbSession) -> CandidateRead:
    candidate = candidate_service.create_candidate(db, payload.name, payload.email, payload.party)
    return CandidateRead.from_model(candidate)


@router.get("")
def list_candidates(
    db: DbSession,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
    party: Annotated[
        str | None, Query(max_length=100, description="Partido exacto, sin distinguir mayúsculas")
    ] = None,
    name: NameFilter = None,
) -> list[CandidateRead]:
    candidates = candidate_service.list_candidates(
        db, limit=limit, offset=offset, party=party, name=name
    )
    return [CandidateRead.from_model(candidate) for candidate in candidates]


@router.get("/{candidate_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}})
def get_candidate(candidate_id: int, db: DbSession) -> CandidateRead:
    return CandidateRead.from_model(candidate_service.get_candidate(db, candidate_id))


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
def delete_candidate(candidate_id: int, db: DbSession) -> None:
    candidate_service.delete_candidate(db, candidate_id)
