from infrastructure.db.models.base import PGView


class UserOverviewView(PGView):
    schema = "user"
    name = "_user_overview"
    query = """
    SELECT
        u.id,
        u.email,
        u.name,
        u.name__family,
        u.name__given,
        u.name__middle,
        u.name__prefix,
        u.name__suffix,
        u.birthday,
        u.gender,
        u.address__city,
        u.address__country,
        u.address__line1,
        u.address__line2,
        u.created_at,
        u.updated_at,
        u.deleted_at
    FROM "user"."user" u
    """
