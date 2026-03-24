from infrastructure.db.models.base import PGView


class UserOverviewView(PGView):
    schema = "user"
    name = "_user_overview"
    query = """
    SELECT
        u.id,
        u.email,
        u.name,
        u.created_at,
        u.updated_at,
        u.deleted_at
    FROM "user"."user" u
    """
