from sqlalchemy.exc import IntegrityError


def violated_constraint(error: IntegrityError) -> str | None:
    # Se identifica la restricción por su nombre (diag de psycopg) y no por el texto
    # del mensaje, que cambia con el idioma y la versión de PostgreSQL.
    diag = getattr(error.orig, "diag", None)
    return diag.constraint_name if diag else None
