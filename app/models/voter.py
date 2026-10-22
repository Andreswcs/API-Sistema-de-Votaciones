from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.constants import VOTER_ROLE
from app.models.person import Person


class Voter(Base):
    __tablename__ = "voters"
    __table_args__ = (
        # La FK compuesta (person_id, role) con role fijado a 'VOTER' por CHECK obliga a que
        # la persona referenciada tenga ese mismo rol: nadie puede ser votante y candidato a la vez.
        ForeignKeyConstraint(
            ["person_id", "role"],
            ["persons.id", "persons.role"],
            name="fk_voters_person",
            ondelete="RESTRICT",
        ),
        CheckConstraint(f"role = '{VOTER_ROLE}'", name="ck_voters_role"),
    )

    person_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    role: Mapped[str] = mapped_column(String(10), default=VOTER_ROLE, server_default=VOTER_ROLE)
    has_voted: Mapped[bool] = mapped_column(default=False, server_default=false())

    person: Mapped[Person] = relationship(lazy="joined", innerjoin=True)
