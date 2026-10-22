from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Identity, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.constants import FK_VOTES_CANDIDATE, FK_VOTES_VOTER, UQ_VOTES_VOTER


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("voter_id", name=UQ_VOTES_VOTER),
        Index("ix_votes_candidate_id", "candidate_id"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    voter_id: Mapped[int] = mapped_column(
        ForeignKey("voters.person_id", name=FK_VOTES_VOTER, ondelete="RESTRICT")
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.person_id", name=FK_VOTES_CANDIDATE, ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
