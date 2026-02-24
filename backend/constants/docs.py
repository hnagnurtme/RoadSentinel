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


class AuthDocs:
    """Documentation for auth endpoints."""

    class Register:
        SUMMARY = "Register"
        DESCRIPTION = "Create a new user account. Optionally provide an organization name. Returns a JWT token pair."

    class Login:
        SUMMARY = "Login"
        DESCRIPTION = "Authenticate with email and password. Returns an access + refresh JWT token pair."

    class Refresh:
        SUMMARY = "Refresh token"
        DESCRIPTION = "Exchange a valid refresh token for a new access token."

    class Logout:
        SUMMARY = "Logout"
        DESCRIPTION = "Invalidate the current session (client must discard stored tokens)."