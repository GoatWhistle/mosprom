import math


def scene_to_build(vector):
    return (vector[0], -vector[2], vector[1])


def build_to_scene(vector):
    return (vector[0], vector[2], -vector[1])


def euler_matrix(rotation_deg):
    rx, ry, rz = [math.radians(item) for item in rotation_deg]
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rot_x = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    rot_y = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rot_z = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))
    return multiply(rot_z, multiply(rot_y, rot_x))


def multiply(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def conjugate_to_scene(matrix):
    swap = ((1, 0, 0), (0, 0, 1), (0, -1, 0))
    inverse = ((1, 0, 0), (0, 0, -1), (0, 1, 0))
    return multiply(swap, multiply(matrix, inverse))


def matrix_to_quaternion(m):
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        return ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    if m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        return (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    if m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        return ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
    return ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)


def build_rotation_to_scene_quaternion(rotation_deg):
    return matrix_to_quaternion(conjugate_to_scene(euler_matrix(rotation_deg)))


def quaternion_to_matrix(q):
    x, y, z, w = q
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def matrix_to_euler(m):
    sy = -m[2][0]
    sy = max(-1.0, min(1.0, sy))
    ry = math.asin(sy)
    if abs(sy) < 0.999999:
        rx = math.atan2(m[2][1], m[2][2])
        rz = math.atan2(m[1][0], m[0][0])
    else:
        rx = math.atan2(-m[1][2], m[1][1])
        rz = 0.0
    return tuple(math.degrees(item) for item in (rx, ry, rz))


def scene_quaternion_to_build_euler(q):
    scene = quaternion_to_matrix(q)
    swap = ((1, 0, 0), (0, 0, -1), (0, 1, 0))
    inverse = ((1, 0, 0), (0, 0, 1), (0, -1, 0))
    return matrix_to_euler(multiply(swap, multiply(scene, inverse)))
