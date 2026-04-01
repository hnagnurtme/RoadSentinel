from infrastructure.db.models.base import PGView


class UserOverviewView(PGView):
    schema = "user"
    name = "_user_overview"
    query = """
    SELECT
        u._id,
        u.email,
        u.name,
        u.avatar_image_url,
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
        u._created_at,
        u._updated_at,
        u._deleted_at
    FROM "user"."user" u
    """
