"""Static depot capacities and route-to-depot distances."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Depot:
    depot_id: str
    name: str
    capacity: int


DEPOTS = (
    Depot("D01", "North Depot", 3),
    Depot("D02", "South Depot", 3),
    Depot("D03", "East Depot", 2),
    Depot("D04", "West Depot", 2),
    Depot("D05", "Central Depot", 4),
)

DISTANCE_TABLE = {
    "A": {"D01": 2, "D02": 8, "D03": 5, "D04": 7, "D05": 4},
    "B": {"D01": 6, "D02": 3, "D03": 8, "D04": 5, "D05": 4},
    "C": {"D01": 7, "D02": 5, "D03": 2, "D04": 8, "D05": 4},
    "D": {"D01": 5, "D02": 7, "D03": 6, "D04": 2, "D05": 3},
    "E": {"D01": 4, "D02": 6, "D03": 5, "D04": 7, "D05": 1},
}


def get_route_distances(route_key: str) -> dict[str, int] | None:
    """Return a copy of the distance lookup for a route letter."""
    distances = DISTANCE_TABLE.get(route_key.upper()) if isinstance(route_key, str) else None
    return distances.copy() if distances is not None else None


def sorted_depots(route_key: str) -> list[tuple[Depot, int]]:
    """Return depots ordered by distance, then depot ID for deterministic ties."""
    distances = get_route_distances(route_key)
    if distances is None:
        return []
    depots_by_id = {depot.depot_id: depot for depot in DEPOTS}
    return sorted(
        ((depots_by_id[depot_id], distance) for depot_id, distance in distances.items()),
        key=lambda item: (item[1], item[0].depot_id),
    )
