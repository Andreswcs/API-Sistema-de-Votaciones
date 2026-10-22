class DomainError(Exception):
    code = "DOMAIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "NOT_FOUND"


class EmailAlreadyRegisteredError(DomainError):
    code = "EMAIL_ALREADY_REGISTERED"

    def __init__(self, email: str) -> None:
        super().__init__(f"El email {email} ya está registrado")


class AlreadyVotedError(DomainError):
    code = "ALREADY_VOTED"

    def __init__(self, voter_id: int) -> None:
        super().__init__(f"El votante {voter_id} ya ha votado")


class ResourceInUseError(DomainError):
    code = "RESOURCE_IN_USE"
