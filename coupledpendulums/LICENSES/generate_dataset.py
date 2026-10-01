"""Rebuild the Artelnics coupled-pendulum dataset deterministically."""

import csv
import math
from pathlib import Path

import numpy as np


g, length, mass, coupling, damping, dt = 9.81, 1.0, 1.0, 0.8, 0.03, 0.01
state = np.array([0.35, -0.20, 0.0, 0.0], dtype=float)


def derivative(value):
    theta_1, theta_2, omega_1, omega_2 = value
    scale = coupling / (mass * length * length)
    return np.array([
        omega_1,
        omega_2,
        -g / length * math.sin(theta_1) - scale * (theta_1 - theta_2) - damping * omega_1,
        -g / length * math.sin(theta_2) - scale * (theta_2 - theta_1) - damping * omega_2,
    ])


output = Path(__file__).resolve().parents[1] / "coupledpendulums.csv"
with output.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream, delimiter=";", lineterminator="\n")
    writer.writerow(["time", "theta_1", "theta_2", "omega_1", "omega_2"])
    for index in range(10_000):
        writer.writerow([f"{index * dt:.2f}", *(f"{item:.10f}" for item in state)])
        k1 = derivative(state)
        k2 = derivative(state + dt * k1 / 2)
        k3 = derivative(state + dt * k2 / 2)
        k4 = derivative(state + dt * k3)
        state = state + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
