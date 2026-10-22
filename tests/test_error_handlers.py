import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_handlers import register_error_handlers
from app.core.exceptions import (
    AlreadyVotedError,
    DomainError,
    EmailAlreadyRegisteredError,
    NotFoundError,
    ResourceInUseError,
)


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (NotFoundError("Votante 1 no encontrado"), 404, "NOT_FOUND"),
        (EmailAlreadyRegisteredError("ana@mail.com"), 409, "EMAIL_ALREADY_REGISTERED"),
        (AlreadyVotedError(1), 409, "ALREADY_VOTED"),
        (ResourceInUseError("En uso"), 409, "RESOURCE_IN_USE"),
    ],
)
def test_domain_errors_are_translated_to_http(
    error: DomainError, expected_status: int, expected_code: str
) -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise error

    response = TestClient(app).get("/boom")

    assert response.status_code == expected_status
    assert response.json() == {"detail": error.message, "code": expected_code}
