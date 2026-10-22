from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.constants import CANDIDATE_ROLE
from app.models.person import Person


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        # Igual que en Voter: la FK compuesta con role fijado por CHECK impide que
        # una persona registrada como votante tenga también fila de candidato.
        ForeignKeyConstraint(
            ["person_id", "role"],
            ["persons.id", "persons.role"],
            name="fk_candidates_person",
            ondelete="RESTRICT",
        ),
        CheckConstraint(f"role = '{CANDIDATE_ROLE}'", name="ck_candidates_role"),
        CheckConstraint("votes >= 0", name="ck_candidates_votes"),
    )

    person_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    role: Mapped[str] = mapped_column(
        String(10), default=CANDIDATE_ROLE, server_default=CANDIDATE_ROLE
    )
    party: Mapped[str | None] = mapped_column(String(100))
    votes: Mapped[int] = mapped_column(default=0, server_default="0")

    person: Mapped[Person] = relationship(lazy="joined", innerjoin=True)
