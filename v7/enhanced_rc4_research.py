
"""
enhanced_rc4_research.py

Research project:
Original RC4 vs Enhanced RC4 with Chaotic Double Pendulum Entropy

Requirements:
pip install numpy matplotlib scipy
"""

import math
import random
import hashlib
from collections import Counter
from math import log2
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chisquare, pearsonr


# =====================================================
# ORIGINAL RC4
# =====================================================

class RC4:

    def __init__(self, key: bytes):
        self.S = self.ksa(key)

    def ksa(self, key):
        S = list(range(256))
        j = 0

        for i in range(256):
            j = (j + S[i] + key[i % len(key)]) % 256
            S[i], S[j] = S[j], S[i]

        return S

    def prga(self):
        S = self.S.copy()
        i = 0
        j = 0

        while True:
            i = (i + 1) % 256
            j = (j + S[i]) % 256

            S[i], S[j] = S[j], S[i]

            yield S[(S[i] + S[j]) % 256]

    def keystream(self, n):
        g = self.prga()
        return bytes(next(g) for _ in range(n))


# =====================================================
# DOUBLE PENDULUM
# =====================================================

class DoublePendulum:

    def __init__(self):
        self.theta1 = random.uniform(0.1, 3.0)
        self.theta2 = random.uniform(0.1, 3.0)
        self.omega1 = random.uniform(-1, 1)
        self.omega2 = random.uniform(-1, 1)

        self.m1 = 1.0
        self.m2 = 1.0
        self.l1 = 1.0
        self.l2 = 1.0
        self.g = 9.81

    def step(self, dt):

        delta = self.theta2 - self.theta1

        den1 = (self.m1 + self.m2) * self.l1 - self.m2 * self.l1 * math.cos(delta) ** 2
        den2 = (self.l2 / self.l1) * den1

        a1 = (
            self.m2 * self.l1 * self.omega1**2 * math.sin(delta) * math.cos(delta)
            + self.m2 * self.g * math.sin(self.theta2) * math.cos(delta)
            + self.m2 * self.l2 * self.omega2**2 * math.sin(delta)
            - (self.m1 + self.m2) * self.g * math.sin(self.theta1)
        ) / den1

        a2 = (
            -self.m2 * self.l2 * self.omega2**2 * math.sin(delta) * math.cos(delta)
            + (self.m1 + self.m2)
            * (
                self.g * math.sin(self.theta1) * math.cos(delta)
                - self.l1 * self.omega1**2 * math.sin(delta)
                - self.g * math.sin(self.theta2)
            )
        ) / den2

        self.omega1 += a1 * dt
        self.omega2 += a2 * dt

        self.theta1 += self.omega1 * dt
        self.theta2 += self.omega2 * dt

        return self.theta1, self.theta2, self.omega1, self.omega2


def generate_chaos(n=256):

    p = DoublePendulum()

    out = []

    for _ in range(n):
        t1, t2, w1, w2 = p.step(0.01)

        value = int(
            abs(t1 * 1e6)
            + abs(t2 * 1e6)
            + abs(w1 * 1e6)
            + abs(w2 * 1e6)
        )

        out.append(value % 256)

    return bytes(out)


# =====================================================
# ENHANCED RC4
# =====================================================

class EnhancedRC4:

    def __init__(self, password):

        chaos = generate_chaos(512)

        self.key = hashlib.sha512(
            password.encode() + chaos
        ).digest()

        self.chaos = chaos

        self.S = self.enhanced_ksa()

    def enhanced_ksa(self):

        S = list(range(256))

        j = 0

        for rnd in range(10):

            for i in range(256):

                j = (
                    j
                    + S[i]
                    + self.key[i % len(self.key)]
                    + self.chaos[(i + rnd) % len(self.chaos)]
                ) % 256

                S[i], S[j] = S[j], S[i]

        return S

    def prga(self):

        S = self.S.copy()

        i = 0
        j = 0

        for _ in range(3072):
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]

        while True:

            i = (i + 1) % 256
            j = (j + S[i]) % 256

            S[i], S[j] = S[j], S[i]

            yield S[(S[i] + S[j]) % 256]

    def keystream(self, n):

        g = self.prga()

        return bytes(next(g) for _ in range(n))


# =====================================================
# METRICS
# =====================================================

def entropy(data):

    freq = Counter(data)
    total = len(data)

    h = 0

    for c in freq.values():
        p = c / total
        h -= p * log2(p)

    return h


def chi_square_test(data):

    freq = np.zeros(256)

    for b in data:
        freq[b] += 1

    expected = np.ones(256) * (len(data) / 256)

    stat, _ = chisquare(freq, expected)

    return stat


def avalanche(stream1, stream2):

    diff = 0

    for a, b in zip(stream1, stream2):
        diff += bin(a ^ b).count("1")

    return diff / (len(stream1) * 8) * 100


def correlation(stream1, stream2):

    a = np.array(list(stream1))
    b = np.array(list(stream2))

    return pearsonr(a, b)[0]


# =====================================================
# BIAS TEST
# =====================================================

def first_byte_bias_rc4(samples=10000):

    counter = Counter()

    for i in range(samples):

        key = hashlib.sha256(str(i).encode()).digest()

        rc4 = RC4(key)

        first = rc4.keystream(1)[0]

        counter[first] += 1

    return counter


def first_byte_bias_enhanced(samples=10000):

    counter = Counter()

    for i in range(samples):

        e = EnhancedRC4(str(i))

        first = e.keystream(1)[0]

        counter[first] += 1

    return counter


# =====================================================
# PLOTS
# =====================================================

def plot_frequency(data, filename):

    freq = [0] * 256

    for b in data:
        freq[b] += 1

    plt.figure(figsize=(12, 5))
    plt.bar(range(256), freq)
    plt.title("Byte Frequency Distribution")
    plt.xlabel("Byte")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


# =====================================================
# MAIN EXPERIMENT
# =====================================================

def run_experiment():

    SIZE = 100000

    rc4 = RC4(b"secret123")
    rc4_stream = rc4.keystream(SIZE)

    enhanced = EnhancedRC4("secret123")
    enhanced_stream = enhanced.keystream(SIZE)

    print("\\n==============================")
    print("RC4 COMPARISON REPORT")
    print("==============================")

    e1 = entropy(rc4_stream)
    e2 = entropy(enhanced_stream)

    print(f"Entropy RC4       : {e1:.5f}")
    print(f"Entropy Enhanced  : {e2:.5f}")

    c1 = chi_square_test(rc4_stream)
    c2 = chi_square_test(enhanced_stream)

    print(f"ChiSquare RC4     : {c1:.5f}")
    print(f"ChiSquare Enhanced: {c2:.5f}")

    r1 = RC4(b"secret123").keystream(10000)
    r2 = RC4(b"secret124").keystream(10000)

    er1 = EnhancedRC4("secret123").keystream(10000)
    er2 = EnhancedRC4("secret124").keystream(10000)

    print(f"Avalanche RC4     : {avalanche(r1,r2):.2f}%")
    print(f"Avalanche Enhanced: {avalanche(er1,er2):.2f}%")

    print(f"Correlation RC4   : {correlation(r1,r2):.5f}")
    print(f"Correlation Enh.  : {correlation(er1,er2):.5f}")

    plot_frequency(rc4_stream, "rc4_frequency.png")
    plot_frequency(enhanced_stream, "enhanced_frequency.png")

    bias1 = first_byte_bias_rc4()
    bias2 = first_byte_bias_enhanced()

    plt.figure(figsize=(12,5))
    plt.bar(list(bias1.keys()), list(bias1.values()))
    plt.title("RC4 First Byte Bias")
    plt.tight_layout()
    plt.savefig("rc4_bias.png")
    plt.close()

    plt.figure(figsize=(12,5))
    plt.bar(list(bias2.keys()), list(bias2.values()))
    plt.title("Enhanced RC4 First Byte Bias")
    plt.tight_layout()
    plt.savefig("enhanced_bias.png")
    plt.close()

    print("\\nGenerated Files:")
    print("rc4_frequency.png")
    print("enhanced_frequency.png")
    print("rc4_bias.png")
    print("enhanced_bias.png")


if __name__ == "__main__":
    run_experiment()
