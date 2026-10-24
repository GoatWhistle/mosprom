import math

from .mesh import bounds, box, circle, prism, square_with_hole
from .settings import known_keys

BASE_MM = (70.0, 50.0, 2.0)
OVERHANG_ANGLES = [45, 60, 70]
HOLE_DIAMETERS = [3.0, 4.0, 5.0]
SPIRE_STEPS = [8.0, 6.0, 4.0, 3.0, 2.0, 1.0]
FACES = {"A": {"side": "left, x = 0", "dots": [(1.5, 26.0)]},
         "B": {"side": "front, y = 0", "dots": [(14.0, 1.5), (18.0, 1.5)]},
         "C": {"side": "right, x = 70", "dots": [(68.5, 26.0), (68.5, 30.0), (68.5, 34.0)]},
         "D": {"side": "back, y = 50", "dots": [(40.0, 48.5), (44.0, 48.5), (48.0, 48.5), (52.0, 48.5)]}}

ZONES = [
    {"id": "base", "face": "all sides and bottom",
     "look_for": "first layer lines fused, no flared bottom edge (elephant foot), corners flat on the bed",
     "setting_keys": ["layer_height_0", "material_bed_temperature", "adhesion_type"],
     "defect_ids": ["first_layer_squish", "poor_adhesion", "warping"]},
    {"id": "overhangs", "face": "A",
     "look_for": "undersides of the three ramps 45/60/70 degrees from vertical: smooth or drooping, curled edges",
     "setting_keys": ["cool_fan_speed", "support_angle"], "defect_ids": ["overhang_sag"]},
    {"id": "bridge", "face": "B",
     "look_for": "underside of the 20 mm span: straight strands or sagging, gaps between strands",
     "setting_keys": ["bridge_settings_enabled", "bridge_skin_speed", "bridge_fan_speed", "cool_fan_speed"],
     "defect_ids": ["overhang_sag"]},
    {"id": "towers", "face": "B",
     "look_for": "threads or hairs in the 20 mm gap between the two 5 mm towers, seen from face B above the bridge "
                 "or from face D; blobs on tower walls",
     "setting_keys": ["retraction_amount", "retraction_speed", "material_print_temperature"],
     "defect_ids": ["stringing", "zits_blobs"]},
    {"id": "holes", "face": "top",
     "look_for": "round holes of 3, 4 and 5 mm, left to right from face A",
     "setting_keys": ["xy_offset"], "defect_ids": ["dimension_error"],
     "measure": "measure each hole with a caliper and pass nominal and measured diameters to calculate hole_compensation"},
    {"id": "thin_wall", "face": "D",
     "look_for": "the 0.8 mm wall is solid, without gaps or missing lines",
     "setting_keys": ["wall_line_width", "material_flow"], "defect_ids": ["wall_gaps", "under_extrusion"]},
    {"id": "spire", "face": "D",
     "look_for": "small top steps 3..1 mm: sharp edges or melted, blobby tips",
     "setting_keys": ["cool_min_layer_time", "material_print_temperature"],
     "defect_ids": ["over_extrusion", "rough_surface"]},
    {"id": "top", "face": "top",
     "look_for": "the 20 x 20 mm pad top is closed, without holes or visible infill",
     "setting_keys": ["top_layers", "infill_sparse_density"], "defect_ids": ["top_surface_holes"]},
]


def _overhangs(z0, height):
    triangles = []
    for index, angle in enumerate(OVERHANG_ANGLES):
        y = 3.0 + index * 8.0
        reach = height * math.tan(math.radians(angle))
        profile = [(24.0, z0), (28.0, z0), (28.0, z0 + height), (24.0 - reach, z0 + height)]
        triangles += prism(profile, y, y + 5.0, plane="xz")
    return triangles


def _bridge(z0):
    profile = [(36.0, z0), (40.0, z0), (40.0, z0 + 8.0), (60.0, z0 + 8.0), (60.0, z0), (64.0, z0),
               (64.0, z0 + 9.2), (36.0, z0 + 9.2)]
    return prism(profile, 2.0, 10.0, plane="xz")


def _towers(z0):
    return prism(circle(40.0, 20.0, 2.5), z0, z0 + 25.0) + prism(circle(65.0, 20.0, 2.5), z0, z0 + 25.0)


def _holes(z0):
    triangles = []
    x = 2.0
    for diameter in HOLE_DIAMETERS:
        size = diameter + 6.0
        triangles += square_with_hole(x + size / 2.0, 33.0, size, diameter / 2.0, z0, z0 + 5.0)
        x += size + 2.0
    return triangles


def _spire(z0):
    triangles = []
    for index, size in enumerate(SPIRE_STEPS):
        half = size / 2.0
        triangles += box(32.0 - half, 44.0 - half, z0 + 3.0 * index, 32.0 + half, 44.0 + half, z0 + 3.0 * (index + 1))
    return triangles


def _dots(z0):
    return [triangle for face in sorted(FACES) for x, y in FACES[face]["dots"]
            for triangle in prism(circle(x, y, 1.0, 16), z0, z0 + 1.0)]


def calibration_figure(params):
    width, depth, plate = BASE_MM
    parts = {"base": box(0, 0, 0, width, depth, plate) + _dots(plate), "overhangs": _overhangs(plate, 8.0),
             "bridge": _bridge(plate), "towers": _towers(plate), "holes": _holes(plate),
             "thin_wall": box(2.0, 44.0, plate, 22.0, 44.8, plate + 12.0), "spire": _spire(plate),
             "top": box(44.0, 27.0, plate, 64.0, 47.0, plate + 6.0)}
    zones = [dict(zone, bbox_mm=bounds(parts[zone["id"]])) for zone in ZONES]
    triangles = [triangle for zone in ZONES for triangle in parts[zone["id"]]]
    return triangles, {"checks": "one fixed figure with a zone per print problem; params are ignored so attempts compare",
                       "faces": dict((name, {"side": FACES[name]["side"], "dots": len(FACES[name]["dots"])})
                                     for name in FACES),
                       "photos": "photograph each face A-D (count the dots on the plate edge) and the top in good light",
                       "zones": zones,
                       "assumes": "the slicer unions overlapping bodies (Cura meshfix_union_all)"}


def checked_zones(zones, facts):
    unknown = []
    checked = []
    for zone in zones:
        keys = known_keys(facts, zone["setting_keys"])
        unknown += [key for key in zone["setting_keys"] if key not in keys]
        checked.append(dict(zone, setting_keys=keys))
    return checked, sorted(set(unknown))
