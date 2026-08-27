import math


def bearing(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])

    dlon = lon2 - lon1

    x = math.sin(dlon) * math.cos(lat2)

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(dlon)
    )

    return math.degrees(math.atan2(x, y))


def distance_m(a, b):
    R = 6371000

    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a_ = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return R * 2 * math.asin(math.sqrt(a_))


def get_turn_directions(path_coords):
    directions = []

    if len(path_coords) < 2:
        return directions

    directions.append({
        "step": 1,
        "instruction": "Start your journey",
        "distance_m": 0,
        "lat": path_coords[0][0],
        "lon": path_coords[0][1]
    })

    for i in range(1, len(path_coords) - 1):

        prev = path_coords[i - 1]
        curr = path_coords[i]
        next_ = path_coords[i + 1]

        b1 = bearing(prev, curr)
        b2 = bearing(curr, next_)

        angle = (b2 - b1 + 360) % 360

        dist = round(distance_m(prev, curr))

        if dist < 20:
            continue

        if 30 < angle < 150:
            instruction = "Turn right"

        elif 210 < angle < 330:
            instruction = "Turn left"

        elif 150 <= angle <= 210:
            instruction = "Make a U-turn"

        else:
            continue

        directions.append({
            "step": len(directions) + 1,
            "instruction": instruction,
            "distance_m": dist,
            "lat": curr[0],
            "lon": curr[1]
        })

    directions.append({
        "step": len(directions) + 1,
        "instruction": "You have arrived at your destination!",
        "distance_m": 0,
        "lat": path_coords[-1][0],
        "lon": path_coords[-1][1]
    })

    return directions