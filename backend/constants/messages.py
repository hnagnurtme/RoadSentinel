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

    # Organization messages
    ORGANIZATION_CREATED = "Organization created successfully"
    ORGANIZATION_UPDATED = "Organization updated successfully"
    ORGANIZATION_RETRIEVED = "Organization retrieved"
    ORGANIZATION_LIST_RETRIEVED = "Organizations retrieved"

    # Project messages
    PROJECT_CREATED = "Project created successfully"
    PROJECT_UPDATED = "Project updated successfully"
    PROJECT_DELETED = "Project deleted successfully"
    PROJECT_RETRIEVED = "Project retrieved"
    PROJECT_LIST_RETRIEVED = "Projects retrieved"
    PROJECT_MEMBER_ADDED = "Member added to project successfully"
    PROJECT_MEMBER_REMOVED = "Member removed from project successfully"
    PROJECT_MEMBERS_RETRIEVED = "Project members retrieved"

    # Task messages
    TASK_CREATED = "Task created successfully"
    TASK_UPDATED = "Task updated successfully"
    TASK_DELETED = "Task deleted successfully"
    TASK_RETRIEVED = "Task retrieved"
    TASK_LIST_RETRIEVED = "Tasks retrieved"
    TASK_ASSIGNED = "Task assigned successfully"
    TASK_STATUS_UPDATED = "Task status updated"

    # Comment messages
    COMMENT_ADDED = "Comment added successfully"
    COMMENTS_RETRIEVED = "Comments retrieved successfully"

    # Report messages
    REPORT_RETRIEVED = "Report generated successfully"

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
