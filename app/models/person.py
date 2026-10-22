from sqlalchemy import CheckConstraint, Identity, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.constants import CANDIDATE_ROLE, UQ_PERSONS_EMAIL, VOTER_ROLE


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = (
        UniqueConstraint("email", name=UQ_PERSONS_EMAIL),
        CheckConstraint("email = lower(email)", name="ck_persons_email_lowercase"),
        CheckConstraint(f"role IN ('{VOTER_ROLE}', '{CANDIDATE_ROLE}')", name="ck_persons_role"),
        # Redundante con la PK: es el destino de las FK compuestas (person_id, role).
        UniqueConstraint("id", "role", name="uq_persons_id_role"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))
