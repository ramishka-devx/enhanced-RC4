import numpy as np
from scipy.integrate import solve_ivp
import hashlib

g = 9.81

m1 = 1.0
m2 = 1.0

L1 = 1.0
L2 = 1.0


def equations(t, y):

    theta1, omega1, theta2, omega2 = y

    delta = theta2 - theta1

    dtheta1 = omega1
    dtheta2 = omega2

    den1 = L1 * (
        2 * m1
        + m2
        - m2 * np.cos(2 * theta1 - 2 * theta2)
    )

    den2 = L2 * (
        2 * m1
        + m2
        - m2 * np.cos(2 * theta1 - 2 * theta2)
    )

    domega1 = (
        -g * (2 * m1 + m2) * np.sin(theta1)
        - m2 * g * np.sin(theta1 - 2 * theta2)
        - 2
        * np.sin(delta)
        * m2
        * (
            omega2**2 * L2
            + omega1**2 * L1 * np.cos(delta)
        )
    ) / den1

    domega2 = (
        2
        * np.sin(delta)
        * (
            omega1**2 * L1 * (m1 + m2)
            + g * (m1 + m2) * np.cos(theta1)
            + omega2**2 * L2 * m2 * np.cos(delta)
        )
    ) / den2

    return [
        dtheta1,
        domega1,
        dtheta2,
        domega2
    ]


def simulate():

    initial_state = [
        np.pi / 2,
        0,
        np.pi / 2 + 0.001,
        0
    ]

    solution = solve_ivp(
        equations,
        [0, 30],
        initial_state,
        t_eval=np.linspace(0, 30, 10000)
    )

    return solution


def generate_entropy_bytes(length=256):

    solution = simulate()

    theta1 = solution.y[0]
    theta2 = solution.y[2]

    entropy = bytearray()

    for t1, t2 in zip(theta1, theta2):

        data = (
            f"{t1:.12f}"
            f"{t2:.12f}"
        ).encode()

        digest = hashlib.sha256(data).digest()

        entropy.extend(digest)

        if len(entropy) >= length:
            break

    return bytes(entropy[:length])