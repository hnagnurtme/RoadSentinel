from dataclasses import dataclass


@dataclass(frozen=True)
class ListVehiclesQuery:
    limit: int = 20
