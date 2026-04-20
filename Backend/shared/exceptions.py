"""
shared/exceptions.py
---------------------
Application-level exception hierarchy.

All exceptions carry an HTTP ``status_code`` and a machine-readable ``code``
string so the exception middleware can produce consistent error responses
without any extra mapping logic.
"""


class AppException(Exception):
    status_code: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundException(AppException):
    status_code = 404
    code = "NOT_FOUND"


class ConflictException(AppException):
    status_code = 409
    code = "CONFLICT"


class ValidationException(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"


class ForbiddenException(AppException):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedException(AppException):
    status_code = 401
    code = "UNAUTHORIZED"
