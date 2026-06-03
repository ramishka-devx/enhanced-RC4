import math
import time
import hashlib
import random
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chisquare


# ============================================================
# DOUBLE PENDULUM
# ============================================================

class DoublePendulum:

    def __init__(self, key):

        self.g = 9.81
        self.m1 = 1.0
        self.m2 = 1.0
        self.l1 = 1.0
        self.l2 = 1.0

        key_bytes = bytes(key)

        digest = hashlib.sha256(key_bytes).digest()

        self.theta1 = (
            int.from_bytes(digest[0:8], "big")
            / (2**64)
        ) * (2 * math.pi)

        self.theta2 = (
            int.from_bytes(digest[8:16], "big")
            / (2**64)
        ) * (2 * math.pi)

        self.omega1 = (
            int.from_bytes(digest[16:24], "big")
            / (2**64) - 0.5
        ) * 20

        self.omega2 = (
            int.from_bytes(digest[24:32], "big")
            / (2**64) - 0.5
        ) * 20

        self.dt = 0.01


def chaotic_bytes(key, length=4096):

    dp = DoublePendulum(key)

    out = []

    while len(out) < length:

        vals = dp.step()

        data = "".join(
            f"{x:.15f}" for x in vals
        )

        digest = hashlib.sha256(
            data.encode()
        ).digest()

        out.extend(digest)

    return out[:length]


# ============================================================
# STANDARD RC4
# ============================================================

class RC4:

    def __init__(self, key):

        self.S = list(range(256))
        self.i = 0
        self.j = 0

        j = 0

        for i in range(256):
            j = (j + self.S[i] + key[i % len(key)]) % 256
            self.S[i], self.S[j] = self.S[j], self.S[i]

    def next_byte(self):

        self.i = (self.i + 1) % 256
        self.j = (self.j + self.S[self.i]) % 256

        self.S[self.i], self.S[self.j] = self.S[self.j], self.S[self.i]

        return self.S[(self.S[self.i] + self.S[self.j]) % 256]

    def generate(self, n):
        return [self.next_byte() for _ in range(n)]


# ============================================================
# RC4 DROP
# ============================================================

class RC4Drop(RC4):

    def __init__(self, key, drop_n=3072):

        super().__init__(key)

        for _ in range(drop_n):
            self.next_byte()


# ============================================================
# CHAOTIC RC4
# ============================================================

class ChaoticRC4:

    def __init__(self, key):

        self.S = list(range(256))

        chaos = chaotic_bytes(
           key,
           length=4096
        )

        enhanced_key = hashlib.sha256(
            bytes(key) + bytes(chaos[:256])
        ).digest()

        enhanced_key = list(enhanced_key) * 8
        enhanced_key = enhanced_key[:256]

        j = 0

        for round_no in range(4):

            for i in range(256):

                j = (
                    j
                    + self.S[i]
                    + enhanced_key[i]
                    + chaos[(i + round_no) % len(chaos)]
                ) % 256

                self.S[i], self.S[j] = self.S[j], self.S[i]

        self.i = 0
        self.j = 0

        for _ in range(4096):
            self.next_byte()

    def next_byte(self):

        self.i = (self.i + 1) % 256
        self.j = (self.j + self.S[self.i]) % 256

        self.S[self.i], self.S[self.j] = self.S[self.j], self.S[self.i]

        return self.S[(self.S[self.i] + self.S[self.j]) % 256]

    def generate(self, n):
        return [self.next_byte() for _ in range(n)]


# ============================================================
# METRICS
# ============================================================

def entropy(data):

    counts = Counter(data)

    h = 0

    for c in counts.values():
        p = c / len(data)
        h -= p * math.log2(p)

    return h


def chi_square_metric(data):

    counts = np.zeros(256)

    for b in data:
        counts[b] += 1

    expected = np.ones(256) * (len(data) / 256)

    chi, _ = chisquare(counts, expected)

    return chi


def correlation(data):

    x = np.array(data[:-1])
    y = np.array(data[1:])

    return np.corrcoef(x, y)[0, 1]


def avalanche(cipher_class):

    key1 = [ord(c) for c in "SecretKey123"]
    key2 = key1.copy()

    key2[0] ^= 1

    a = cipher_class(key1).generate(4096)
    b = cipher_class(key2).generate(4096)

    changed = 0
    total = 0

    for x, y in zip(a, b):

        diff = x ^ y

        changed += bin(diff).count("1")
        total += 8

    return (changed / total) * 100


def first_byte_bias(cipher_class, runs=5000):

    counts = Counter()

    for i in range(runs):

        key = [random.randint(0, 255) for _ in range(16)]

        first = cipher_class(key).generate(1)[0]

        counts[first] += 1

    return counts


# ============================================================
# VISUALIZATION
# ============================================================

def frequency_graph(data, filename):

    counts = Counter(data)

    x = list(range(256))
    y = [counts.get(i, 0) for i in x]

    plt.figure(figsize=(12, 5))
    plt.bar(x, y)
    plt.title(filename)
    plt.xlabel("Byte Value")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


# ============================================================
# EXPERIMENT
# ============================================================

def evaluate(name, cipher_class):

    key = [ord(c) for c in "ResearchKey2026"]

    start = time.time()

    stream = cipher_class(key).generate(100000)

    elapsed = time.time() - start

    frequency_graph(stream, f"{name}_frequency.png")

    return {
        "Algorithm": name,
        "Entropy": entropy(stream),
        "ChiSquare": chi_square_metric(stream),
        "Correlation": correlation(stream),
        "AvalanchePercent": avalanche(cipher_class),
        "TimeSeconds": elapsed
    }


def main():

    print("Running experiments...")

    results = []

    results.append(evaluate("Standard_RC4", RC4))
    results.append(evaluate("RC4_Drop", RC4Drop))
    results.append(evaluate("Chaotic_RC4", ChaoticRC4))

    df = pd.DataFrame(results)

    print(df)

    df.to_csv("results.csv", index=False)

    print("\nSaved: results.csv")

    print("\nRunning first-byte bias test...")

    bias = first_byte_bias(ChaoticRC4)

    bias_df = pd.DataFrame(
        sorted(bias.items()),
        columns=["Byte", "Count"]
    )

    bias_df.to_csv("first_byte_bias.csv", index=False)

    print("Saved: first_byte_bias.csv")

    print("\nFinished.")


if __name__ == "__main__":
    main()
