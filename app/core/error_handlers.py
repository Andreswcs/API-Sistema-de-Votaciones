from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AlreadyVotedError,
    DomainError,
    EmailAlreadyRegisteredError,
    NotFoundError,
    ResourceInUseError,
)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    EmailAlreadyRegisteredError: status.HTTP_409_CONFLICT,
    AlreadyVotedError: status.HTTP_409_CONFLICT,
    ResourceInUseError: status.HTTP_409_CONFLICT,
}


def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        content={"detail": exc.message, "code": exc.code},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
