"""First-principles rocket calculations for E-Mtrue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import sympy as sp


G0 = 9.80665  # m/s^2


@dataclass(slots=True)
class RocketInputs:
    nose_length_m: float
    body_length_m: float
    body_diameter_m: float
    fin_root_chord_m: float
    fin_tip_chord_m: float
    fin_span_m: float
    fin_sweep_m: float
    fin_count: int
    fin_leading_edge_from_nose_m: float
    dry_mass_kg: float
    propellant_mass_kg: float
    motor_avg_thrust_n: float
    burn_time_s: float
    drag_coefficient: float
    launch_angle_deg: float = 90.0
    air_density_kg_m3: float = 1.225
    simulation_dt_s: float = 0.02
    simulation_max_time_s: float = 120.0


def _fin_normal_force_slope(inputs: RocketInputs) -> float:
    """Barrowman normal-force derivative contribution from fins."""
    mid_chord_sweep = inputs.fin_sweep_m + 0.5 * (
        inputs.fin_tip_chord_m - inputs.fin_root_chord_m
    )
    denom = 1.0 + np.sqrt(
        1.0 + ((2.0 * mid_chord_sweep) / (inputs.fin_root_chord_m + inputs.fin_tip_chord_m)) ** 2
    )
    planform_factor = (
        4.0 * inputs.fin_count * (inputs.fin_span_m / inputs.body_diameter_m) ** 2
    )
    body_interference = 1.0 + (
        inputs.body_diameter_m / (2.0 * inputs.fin_span_m + inputs.body_diameter_m)
    )
    return body_interference * planform_factor / denom


def _fin_cp_location_m(inputs: RocketInputs) -> float:
    """Barrowman fin CP location from nose tip."""
    x_cp_from_fin_le = (
        (inputs.fin_sweep_m / 3.0)
        * ((inputs.fin_root_chord_m + 2.0 * inputs.fin_tip_chord_m) / (inputs.fin_root_chord_m + inputs.fin_tip_chord_m))
        + (1.0 / 6.0)
        * (
            inputs.fin_root_chord_m
            + inputs.fin_tip_chord_m
            - (inputs.fin_root_chord_m * inputs.fin_tip_chord_m) / (inputs.fin_root_chord_m + inputs.fin_tip_chord_m)
        )
    )
    return inputs.fin_leading_edge_from_nose_m + x_cp_from_fin_le


def barrowman_stability(inputs: RocketInputs) -> dict[str, float]:
    """Compute CP, CG and static margin (calibers)."""
    cna_nose = 2.0
    x_cp_nose = (2.0 / 3.0) * inputs.nose_length_m

    cna_fins = _fin_normal_force_slope(inputs)
    x_cp_fins = _fin_cp_location_m(inputs)

    cna_total = cna_nose + cna_fins
    x_cp_total = (cna_nose * x_cp_nose + cna_fins * x_cp_fins) / cna_total

    total_length = inputs.nose_length_m + inputs.body_length_m
    x_cg_structure = 0.5 * total_length
    x_cg_propellant = total_length - 0.25 * inputs.body_length_m
    initial_mass = inputs.dry_mass_kg + inputs.propellant_mass_kg
    x_cg_initial = (
        inputs.dry_mass_kg * x_cg_structure + inputs.propellant_mass_kg * x_cg_propellant
    ) / initial_mass
    x_cg_final = x_cg_structure

    margin_initial_calibers = (x_cp_total - x_cg_initial) / inputs.body_diameter_m
    margin_final_calibers = (x_cp_total - x_cg_final) / inputs.body_diameter_m

    return {
        "cna_nose": cna_nose,
        "cna_fins": cna_fins,
        "x_cp_m": x_cp_total,
        "x_cg_initial_m": x_cg_initial,
        "x_cg_final_m": x_cg_final,
        "margin_initial_calibers": margin_initial_calibers,
        "margin_final_calibers": margin_final_calibers,
    }


def _symbolic_equations() -> dict[str, str]:
    """Symbolic first-principles equations shown on results page."""
    t, m, g, rho, cd, area, v, thrust = sp.symbols("t m g rho cd A v T", positive=True)
    drag = sp.Rational(1, 2) * rho * cd * area * v**2
    accel = (thrust - m * g - drag) / m
    pe = m * g * sp.symbols("h", nonnegative=True)
    return {
        "drag_force": sp.latex(sp.Eq(sp.Symbol("F_D"), drag)),
        "acceleration": sp.latex(sp.Eq(sp.Symbol("a"), accel)),
        "potential_energy": sp.latex(sp.Eq(sp.Symbol("E_p"), pe)),
    }


def simulate_trajectory(inputs: RocketInputs) -> dict[str, Any]:
    """Integrate vertical trajectory using explicit time stepping."""
    dt = inputs.simulation_dt_s
    area = np.pi * (inputs.body_diameter_m * 0.5) ** 2
    propellant_flow_kg_s = inputs.propellant_mass_kg / inputs.burn_time_s
    vertical_component = np.sin(np.deg2rad(inputs.launch_angle_deg))

    t_values = [0.0]
    h_values = [0.0]
    v_values = [0.0]
    m_values = [inputs.dry_mass_kg + inputs.propellant_mass_kg]
    thrust_values = []
    drag_values = []

    thrust_work_j = 0.0
    drag_loss_j = 0.0

    max_steps = int(inputs.simulation_max_time_s / dt)
    for step in range(max_steps):
        t = t_values[-1]
        h = h_values[-1]
        v = v_values[-1]

        propellant_left = max(inputs.propellant_mass_kg - propellant_flow_kg_s * t, 0.0)
        mass = inputs.dry_mass_kg + propellant_left
        thrust = inputs.motor_avg_thrust_n if t <= inputs.burn_time_s else 0.0
        thrust_vertical = thrust * vertical_component

        drag_mag = 0.5 * inputs.air_density_kg_m3 * inputs.drag_coefficient * area * v * v
        drag_force = drag_mag * np.sign(v)

        accel = (thrust_vertical - mass * G0 - drag_force) / mass
        v_next = v + accel * dt
        h_next = h + v_next * dt
        t_next = t + dt

        dh = h_next - h
        thrust_work_j += thrust_vertical * dh
        drag_loss_j += abs(drag_force * dh)

        t_values.append(t_next)
        h_values.append(h_next)
        v_values.append(v_next)
        m_values.append(mass)
        thrust_values.append(thrust_vertical)
        drag_values.append(drag_mag)

        if t_next > inputs.burn_time_s and h_next <= 0.0 and v_next < 0.0:
            h_values[-1] = 0.0
            break

    t_arr = np.array(t_values)
    h_arr = np.array(h_values)
    v_arr = np.array(v_values)

    apogee_idx = int(np.argmax(h_arr))
    apogee_m = float(np.max(h_arr))
    max_velocity_m_s = float(np.max(v_arr))

    return {
        "time_s": t_arr,
        "altitude_m": h_arr,
        "velocity_m_s": v_arr,
        "mass_kg": np.array(m_values),
        "thrust_n": np.array(thrust_values),
        "drag_n": np.array(drag_values),
        "apogee_m": apogee_m,
        "max_velocity_m_s": max_velocity_m_s,
        "time_to_apogee_s": float(t_arr[apogee_idx]),
        "flight_time_s": float(t_arr[-1]),
        "thrust_work_j": thrust_work_j,
        "drag_loss_j": drag_loss_j,
    }


def energy_balance(inputs: RocketInputs, trajectory: dict[str, Any]) -> dict[str, float]:
    """Check if thrust work roughly balances losses + potential energy."""
    apogee_m = trajectory["apogee_m"]
    thrust_work_j = trajectory["thrust_work_j"]
    drag_loss_j = trajectory["drag_loss_j"]

    potential_at_apogee_j = inputs.dry_mass_kg * G0 * apogee_m
    residual_j = thrust_work_j - drag_loss_j - potential_at_apogee_j
    residual_pct = (
        100.0 * residual_j / thrust_work_j if abs(thrust_work_j) > 1e-9 else 0.0
    )

    return {
        "thrust_work_j": thrust_work_j,
        "drag_loss_j": drag_loss_j,
        "potential_at_apogee_j": potential_at_apogee_j,
        "residual_j": residual_j,
        "residual_pct": residual_pct,
    }


def run_full_analysis(inputs: RocketInputs) -> dict[str, Any]:
    """Run all first-principles checks and aggregate results."""
    stability = barrowman_stability(inputs)
    trajectory = simulate_trajectory(inputs)
    energy = energy_balance(inputs, trajectory)

    return {
        "inputs": inputs,
        "stability": stability,
        "trajectory": trajectory,
        "energy": energy,
        "equations": _symbolic_equations(),
    }


def generate_fix_suggestions(
    analysis: dict[str, Any], comparisons: dict[str, dict[str, float | None]]
) -> list[str]:
    """Generate practical physics-based tuning suggestions."""
    stability = analysis["stability"]
    energy = analysis["energy"]
    suggestions: list[str] = []

    margin = stability["margin_initial_calibers"]
    if margin < 1.0:
        suggestions.append(
            "Increase static margin toward 1.5-2.0 calibers: enlarge fin span, move fins further aft, or reduce forward mass."
        )
    elif margin > 3.0:
        suggestions.append(
            "Static margin is high; consider slightly smaller fins to reduce weathercocking while staying above 1.0 caliber."
        )

    apogee_cmp = comparisons.get("apogee_m", {})
    if apogee_cmp.get("mismatch_pct") is not None and abs(apogee_cmp["mismatch_pct"]) > 10.0:
        suggestions.append(
            "Large apogee mismatch suggests drag or mass assumptions are off; verify Cd, frontal area, and propellant mass."
        )

    vel_cmp = comparisons.get("max_velocity_m_s", {})
    if vel_cmp.get("mismatch_pct") is not None and abs(vel_cmp["mismatch_pct"]) > 10.0:
        suggestions.append(
            "Velocity mismatch often indicates thrust-curve assumptions are too simple; replace average thrust with time-resolved motor data."
        )

    if abs(energy["residual_pct"]) > 20.0:
        suggestions.append(
            "Energy residual is large; check burn time, average thrust, and drag coefficient consistency across tools."
        )

    if not suggestions:
        suggestions.append(
            "Physics and simulator are reasonably aligned. Next, tighten uncertainty bands with measured Cd and motor test data."
        )

    return suggestions
