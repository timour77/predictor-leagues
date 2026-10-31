"""Domain rule violations; main.py turns them into JSON responses so routers stay thin."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    """The request is valid but not allowed in the current state (deadline passed, League closed)."""
    status_code = 409


class Invalid(DomainError):
    status_code = 422
