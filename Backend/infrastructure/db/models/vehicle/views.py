from infrastructure.db.models.base import PGView


class VehicleOverviewView(PGView):
    schema = "vehicle"
    name = "_vehicle_overview"
    query = """
    SELECT
        v._id,
        v.plate_number,
        v.manufacturer,
        v.model,
        v.color,
        v.production_year,
        v.vin,
        v._created_at,
        v._updated_at,
        v._deleted_at
    FROM "vehicle"."vehicle" v
    """
