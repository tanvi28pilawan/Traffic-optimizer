import math


# ============================================================
# BEARING
# ============================================================

def bearing(a, b):
    """
    Calculate bearing/direction from point A to point B.

    Points are in [latitude, longitude] format.
    Returns bearing in degrees.
    """

    lat1 = math.radians(a[0])
    lon1 = math.radians(a[1])

    lat2 = math.radians(b[0])
    lon2 = math.radians(b[1])

    dlon = lon2 - lon1

    x = math.sin(dlon) * math.cos(lat2)

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(dlon)
    )

    return math.degrees(math.atan2(x, y))


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def distance_m(a, b):
    """
    Calculate straight-line distance between two
    latitude/longitude points using the Haversine formula.

    Returns distance in meters.
    """

    R = 6371000.0  # Earth radius in meters

    lat1 = math.radians(a[0])
    lon1 = math.radians(a[1])

    lat2 = math.radians(b[0])
    lon2 = math.radians(b[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    haversine = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    # Prevent floating-point errors from making
    # the value slightly greater than 1.
    haversine = min(1.0, max(0.0, haversine))

    return R * 2.0 * math.asin(math.sqrt(haversine))


# ============================================================
# A* HEURISTIC
# ============================================================

def make_heuristic(G):
    """
    Creates the heuristic function used by A*.

    The heuristic estimates the remaining distance between
    two graph nodes using straight-line Haversine distance.

    Graph edge weights are measured in meters, so the
    heuristic uses the same unit.

    This heuristic is suitable for A* shortest-path routing.
    """

    def heuristic(u, v):
        u_data = G.nodes[u]
        v_data = G.nodes[v]

        u_point = (
            float(u_data["y"]),
            float(u_data["x"])
        )

        v_point = (
            float(v_data["y"]),
            float(v_data["x"])
        )

        return distance_m(u_point, v_point)

    return heuristic


# ============================================================
# TURN DIRECTIONS
# ============================================================

def get_turn_directions(path_coords):
    """
    Convert route coordinates into simple turn-by-turn
    navigation instructions.

    path_coords format:
        [
            [latitude, longitude],
            [latitude, longitude],
            ...
        ]
    """

    directions = []

    if not path_coords:
        return directions

    if len(path_coords) == 1:
        return [
            {
                "step": 1,
                "instruction": "You have arrived at your destination!",
                "distance_m": 0,
                "lat": path_coords[0][0],
                "lon": path_coords[0][1]
            }
        ]

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    directions.append({
        "step": 1,
        "instruction": "Start your journey",
        "distance_m": 0,
        "lat": path_coords[0][0],
        "lon": path_coords[0][1]
    })

    # --------------------------------------------------------
    # TURNS
    # --------------------------------------------------------

    for i in range(1, len(path_coords) - 1):

        prev_point = path_coords[i - 1]
        current_point = path_coords[i]
        next_point = path_coords[i + 1]

        previous_bearing = bearing(
            prev_point,
            current_point
        )

        next_bearing = bearing(
            current_point,
            next_point
        )

        # Normalize angle to 0-360
        angle = (
            next_bearing
            - previous_bearing
            + 360
        ) % 360

        segment_distance = round(
            distance_m(
                prev_point,
                current_point
            )
        )

        # Ignore extremely small segments
        if segment_distance < 20:
            continue

        instruction = None

        # ----------------------------------------------------
        # RIGHT TURN
        # ----------------------------------------------------

        if 30 < angle < 150:
            instruction = "Turn right"

        # ----------------------------------------------------
        # LEFT TURN
        # ----------------------------------------------------

        elif 210 < angle < 330:
            instruction = "Turn left"

        # ----------------------------------------------------
        # U-TURN
        # ----------------------------------------------------

        elif 150 <= angle <= 210:
            instruction = "Make a U-turn"

        # ----------------------------------------------------
        # STRAIGHT / VERY SMALL CHANGE
        # ----------------------------------------------------

        else:
            continue

        directions.append({
            "step": len(directions) + 1,
            "instruction": instruction,
            "distance_m": segment_distance,
            "lat": current_point[0],
            "lon": current_point[1]
        })

    # --------------------------------------------------------
    # DESTINATION
    # --------------------------------------------------------

    directions.append({
        "step": len(directions) + 1,
        "instruction": "You have arrived at your destination!",
        "distance_m": 0,
        "lat": path_coords[-1][0],
        "lon": path_coords[-1][1]
    })

    return directions