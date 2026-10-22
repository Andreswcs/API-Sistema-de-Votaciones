from pydantic import BaseModel

from app.models import Voter
from app.schemas.person import PersonEmail, PersonName


class VoterCreate(BaseModel):
    name: PersonName
    email: PersonEmail


class VoterRead(BaseModel):
    id: int
    name: str
    email: str
    has_voted: bool

    @classmethod
    def from_model(cls, voter: Voter) -> "VoterRead":
        return cls(
            id=voter.person_id,
            name=voter.person.name,
            email=voter.person.email,
            has_voted=voter.has_voted,
        )
