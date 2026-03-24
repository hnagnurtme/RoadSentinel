from infrastructure.db.models.base import Base, DataModel, PGView
from infrastructure.db.models.alert import Alert, AlertOverviewView
from infrastructure.db.models.user import User, UserOverviewView

PG_VIEWS: tuple[type[PGView], ...] = (UserOverviewView, AlertOverviewView)

__all__ = [
    "Base",
    "DataModel",
    "PGView",
    "PG_VIEWS",
    "User",
    "Alert",
    "UserOverviewView",
    "AlertOverviewView",
]
