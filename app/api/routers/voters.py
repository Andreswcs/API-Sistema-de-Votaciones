from fastapi import APIRouter, status

from app.api.dependencies import DbSession
from app.schemas.error import ErrorResponse
from app.schemas.voter import VoterCreate, VoterRead
from app.services import voter_service

router = APIRouter(prefix="/voters", tags=["voters"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
)
def create_voter(payload: VoterCreate, db: DbSession) -> VoterRead:
    return VoterRead.from_model(voter_service.create_voter(db, payload.name, payload.email))


@router.get("")
def list_voters(db: DbSession) -> list[VoterRead]:
    return [VoterRead.from_model(voter) for voter in voter_service.list_voters(db)]


@router.get("/{voter_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}})
def get_voter(voter_id: int, db: DbSession) -> VoterRead:
    return VoterRead.from_model(voter_service.get_voter(db, voter_id))


@router.delete(
    "/{voter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
def delete_voter(voter_id: int, db: DbSession) -> None:
    voter_service.delete_voter(db, voter_id)
