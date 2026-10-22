from typing import Annotated

from fastapi import Query

DEFAULT_LIMIT = 50
MAX_LIMIT = 100

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Número máximo de resultados")]
Offset = Annotated[int, Query(ge=0, description="Resultados que se omiten desde el inicio")]
NameFilter = Annotated[
    str | None,
    Query(max_length=100, description="Coincidencia parcial, sin distinguir mayúsculas"),
]
