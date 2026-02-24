"""Common response messages used across the application."""


class Messages:
    """Centralized response messages to avoid magic strings."""

    # Success messages
    SUCCESS = "Success"
    CREATED = "Created successfully"
    UPDATED = "Updated successfully"
    DELETED = "Deleted successfully"

    # Auth messages
    USER_REGISTERED = "User registered successfully"
    LOGIN_SUCCESS = "Login successful"
    TOKEN_REFRESHED = "Token refreshed successfully"
    LOGOUT_SUCCESS = "Logged out successfully"

    # User messages
    USER_PROFILE_RETRIEVED = "User profile retrieved"
    USER_PROFILE_UPDATED = "User profile updated"
    USER_NOT_FOUND = "User not found"
    USER_DEACTIVATED = "User account is deactivated"

    # Health messages
    API_HEALTHY = "API is healthy"
    DATABASE_HEALTHY = "Database connection is healthy"
    REDIS_HEALTHY = "Redis connection is healthy"

    # Error messages
    INTERNAL_ERROR = "Internal server error"
    VALIDATION_ERROR = "Validation error"
    NOT_FOUND = "Resource not found"
    UNAUTHORIZED = "Unauthorized"
    FORBIDDEN = "Access denied"
    CONFLICT = "Resource conflict"
    BAD_REQUEST = "Bad request"
