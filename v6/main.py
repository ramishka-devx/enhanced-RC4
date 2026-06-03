import math
import random
import hashlib
from collections import Counter
from math import log2


# =====================================================
# DOUBLE PENDULUM CHAOTIC ENTROPY GENERATOR
# =====================================================

class DoublePendulum:
    def __init__(
            self,
            theta1=math.pi / 2,
            theta2=math.pi / 2 + 0.01,
            omega1=0.0,
            omega2=0.0,
            m1=1.0,
            m2=1.0,
            l1=1.0,
            l2=1.0,
            g=9.81):

        self.theta1 = theta1
        self.theta2 = theta2
        self.omega1 = omega1
        self.omega2 = omega2

        self.m1 = m1
        self.m2 = m2

        self.l1 = l1
        self.l2 = l2

        self.g = g

    def step(self, dt):

        m1 = self.m1
        m2 = self.m2
        l1 = self.l1
        l2 = self.l2
        g = self.g

        t1 = self.theta1
        t2 = self.theta2

        w1 = self.omega1
        w2 = self.omega2

        delta = t2 - t1

        den1 = (m1 + m2) * l1 - m2 * l1 * math.cos(delta) ** 2
        den2 = (l2 / l1) * den1

        a1 = (
                m2 * l1 * w1 * w1 * math.sin(delta) * math.cos(delta)
                + m2 * g * math.sin(t2) * math.cos(delta)
                + m2 * l2 * w2 * w2 * math.sin(delta)
                - (m1 + m2) * g * math.sin(t1)
        ) / den1

        a2 = (
                -m2 * l2 * w2 * w2 * math.sin(delta) * math.cos(delta)
                + (m1 + m2)
                * (
                        g * math.sin(t1) * math.cos(delta)
                        - l1 * w1 * w1 * math.sin(delta)
                        - g * math.sin(t2)
                )
        ) / den2

        self.omega1 += a1 * dt
        self.omega2 += a2 * dt

        self.theta1 += self.omega1 * dt
        self.theta2 += self.omega2 * dt

        return (
            self.theta1,
            self.theta2,
            self.omega1,
            self.omega2
        )


# =====================================================
# CHAOTIC KEY GENERATOR
# =====================================================

def generate_chaotic_bytes(length=256):

    p = DoublePendulum(
        theta1=random.uniform(0, math.pi),
        theta2=random.uniform(0, math.pi),
        omega1=random.uniform(-1, 1),
        omega2=random.uniform(-1, 1)
    )

    data = bytearray()

    for _ in range(length * 8):

        t1, t2, w1, w2 = p.step(0.01)

        value = (
                abs(t1 * 1000000)
                + abs(t2 * 1000000)
                + abs(w1 * 1000000)
                + abs(w2 * 1000000)
        )

        b = int(value) & 0xFF

        data.append(b)

    return bytes(data[:length])


# =====================================================
# KEY EXPANSION
# =====================================================

def build_final_key(user_key):

    chaotic = generate_chaotic_bytes(256)

    combined = user_key.encode() + chaotic

    digest = hashlib.sha512(combined).digest()

    for _ in range(10):
        digest = hashlib.sha512(digest + chaotic).digest()

    return digest


# =====================================================
# IMPROVED RC4 KSA
# =====================================================

def improved_ksa(key):

    S = list(range(256))

    key = list(key)

    j = 0

    # Standard KSA
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]

    # Additional mixing rounds
    for round_num in range(8):

        for i in range(256):

            index = (
                    key[(i + round_num) % len(key)]
                    ^ key[(255 - i) % len(key)]
            )

            j = (j + S[i] + index) % 256

            S[i], S[j] = S[j], S[i]

    return S


# =====================================================
# PRGA
# =====================================================

def prga(S):

    i = 0
    j = 0

    while True:

        i = (i + 1) % 256
        j = (j + S[i]) % 256

        S[i], S[j] = S[j], S[i]

        K = S[(S[i] + S[j]) % 256]

        yield K


# =====================================================
# ENCRYPT / DECRYPT
# =====================================================

def encrypt(plaintext, password):

    key = build_final_key(password)

    S = improved_ksa(key)

    stream = prga(S)

    cipher = bytearray()

    for b in plaintext.encode():
        cipher.append(b ^ next(stream))

    return cipher.hex()


def decrypt(cipher_hex, password):

    key = build_final_key(password)

    S = improved_ksa(key)

    stream = prga(S)

    ciphertext = bytes.fromhex(cipher_hex)

    plain = bytearray()

    for b in ciphertext:
        plain.append(b ^ next(stream))

    return plain.decode(errors="ignore")


# =====================================================
# ENTROPY TEST
# =====================================================

def shannon_entropy(data):

    if isinstance(data, str):
        data = data.encode()

    freq = Counter(data)

    total = len(data)

    entropy = 0

    for count in freq.values():

        p = count / total

        entropy -= p * log2(p)

    return entropy


# =====================================================
# FREQUENCY ANALYSIS
# =====================================================

def frequency_analysis(data):

    if isinstance(data, str):
        data = data.encode()

    freq = Counter(data)

    total = len(data)

    print("\nFrequency Analysis")

    for byte, count in sorted(freq.items())[:20]:

        print(
            f"{byte:3d} : "
            f"{count:5d} "
            f"({100 * count / total:.2f}%)"
        )


# =====================================================
# KEYSTREAM RANDOMNESS TEST
# =====================================================

def generate_keystream(password, size=100000):

    key = build_final_key(password)

    S = improved_ksa(key)

    stream = prga(S)

    return bytes(next(stream) for _ in range(size))


def randomness_report(password):

    ks = generate_keystream(password)

    entropy = shannon_entropy(ks)

    print("\n========== RANDOMNESS REPORT ==========")

    print("Keystream Size :", len(ks))
    print("Entropy        :", entropy)

    if entropy > 7.95:
        print("Result         : Excellent")
    elif entropy > 7.8:
        print("Result         : Good")
    else:
        print("Result         : Weak")

    frequency_analysis(ks)


# =====================================================
# DEMO
# =====================================================

if __name__ == "__main__":

    print("Enhanced RC4 Using Chaotic Double Pendulum")
    print("-----------------------------------------")

    password = input("Password : ")

    plaintext = input("Message  : ")

    ciphertext = encrypt(plaintext, password)

    recovered = decrypt(ciphertext, password)

    print("\nCiphertext:")
    print(ciphertext)

    print("\nRecovered:")
    print(recovered)

    print("\nPlaintext Entropy :",
          shannon_entropy(plaintext))

    print("Cipher Entropy    :",
          shannon_entropy(bytes.fromhex(ciphertext)))

    randomness_report(password)