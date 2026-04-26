"""
application/alert/queries/list_alerts_overview.py
-----------------------------------------------
Query for listing alerts with pre-joined user and vehicle data using AlertOverviewView.
"""
from __future__ import annotations

import uuid
from typing import NamedTuple


class ListAlertsOverviewQuery(NamedTuple):
    """Fetch a paginated list of alerts with pre-joined relations."""
    limit: int
    driver_id: uuid.UUID | None = None
