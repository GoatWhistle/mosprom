import math
import struct


def _area2(polygon):
    return sum(polygon[i][0] * polygon[(i + 1) % len(polygon)][1] - polygon[(i + 1) % len(polygon)][0] * polygon[i][1]
               for i in range(len(polygon)))


def _inside(point, a, b, c):
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return side(a, b, point) > 0 and side(b, c, point) > 0 and side(c, a, point) > 0


def triangulate(polygon):
    indices = list(range(len(polygon)))
    triangles = []
    guard = 0
    while len(indices) > 3 and guard < 10000:
        guard += 1
        for position in range(len(indices)):
            i, j, k = indices[position - 1], indices[position], indices[(position + 1) % len(indices)]
            a, b, c = polygon[i], polygon[j], polygon[k]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0:
                continue
            if any(_inside(polygon[m], a, b, c) for m in indices if m not in (i, j, k)):
                continue
            triangles.append((i, j, k))
            del indices[position]
            break
        else:
            break
    if len(indices) == 3:
        triangles.append(tuple(indices))
    return triangles


def prism(polygon, low, high, plane="xy"):
    if _area2(polygon) < 0:
        polygon = list(reversed(polygon))

    def point(u, v, w):
        return (u, v, w) if plane == "xy" else (u, w, v)

    triangles = []
    caps = triangulate(polygon)
    for i, j, k in caps:
        triangles.append((point(polygon[i][0], polygon[i][1], high), point(polygon[j][0], polygon[j][1], high),
                          point(polygon[k][0], polygon[k][1], high)))
        triangles.append((point(polygon[i][0], polygon[i][1], low), point(polygon[k][0], polygon[k][1], low),
                          point(polygon[j][0], polygon[j][1], low)))
    for index in range(len(polygon)):
        a, b = polygon[index], polygon[(index + 1) % len(polygon)]
        a0, b0, a1, b1 = point(a[0], a[1], low), point(b[0], b[1], low), point(a[0], a[1], high), point(b[0], b[1], high)
        triangles.append((a0, b0, b1))
        triangles.append((a0, b1, a1))
    if plane == "xz":
        triangles = [(t[0], t[2], t[1]) for t in triangles]
    return triangles


def box(x0, y0, z0, x1, y1, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def circle(cx, cy, radius, segments=48):
    return [(cx + radius * math.cos(2 * math.pi * i / segments), cy + radius * math.sin(2 * math.pi * i / segments))
            for i in range(segments)]


def square_with_hole(cx, cy, size, radius, z0, z1, segments=48):
    half = size / 2.0
    inner = circle(cx, cy, radius, segments)
    outer = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        dx, dy = math.cos(angle), math.sin(angle)
        scale = half / max(abs(dx), abs(dy))
        outer.append((cx + dx * scale, cy + dy * scale))
    triangles = []
    for i in range(segments):
        j = (i + 1) % segments
        o0, o1, i0, i1 = outer[i], outer[j], inner[i], inner[j]
        triangles += [((i0[0], i0[1], z1), (o0[0], o0[1], z1), (o1[0], o1[1], z1)),
                      ((i0[0], i0[1], z1), (o1[0], o1[1], z1), (i1[0], i1[1], z1)),
                      ((i0[0], i0[1], z0), (o1[0], o1[1], z0), (o0[0], o0[1], z0)),
                      ((i0[0], i0[1], z0), (i1[0], i1[1], z0), (o1[0], o1[1], z0)),
                      ((o0[0], o0[1], z0), (o1[0], o1[1], z0), (o1[0], o1[1], z1)),
                      ((o0[0], o0[1], z0), (o1[0], o1[1], z1), (o0[0], o0[1], z1)),
                      ((i0[0], i0[1], z0), (i1[0], i1[1], z1), (i1[0], i1[1], z0)),
                      ((i0[0], i0[1], z0), (i0[0], i0[1], z1), (i1[0], i1[1], z1))]
    return triangles


def _normal(triangle):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = triangle
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def write_stl(path, triangles, name="brim calibration"):
    header = name.encode("ascii", "replace")[:80].ljust(80, b" ")
    with open(path, "wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            handle.write(struct.pack("<3f", *_normal(triangle)))
            for vertex in triangle:
                handle.write(struct.pack("<3f", *vertex))
            handle.write(b"\x00\x00")


def bounds(triangles):
    points = [vertex for triangle in triangles for vertex in triangle]
    return {"min": [round(min(p[i] for p in points), 3) for i in range(3)],
            "max": [round(max(p[i] for p in points), 3) for i in range(3)]}
