from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.models import Candidate
from app.schemas.person import PersonEmail, PersonName

PartyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class CandidateCreate(BaseModel):
    name: PersonName
    email: PersonEmail
    party: PartyName | None = None


class CandidateRead(BaseModel):
    id: int
    name: str
    email: str
    party: str | None
    votes: int

    @classmethod
    def from_model(cls, candidate: Candidate) -> "CandidateRead":
        return cls(
            id=candidate.person_id,
            name=candidate.person.name,
            email=candidate.person.email,
            party=candidate.party,
            votes=candidate.votes,
        )
