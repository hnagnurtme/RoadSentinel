from infrastructure.db.models.base import Base, DataModel, PGView
from infrastructure.db.models.alert import Alert, Appeal, AlertOverviewView
from infrastructure.db.models.user import User, UserOverviewView
from infrastructure.db.models.vehicle import Vehicle, VehicleOverviewView

PG_VIEWS: tuple[type[PGView], ...] = (
    UserOverviewView,
    AlertOverviewView,
    VehicleOverviewView,
)

__all__ = [
    "Base",
    "DataModel",
    "PGView",
    "PG_VIEWS",
    "User",
    "Alert",
    "Vehicle",
    "UserOverviewView",
    "AlertOverviewView",
    "VehicleOverviewView",
]
