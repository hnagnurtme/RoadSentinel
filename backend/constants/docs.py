class UserDocs:
    """Documentation for user endpoints."""

    class GetMe:
        SUMMARY = "Get current user"
        DESCRIPTION = "Get the profile of the currently authenticated user."

    class UpdateMe:
        SUMMARY = "Update current user"
        DESCRIPTION = "Update the profile of the currently authenticated user."

    class GetById:
        SUMMARY = "Get user by ID"
        DESCRIPTION = "Get a user's public profile by their ID."

    class List:
        SUMMARY = "List users"
        DESCRIPTION = "Get a paginated list of users in the organization."