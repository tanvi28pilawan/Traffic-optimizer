"""
Tests for bearing(), distance_m(), and get_turn_directions()
using hand-built synthetic coordinate paths (no OSM/network needed).

Run with: python3 test_geo_utils.py
"""

from geo_utils import bearing, distance_m, get_turn_directions

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


# ---------- 1. distance_m() sanity check ----------
# Roughly 111 km per 1 degree of latitude near the equator-ish latitudes.
a = (19.8762, 75.3433)
b = (19.8862, 75.3433)   # ~0.01 deg north
d = distance_m(a, b)
print("\n[distance_m]")
check("north offset ~ 1111m", 1000 < d < 1250, f"got {d:.1f}m")

# ---------- 2. bearing() sanity check ----------
print("\n[bearing]")
brg = bearing(a, b)  # straight north should be ~0 degrees
check("due north bearing ~ 0deg", -2 < brg < 2 or brg > 358, f"got {brg:.1f}")

east_point = (19.8762, 75.3533)  # same lat, moved east in longitude
brg_e = bearing(a, east_point)
check("due east bearing ~ 90deg", 88 < brg_e < 92, f"got {brg_e:.1f}")


# ---------- 3. get_turn_directions() with constructed paths ----------
print("\n[get_turn_directions] straight line (no turns expected)")
straight = [
    (19.8762, 75.3433),
    (19.8772, 75.3433),
    (19.8782, 75.3433),
    (19.8792, 75.3433),
]
result = get_turn_directions(straight)
instructions = [d["instruction"] for d in result]
check("only start+arrive, no turn instructions", instructions == ["Start your journey", "You have arrived at your destination!"],
      f"got {instructions}")

print("\n[get_turn_directions] right turn (heading north, then turns east)")
right_turn = [
    (19.8762, 75.3433),   # start
    (19.8772, 75.3433),   # heading north
    (19.8772, 75.3453),   # now heading east -> should be "Turn right"
]
result = get_turn_directions(right_turn)
instructions = [d["instruction"] for d in result]
check("'Turn right' detected", "Turn right" in instructions, f"got {instructions}")

print("\n[get_turn_directions] left turn (heading north, then turns west)")
left_turn = [
    (19.8762, 75.3433),
    (19.8772, 75.3433),   # heading north
    (19.8772, 75.3413),   # now heading west -> should be "Turn left"
]
result = get_turn_directions(left_turn)
instructions = [d["instruction"] for d in result]
check("'Turn left' detected", "Turn left" in instructions, f"got {instructions}")

print("\n[get_turn_directions] tiny segment (<20m) should be skipped")
tiny = [
    (19.8762, 75.3433),
    (19.8762001, 75.3433001),  # a few meters only
    (19.8772, 75.3453),
]
result = get_turn_directions(tiny)
# should not crash, and length should just be start+arrive (tiny segment skipped, only 3 points total anyway)
check("does not crash on tiny segments", isinstance(result, list))

print(f"\n{'='*40}\n{PASS} passed, {FAIL} failed\n{'='*40}")
