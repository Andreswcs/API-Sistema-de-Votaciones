import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Candidate, Person, Voter
from app.models.constants import CANDIDATE_ROLE, VOTER_ROLE


def test_models_match_database_schema(engine: Engine) -> None:
    inspector = inspect(engine)

    for table in Base.metadata.sorted_tables:
        db_columns = {column["name"] for column in inspector.get_columns(table.name)}
        assert db_columns == set(table.columns.keys()), table.name

        db_constraints = (
            {fk["name"] for fk in inspector.get_foreign_keys(table.name)}
            | {uq["name"] for uq in inspector.get_unique_constraints(table.name)}
            | {ck["name"] for ck in inspector.get_check_constraints(table.name)}
        )
        model_constraints = {c.name for c in table.constraints if c.name and c is not table.primary_key}
        assert model_constraints <= db_constraints, table.name


def test_person_cannot_be_voter_and_candidate(db_session: Session) -> None:
    person = Person(name="Ana", email="ana@mail.com", role=VOTER_ROLE)
    db_session.add(Voter(person=person))
    db_session.commit()

    db_session.add(Candidate(person_id=person.id, role=CANDIDATE_ROLE))
    with pytest.raises(IntegrityError):
        db_session.commit()
