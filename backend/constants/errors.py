"""Error codes used throughout the application."""


class ErrorCodes:
    """Centralized error codes to avoid magic strings."""

    # Authentication errors
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    FORBIDDEN = "FORBIDDEN"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    INTEGRITY_ERROR = "INTEGRITY_ERROR"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
