from typing import Annotated

from pydantic import BeforeValidator, EmailStr, StringConstraints


def _normalize_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# email-validator ya limita la dirección a 254 caracteres, dentro del máximo de 255 de la columna.
PersonEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]
