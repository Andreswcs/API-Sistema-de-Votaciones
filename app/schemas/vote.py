from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VoteCreate(BaseModel):
    voter_id: int
    candidate_id: int


class VoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voter_id: int
    candidate_id: int
    created_at: datetime


class CandidateStatistics(BaseModel):
    candidate_id: int
    name: str
    party: str | None
    votes: int
    percentage: float


class VoteStatistics(BaseModel):
    total_votes: int
    total_voters_who_voted: int
    candidates: list[CandidateStatistics]
