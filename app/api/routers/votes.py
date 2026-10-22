from fastapi import APIRouter, status

from app.api.dependencies import DbSession
from app.schemas.error import ErrorResponse
from app.schemas.vote import VoteCreate, VoteRead, VoteStatistics
from app.services import vote_service

router = APIRouter(prefix="/votes", tags=["votes"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
def cast_vote(payload: VoteCreate, db: DbSession) -> VoteRead:
    vote = vote_service.cast_vote(db, payload.voter_id, payload.candidate_id)
    return VoteRead.model_validate(vote)


@router.get("")
def list_votes(db: DbSession) -> list[VoteRead]:
    return [VoteRead.model_validate(vote) for vote in vote_service.list_votes(db)]


@router.get("/statistics")
def get_statistics(db: DbSession) -> VoteStatistics:
    return vote_service.get_statistics(db)
