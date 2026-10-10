import numpy as np
import matplotlib.pyplot as plt

from rc4 import RC4
from enhanced_rc4 import EnhancedRC4

from entropy_analysis import (
    shannon_entropy,
    chi_square
)

key = b"nivralabs"

# 1 MB test data

data = bytes(range(256)) * 4096

# Standard RC4

rc4 = RC4(list(key))

enc1 = rc4.encrypt(data)

# Enhanced RC4

enhanced = EnhancedRC4(list(key))

enc2 = enhanced.encrypt(data)

# Entropy

e1 = shannon_entropy(enc1)
e2 = shannon_entropy(enc2)

print("RC4 Entropy")
print(e1)

print()

print("Enhanced RC4 Entropy")
print(e2)

# Chi Square

chi1, p1 = chi_square(enc1)
chi2, p2 = chi_square(enc2)

print()
print("RC4")

print("Chi:", chi1)
print("P:", p1)

print()

print("Enhanced RC4")

print("Chi:", chi2)
print("P:", p2)

# Histogram

plt.figure(figsize=(10, 5))

plt.hist(
    np.frombuffer(enc1, dtype=np.uint8),
    bins=256
)

plt.title("RC4 Distribution")

plt.savefig("rc4.png")

plt.close()

plt.figure(figsize=(10, 5))

plt.hist(
    np.frombuffer(enc2, dtype=np.uint8),
    bins=256
)

plt.title("Enhanced RC4 Distribution")

plt.savefig("enhanced_rc4.png")

plt.close()


