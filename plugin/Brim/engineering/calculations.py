import math

from ..execution.errors import OperationError
from ..protocol import constants
from .lewis import form_factor

DEFAULT_POISSON = 0.35


def _number(inputs, name, positive=True, default=None):
    value = inputs.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if default is not None and value is None:
            return default
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "%s must be a number" % name)
    if positive and value <= 0:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "%s must be positive" % name)
    return float(value)


def _optional(inputs, name):
    return _number(inputs, name) if inputs.get(name) is not None else None


def _with_safety(result, stress_mpa, inputs):
    allowable = _optional(inputs, "allowable_stress_mpa")
    if allowable is not None:
        result["allowable_stress_mpa"] = allowable
        result["safety_factor"] = round(allowable / stress_mpa, 2) if stress_mpa > 0 else None
    return result


def gear_lewis_bending(inputs):
    torque = _number(inputs, "torque_nm") * 1000.0
    module = _number(inputs, "module_mm")
    teeth = _number(inputs, "teeth")
    face = _number(inputs, "face_width_mm")
    diameter = module * teeth
    factor = form_factor(teeth)
    tangential = 2.0 * torque / diameter
    stress = tangential / (face * module * factor)
    return _with_safety({
        "pitch_diameter_mm": round(diameter, 3), "lewis_form_factor": round(factor, 4),
        "tangential_force_n": round(tangential, 1), "bending_stress_mpa": round(stress, 2),
        "formula": "sigma = Ft / (b * m * Y), Ft = 2T / d, d = m * z",
        "assumptions": ["20° full-depth involute teeth, load at the tip, one tooth in contact",
                        "static Lewis estimate without dynamic, stress-concentration or layer-direction factors",
                        "a printed tooth is weaker across layers; keep layers perpendicular to the tooth face"],
    }, stress, inputs)


def shaft_torsion(inputs):
    torque = _number(inputs, "torque_nm") * 1000.0
    outer = _number(inputs, "diameter_mm")
    inner = _number(inputs, "inner_diameter_mm", positive=False, default=0.0)
    if inner >= outer:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "inner_diameter_mm must be smaller than diameter_mm")
    stress = 16.0 * torque * outer / (math.pi * (outer ** 4 - inner ** 4))
    return _with_safety({
        "shear_stress_mpa": round(stress, 2),
        "formula": "tau = 16 T D / (pi (D^4 - d^4))",
        "assumptions": ["round section without keyways or flats; a keyway or flat raises the stress 1.5-3x",
                        "compare with shear strength, roughly 0.5-0.6 of the tensile strength"],
    }, stress, inputs)


def rotating_hoop_stress(inputs):
    density = _number(inputs, "density_g_cm3") * 1000.0
    rpm = _number(inputs, "rpm")
    radius = _number(inputs, "outer_radius_mm") / 1000.0
    shape = inputs.get("shape") or "ring"
    if shape not in ("ring", "solid_disk"):
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "shape must be ring or solid_disk")
    omega = 2.0 * math.pi * rpm / 60.0
    poisson = _number(inputs, "poisson_ratio", default=DEFAULT_POISSON)
    base = density * omega ** 2 * radius ** 2
    stress = base if shape == "ring" else (3.0 + poisson) / 8.0 * base
    stress_mpa = stress / 1e6
    return _with_safety({
        "angular_velocity_rad_s": round(omega, 2), "tip_speed_m_s": round(omega * radius, 2),
        "hoop_stress_mpa": round(stress_mpa, 3),
        "formula": "ring: sigma = rho w^2 r^2; solid disk: sigma_max = (3 + nu) / 8 rho w^2 R^2",
        "assumptions": ["centrifugal load only; blades add bending loads and the fluid adds pressure",
                        "use the creep or fatigue limit at service temperature as allowable_stress_mpa"],
    }, stress_mpa, inputs)


def part_mass(inputs):
    volume = _number(inputs, "volume_mm3")
    area = _number(inputs, "surface_area_mm2")
    wall = _number(inputs, "wall_thickness_mm")
    infill = _number(inputs, "infill_percent", positive=False)
    density = _number(inputs, "density_g_cm3")
    if infill > 100:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "infill_percent must be 0..100")
    shell = min(volume, area * wall)
    solid = shell + (volume - shell) * infill / 100.0
    mass = solid / 1000.0 * density
    return {
        "shell_volume_mm3": round(shell, 1), "printed_volume_mm3": round(solid, 1), "mass_g": round(mass, 2),
        "effective_density_g_cm3": round(mass / (volume / 1000.0), 3),
        "formula": "m = rho (V_shell + (V - V_shell) * infill), V_shell = min(V, A * t)",
        "assumptions": ["shell thickness is the same on walls, top and bottom", "supports and brim not included"],
    }


def thermal_expansion(inputs):
    length = _number(inputs, "length_mm")
    delta = _number(inputs, "delta_t_c", positive=False)
    coefficient = _number(inputs, "cte_1e6_per_k")
    change = length * coefficient * 1e-6 * delta
    return {"length_change_mm": round(change, 4), "formula": "dL = L * alpha * dT",
            "assumptions": ["free expansion, linear coefficient constant over the range"]}


def hole_compensation(inputs):
    nominal = _number(inputs, "nominal_mm")
    measured = _number(inputs, "measured_mm")
    feature = inputs.get("feature") or "hole"
    if feature not in ("hole", "outer"):
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "feature must be hole or outer")
    error = measured - nominal
    offset = error / 2.0 if feature == "hole" else -error / 2.0
    current = _number(inputs, "current_xy_offset_mm", positive=False, default=0.0)
    return {
        "dimension_error_mm": round(error, 4), "xy_offset_change_mm": round(offset, 4),
        "suggested_xy_offset_mm": round(current + offset, 4),
        "formula": "hole: delta = (measured - nominal) / 2; outer: delta = (nominal - measured) / 2",
        "assumptions": ["xy_offset moves every contour: opening holes also shrinks outer dimensions",
                        "measure a printed sample; shrinkage depends on material and orientation"],
    }


FORMULAS = {
    "gear_lewis_bending": (gear_lewis_bending, "torque_nm, module_mm, teeth, face_width_mm[, allowable_stress_mpa]"),
    "shaft_torsion": (shaft_torsion, "torque_nm, diameter_mm[, inner_diameter_mm, allowable_stress_mpa]"),
    "rotating_hoop_stress": (rotating_hoop_stress,
                             "density_g_cm3, rpm, outer_radius_mm[, shape ring|solid_disk, poisson_ratio, allowable_stress_mpa]"),
    "part_mass": (part_mass, "volume_mm3, surface_area_mm2, wall_thickness_mm, infill_percent, density_g_cm3"),
    "thermal_expansion": (thermal_expansion, "length_mm, delta_t_c, cte_1e6_per_k"),
    "hole_compensation": (hole_compensation, "nominal_mm, measured_mm[, feature hole|outer, current_xy_offset_mm]"),
}


def calculate(formula, inputs):
    entry = FORMULAS.get(formula)
    if entry is None:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "unknown formula %s; formulas: %s" % (
            formula, ", ".join(sorted(FORMULAS))))
    if not isinstance(inputs, dict):
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "inputs must be an object: %s" % entry[1])
    try:
        result = entry[0](inputs)
    except OperationError as error:
        raise OperationError(error.code, "%s (%s needs %s)" % (error.message, formula, entry[1]))
    return dict(result, formula_name=formula, inputs=inputs)
