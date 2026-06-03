import os
import numpy as np
import hashlib
from scipy.integrate import solve_ivp

# Physical constants
g  = 9.81
m1 = 1.0
m2 = 1.0
L1 = 1.0
L2 = 1.0


def equations(t, y):
    """Lagrangian equations of motion for a double pendulum."""
    theta1, omega1, theta2, omega2 = y

    delta  = theta2 - theta1
    cos_2d = np.cos(2 * theta1 - 2 * theta2)
    sin_d  = np.sin(delta)

    den1 = L1 * (2 * m1 + m2 - m2 * cos_2d)
    den2 = L2 * (2 * m1 + m2 - m2 * cos_2d)

    domega1 = (
        -g * (2 * m1 + m2) * np.sin(theta1)
        - m2 * g * np.sin(theta1 - 2 * theta2)
        - 2 * sin_d * m2 * (
            omega2 ** 2 * L2
            + omega1 ** 2 * L1 * np.cos(delta)
        )
    ) / den1

    domega2 = (
        2 * sin_d * (
            omega1 ** 2 * L1 * (m1 + m2)
            + g * (m1 + m2) * np.cos(theta1)
            + omega2 ** 2 * L2 * m2 * np.cos(delta)
        )
    ) / den2

    return [omega1, domega1, omega2, domega2]


def simulate(seed_bytes: bytes = None):
    """
    Simulate the double pendulum.

    Parameters
    ----------
    seed_bytes : bytes, optional
        8 raw bytes used to perturb the initial conditions, making
        each simulation unique.  If None, os.urandom(8) is used so
        that every call produces a fresh chaotic trajectory.

    Returns
    -------
    solution : OdeResult
        scipy solve_ivp solution with .y containing
        [theta1, omega1, theta2, omega2] over time.
    seed_bytes : bytes
        The seed that was used.  Callers must persist/transmit this
        so the receiver can reproduce the same chaos stream.
    """
    if seed_bytes is None:
        seed_bytes = os.urandom(8)

    # Map 8 random bytes to a small float perturbation in (-0.05, +0.05)
    seed_int   = int.from_bytes(seed_bytes, "big")
    seed_float = (seed_int / (2 ** 64 - 1) - 0.5) * 0.1   # range ≈ ±0.05

    initial_state = [
        np.pi / 2 + seed_float,   # theta1
        0.0,                       # omega1
        np.pi / 2 + 0.001 + seed_float,  # theta2 (small offset keeps chaos)
        0.0,                       # omega2
    ]

    solution = solve_ivp(
        equations,
        [0, 30],
        initial_state,
        t_eval=np.linspace(0, 30, 10000),
        method="RK45",
        rtol=1e-9,
        atol=1e-9,
    )

    return solution, seed_bytes


def generate_entropy_bytes(length: int = 256, seed_bytes: bytes = None):
    """
    Generate `length` high-entropy bytes from a chaotic double-pendulum
    simulation.

    Parameters
    ----------
    length : int
        Number of entropy bytes to produce.
    seed_bytes : bytes, optional
        Explicit seed; generated via os.urandom(8) when omitted.

    Returns
    -------
    entropy : bytes
        `length` pseudo-random bytes derived from the chaotic trajectory.
    seed_bytes : bytes
        The seed used (must be stored/transmitted for decryption).
    """
    solution, seed_bytes = simulate(seed_bytes)

    theta1 = solution.y[0]
    theta2 = solution.y[2]

    entropy = bytearray()

    for t1, t2 in zip(theta1, theta2):
        data   = f"{t1:.15f}{t2:.15f}".encode()
        digest = hashlib.sha256(data).digest()
        entropy.extend(digest)
        if len(entropy) >= length:
            break

    return bytes(entropy[:length]), seed_bytes
