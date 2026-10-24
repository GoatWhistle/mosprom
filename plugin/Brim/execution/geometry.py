import math

WELD_DECIMALS = 4
FLAT_COSINE = 0.999
CONTACT_TOLERANCE_MM = 0.05
DEFAULT_SUPPORT_ANGLE_DEG = 50.0

LIMITATIONS = [
    "Fixed-direction analysis: overhang area is computed for one build direction only and is not a 5D printability check.",
    "Components, closedness and volume come from welded vertices with 1e-4 mm tolerance on the mesh as loaded in the slicer.",
    "Volume is reported only for a closed, consistently oriented mesh; otherwise it is null.",
    "Surface statistics ignore self-intersections and tiny features below the tolerance.",
]


def _normalise(vector):
    length = math.sqrt(sum(item * item for item in vector))
    if length == 0:
        raise ValueError("direction must be non-zero")
    return tuple(item / length for item in vector)


def _weld(vertices, triangles):
    index_by_key = {}
    remap = []
    for vertex in vertices:
        key = tuple(round(item, WELD_DECIMALS) for item in vertex)
        remap.append(index_by_key.setdefault(key, len(index_by_key)))
    welded = [(remap[a], remap[b], remap[c]) for a, b, c in triangles]
    return welded, len(index_by_key)


def _components(welded, vertex_count):
    parent = list(range(vertex_count))

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for a, b, c in welded:
        root_a = find(a)
        parent[find(b)] = root_a
        parent[find(c)] = root_a
    return len(set(find(a) for a, _, _ in welded))


def _topology(welded):
    directed = {}
    for a, b, c in welded:
        for start, end in ((a, b), (b, c), (c, a)):
            directed[(start, end)] = directed.get((start, end), 0) + 1
    boundary = 0
    non_manifold = 0
    inconsistent = 0
    seen = set()
    for (start, end), count in directed.items():
        key = (min(start, end), max(start, end))
        if key in seen:
            continue
        seen.add(key)
        forward = directed.get((start, end), 0)
        backward = directed.get((end, start), 0)
        total = forward + backward
        if total == 1:
            boundary += 1
        elif total > 2:
            non_manifold += 1
        elif forward == 2 or backward == 2:
            inconsistent += 1
    return boundary, non_manifold, inconsistent


def _cross2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segment_radius(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, -(a[0] * dx + a[1] * dy) / length))
    return math.hypot(a[0] + t * dx, a[1] + t * dy)


def _rotation_axis(vertices, triangles):
    crossings = 0
    min_radius = None
    max_radius = 0.0
    origin = (0.0, 0.0)
    for a, b, c in triangles:
        p, q, r = vertices[a], vertices[b], vertices[c]
        signs = (_cross2(p, q, origin), _cross2(q, r, origin), _cross2(r, p, origin))
        if (all(item >= 0 for item in signs) or all(item <= 0 for item in signs)) and any(signs):
            crossings += 1
        for start, end in ((p, q), (q, r), (r, p)):
            radius = _segment_radius(start, end)
            min_radius = radius if min_radius is None else min(min_radius, radius)
        max_radius = max(max_radius, max(math.hypot(point[0], point[1]) for point in (p, q, r)))
    return {
        "axis": "vertical line through the build plate center (x = 0, y = 0); the 5D rotation axis",
        "crosses_material": crossings > 0,
        "min_radius_mm": 0.0 if crossings else min_radius,
        "max_radius_mm": max_radius,
    }


def analyze(mesh, direction=None, support_angle_deg=DEFAULT_SUPPORT_ANGLE_DEG):
    vertices = mesh["vertices"]
    triangles = mesh["triangles"]
    axis = _normalise(direction or (0.0, 0.0, 1.0))
    welded, vertex_count = _weld(vertices, triangles)
    boundary, non_manifold, inconsistent = _topology(welded)
    closed = bool(triangles) and boundary == 0 and non_manifold == 0
    oriented = closed and inconsistent == 0
    area = 0.0
    signed_volume = 0.0
    overhang = 0.0
    contact_candidates = []
    min_height = None
    max_height = None
    sine = math.sin(math.radians(support_angle_deg))
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    for a, b, c in triangles:
        p, q, r = vertices[a], vertices[b], vertices[c]
        for point in (p, q, r):
            height = sum(point[i] * axis[i] for i in range(3))
            min_height = height if min_height is None else min(min_height, height)
            max_height = height if max_height is None else max(max_height, height)
            for i in range(3):
                mins[i] = min(mins[i], point[i])
                maxs[i] = max(maxs[i], point[i])
        u = (q[0] - p[0], q[1] - p[1], q[2] - p[2])
        v = (r[0] - p[0], r[1] - p[1], r[2] - p[2])
        cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        twice = math.sqrt(sum(item * item for item in cross))
        triangle_area = twice / 2.0
        area += triangle_area
        signed_volume += (p[0] * (q[1] * r[2] - q[2] * r[1]) - p[1] * (q[0] * r[2] - q[2] * r[0])
                          + p[2] * (q[0] * r[1] - q[1] * r[0])) / 6.0
        if twice == 0:
            continue
        along = sum(cross[i] * axis[i] for i in range(3)) / twice
        if -along > sine:
            overhang += triangle_area
        if along < -FLAT_COSINE:
            contact_candidates.append((triangle_area, sum(p[i] * axis[i] for i in range(3))))
    contact = sum(item[0] for item in contact_candidates
                  if min_height is not None and item[1] - min_height <= CONTACT_TOLERANCE_MM)
    return {
        "units": "mm",
        "frame": mesh.get("frame", "build_plate"),
        "geometry_version": mesh.get("geometry_version"),
        "method": "welded-vertex topology and per-triangle normals",
        "limitations": list(LIMITATIONS),
        "triangle_count": len(triangles),
        "bounds_mm": {"min": list(mins) if triangles else None, "max": list(maxs) if triangles else None},
        "connected_components": _components(welded, vertex_count) if triangles else 0,
        "closed": closed,
        "boundary_edges": boundary,
        "non_manifold_edges": non_manifold,
        "inconsistent_orientation_edges": inconsistent,
        "volume_valid": oriented,
        "volume_mm3": abs(signed_volume) if oriented else None,
        "surface_area_mm2": area,
        "direction": list(axis),
        "support_angle_deg": support_angle_deg,
        "height_along_direction_mm": (max_height - min_height) if triangles else 0.0,
        "overhang_area_mm2": overhang,
        "overhang_area_fraction": overhang / area if area > 0 else 0.0,
        "bed_contact_area_mm2": contact,
        "rotation_axis_5d": _rotation_axis(vertices, triangles) if triangles else None,
    }
