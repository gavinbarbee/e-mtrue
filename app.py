from __future__ import annotations

import random
from typing import Any

from flask import Flask, render_template, request

from physics import RocketInputs, generate_fix_suggestions, run_full_analysis


app = Flask(__name__)


ELON_QUOTES = [
    "I think it is important to reason from first principles rather than by analogy. - Elon Musk",
    "Boil things down to the most fundamental truths and reason up from there. - Elon Musk",
    "First principles is kind of a physics way of looking at the world. - Elon Musk",
    "Physics is really nothing more than the search for ultimate simplicity. - Elon Musk",
    "The scientific method is all about not fooling yourself. - Elon Musk",
]


ESSENTIAL_FLOAT_FIELDS = {
    "body_length_m": "Body tube length (m)",
    "body_diameter_m": "Body diameter (m)",
    "dry_mass_kg": "Dry mass (kg)",
    "propellant_mass_kg": "Propellant mass (kg)",
    "motor_avg_thrust_n": "Average motor thrust (N)",
    "burn_time_s": "Burn time (s)",
}

OPTIONAL_FLOAT_FIELDS = {
    "nose_length_m": ("Nose cone length (m)", None),
    "fin_root_chord_m": ("Fin root chord (m)", None),
    "fin_tip_chord_m": ("Fin tip chord (m)", None),
    "fin_span_m": ("Fin span (m)", None),
    "fin_sweep_m": ("Fin sweep (m)", None),
    "fin_leading_edge_from_nose_m": ("Fin leading edge position (m)", None),
    "drag_coefficient": ("Drag coefficient Cd", 0.55),
    "launch_angle_deg": ("Launch angle (deg)", 90.0),
    "air_density_kg_m3": ("Air density (kg/m^3)", 1.225),
    "sim_apogee_m": ("Simulator apogee (m)", None),
    "sim_max_velocity_m_s": ("Simulator max velocity (m/s)", None),
    "sim_stability_calibers": ("Simulator stability margin (cal)", None),
}

POSITIVE_ESSENTIAL_FIELDS = {
    "body_length_m",
    "body_diameter_m",
    "dry_mass_kg",
    "propellant_mass_kg",
    "motor_avg_thrust_n",
    "burn_time_s",
}


def _parse_required_float(
    form: dict[str, str],
    key: str,
    label: str,
    errors: list[str],
    min_value: float = 0.0,
    allow_equal_min: bool = False,
) -> float:
    value = form.get(key, "").strip()
    if not value:
        errors.append(f"{label} is required.")
        return 0.0
    try:
        parsed = float(value)
    except ValueError:
        errors.append(f"{label} must be a number.")
        return 0.0
    is_invalid = parsed < min_value if allow_equal_min else parsed <= min_value
    if is_invalid:
        comparator = "greater than or equal to" if allow_equal_min else "greater than"
        errors.append(f"{label} must be {comparator} {min_value}.")
    return parsed


def _parse_optional_float(
    form: dict[str, str], key: str, label: str, errors: list[str], default: float | None
) -> float | None:
    value = form.get(key, "").strip()
    if value == "":
        return default
    try:
        return float(value)
    except ValueError:
        errors.append(f"{label} must be a number when provided.")
        return default


def _parse_fin_count(form: dict[str, str], errors: list[str]) -> int:
    value = form.get("fin_count", "").strip()
    if not value:
        errors.append("Fin count is required.")
        return 0
    try:
        parsed = int(value)
    except ValueError:
        errors.append("Fin count must be an integer.")
        return 0
    if parsed < 3:
        errors.append("Fin count should be at least 3 for a stable fin set.")
    return parsed


def _initial_form_data() -> dict[str, str]:
    return {
        "body_length_m": "1.6",
        "body_diameter_m": "0.102",
        "dry_mass_kg": "2.1",
        "propellant_mass_kg": "0.55",
        "motor_avg_thrust_n": "220",
        "burn_time_s": "2.0",
        "drag_coefficient": "0.55",
        "launch_angle_deg": "90",
        "air_density_kg_m3": "1.225",
        "fin_count": "4",
    }


def _resolve_optional_geometry(
    essential: dict[str, float], optionals: dict[str, float | None]
) -> dict[str, float]:
    body_length = essential["body_length_m"]
    diameter = essential["body_diameter_m"]

    nose_length = optionals["nose_length_m"] or (0.2 * body_length)
    fin_root = optionals["fin_root_chord_m"] or (1.4 * diameter)
    fin_tip = optionals["fin_tip_chord_m"] or (0.7 * diameter)
    fin_span = optionals["fin_span_m"] or (1.1 * diameter)
    fin_sweep = optionals["fin_sweep_m"] or (0.4 * diameter)
    fin_le = optionals["fin_leading_edge_from_nose_m"] or (nose_length + 0.7 * body_length)

    total_length = nose_length + body_length
    fin_le = max(0.0, min(fin_le, total_length - 0.1 * fin_root))

    return {
        "nose_length_m": nose_length,
        "fin_root_chord_m": fin_root,
        "fin_tip_chord_m": fin_tip,
        "fin_span_m": fin_span,
        "fin_sweep_m": fin_sweep,
        "fin_leading_edge_from_nose_m": fin_le,
    }


def _build_simulator_payload(form: dict[str, str], errors: list[str]) -> dict[str, float | None]:
    simulator: dict[str, float | None] = {}
    for key, (label, default) in OPTIONAL_FLOAT_FIELDS.items():
        if not key.startswith("sim_"):
            continue
        simulator[key] = _parse_optional_float(form, key, label, errors, default)
    return simulator


def _build_optional_payload(form: dict[str, str], errors: list[str]) -> dict[str, float | None]:
    optionals: dict[str, float | None] = {}
    for key, (label, default) in OPTIONAL_FLOAT_FIELDS.items():
        if key.startswith("sim_"):
            continue
        optionals[key] = _parse_optional_float(form, key, label, errors, default)
    return optionals


def _build_comparisons(
    analysis: dict[str, Any], simulator: dict[str, float | None]
) -> dict[str, dict[str, float | None]]:
    physics_values = {
        "apogee_m": analysis["trajectory"]["apogee_m"],
        "max_velocity_m_s": analysis["trajectory"]["max_velocity_m_s"],
        "stability_calibers": analysis["stability"]["margin_initial_calibers"],
    }

    sim_values = {
        "apogee_m": simulator.get("sim_apogee_m"),
        "max_velocity_m_s": simulator.get("sim_max_velocity_m_s"),
        "stability_calibers": simulator.get("sim_stability_calibers"),
    }

    comparisons: dict[str, dict[str, float | None]] = {}
    for metric, physics_value in physics_values.items():
        sim_value = sim_values[metric]
        mismatch_pct: float | None = None
        if sim_value is not None and abs(physics_value) > 1e-9:
            mismatch_pct = ((sim_value - physics_value) / physics_value) * 100.0
        comparisons[metric] = {
            "physics": physics_value,
            "simulator": sim_value,
            "mismatch_pct": mismatch_pct,
        }
    return comparisons


def _build_verdict(
    analysis: dict[str, Any], comparisons: dict[str, dict[str, float | None]]
) -> dict[str, str]:
    margin = analysis["stability"]["margin_initial_calibers"]
    energy_residual = abs(analysis["energy"]["residual_pct"])
    mismatch_values = [
        abs(row["mismatch_pct"])
        for row in comparisons.values()
        if row["mismatch_pct"] is not None
    ]
    max_mismatch = max(mismatch_values) if mismatch_values else 0.0

    status = "PASS"
    explanation = "Physics checks are consistent: stable margins, acceptable energy closure, and no major simulator conflict."
    if margin < 1.0 or energy_residual > 25.0 or max_mismatch > 20.0:
        status = "FAIL"
        explanation = "One or more checks are outside safe limits. Adjust geometry, mass, or drag assumptions before trusting this design."
    elif margin < 1.5 or energy_residual > 15.0 or max_mismatch > 10.0:
        status = "WARN"
        explanation = "Design is flyable but uncertain. Tighten inputs and reduce mismatch before final sign-off."

    styles = {
        "PASS": {
            "badge": "bg-emerald-500/20 text-emerald-300 border-emerald-400/40",
            "dot": "bg-emerald-400",
            "title": "E-Mtrue VERIFIED",
        },
        "WARN": {
            "badge": "bg-amber-500/20 text-amber-300 border-amber-400/40",
            "dot": "bg-amber-400",
            "title": "E-Mtrue REVIEW NEEDED",
        },
        "FAIL": {
            "badge": "bg-rose-500/20 text-rose-300 border-rose-400/40",
            "dot": "bg-rose-400",
            "title": "E-Mtrue NOT VERIFIED",
        },
    }

    return {
        "status": status,
        "title": styles[status]["title"],
        "explanation": explanation,
        "badge_class": styles[status]["badge"],
        "dot_class": styles[status]["dot"],
    }


@app.get("/")
def index():
    return render_template(
        "index.html",
        errors=[],
        form_data=_initial_form_data(),
        quote=random.choice(ELON_QUOTES),
    )


@app.post("/calculate")
def calculate():
    form = request.form.to_dict()
    errors: list[str] = []

    essential_values = {
        key: _parse_required_float(
            form,
            key,
            label,
            errors,
            min_value=0.0,
            allow_equal_min=key not in POSITIVE_ESSENTIAL_FIELDS,
        )
        for key, label in ESSENTIAL_FLOAT_FIELDS.items()
    }
    optionals = _build_optional_payload(form, errors)
    simulator = _build_simulator_payload(form, errors)
    fin_count = _parse_fin_count(form, errors) if form.get("fin_count", "").strip() else 4

    launch_angle = optionals["launch_angle_deg"]
    air_density = optionals["air_density_kg_m3"]
    geometry = _resolve_optional_geometry(essential_values, optionals)

    if geometry["fin_leading_edge_from_nose_m"] > (
        geometry["nose_length_m"] + essential_values["body_length_m"]
    ):
        errors.append("Fin leading edge position must lie within total rocket length.")
    if launch_angle is not None and not (0.0 < launch_angle <= 90.0):
        errors.append("Launch angle must be in the range (0, 90] degrees.")
    if air_density is not None and air_density <= 0.0:
        errors.append("Air density must be greater than 0.")
    if geometry["fin_tip_chord_m"] > geometry["fin_root_chord_m"] * 3.0:
        errors.append("Fin tip chord appears too large relative to root chord; verify geometry units.")
    if geometry["fin_span_m"] <= 0.0 or geometry["fin_root_chord_m"] <= 0.0:
        errors.append("Fin dimensions must be greater than 0.")
    if optionals["drag_coefficient"] is not None and optionals["drag_coefficient"] <= 0.0:
        errors.append("Drag coefficient must be greater than 0.")

    if errors:
        return render_template(
            "index.html",
            errors=errors,
            form_data=form,
            quote=random.choice(ELON_QUOTES),
        )

    inputs = RocketInputs(
        **essential_values,
        **geometry,
        fin_count=fin_count,
        drag_coefficient=optionals["drag_coefficient"] if optionals["drag_coefficient"] is not None else 0.55,
        launch_angle_deg=launch_angle if launch_angle is not None else 90.0,
        air_density_kg_m3=air_density if air_density is not None else 1.225,
    )

    analysis = run_full_analysis(inputs)
    comparisons = _build_comparisons(analysis, simulator)
    suggestions = generate_fix_suggestions(analysis, comparisons)
    verdict = _build_verdict(analysis, comparisons)

    return render_template(
        "results.html",
        analysis=analysis,
        simulator=simulator,
        comparisons=comparisons,
        suggestions=suggestions,
        verdict=verdict,
        quote=random.choice(ELON_QUOTES),
    )


if __name__ == "__main__":
    app.run(debug=True)
