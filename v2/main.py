"""
main.py
-------
Comparison of Standard RC4 vs Enhanced RC4 (chaos-augmented KSA + Drop-3072).

Both ciphers use Drop-3072 for a fair apples-to-apples comparison.

Evaluation metrics:
  - Shannon entropy      (ideal: 8.0 bits/byte)
  - Chi-square test      (p > 0.05 → statistically uniform)
  - Bit-independence     (ideal: 0.5)
  - Correctness check    (encrypt → decrypt roundtrip)
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rc4          import RC4
from enhanced_rc4 import EnhancedRC4
from entropy_analysis import shannon_entropy, chi_square, bit_independence


# ── Configuration ─────────────────────────────────────────────────────────────

KEY      = b"nivralabs"
DROP     = 3072          # applied to both ciphers for a fair comparison

# 1 MB test corpus: all 256 byte values repeated equally
DATA     = bytes(range(256)) * 4096


# ── Standard RC4 (with Drop-3072) ─────────────────────────────────────────────

rc4      = RC4(list(KEY), drop=DROP)
enc_rc4  = rc4.encrypt(DATA)

# Verify decryption
rc4_dec  = RC4(list(KEY), drop=DROP)
assert rc4_dec.decrypt(enc_rc4) == DATA, "RC4 decryption mismatch!"

# ── Enhanced RC4 ───────────────────────────────────────────────────────────────

enc_obj       = EnhancedRC4(list(KEY))           # generates fresh random seed
enc_enhanced  = enc_obj.encrypt(DATA)
chaos_seed    = enc_obj.seed_bytes               # must be stored/sent with ciphertext

# Verify decryption (pass the same seed)
dec_obj       = EnhancedRC4(list(KEY), seed_bytes=chaos_seed)
assert dec_obj.decrypt(enc_enhanced) == DATA, "Enhanced RC4 decryption mismatch!"

print("✓ Correctness check passed for both ciphers.\n")

# ── Entropy ────────────────────────────────────────────────────────────────────

e_rc4      = shannon_entropy(enc_rc4)
e_enhanced = shannon_entropy(enc_enhanced)

print("Shannon Entropy (bits/byte)  — ideal: 8.0")
print(f"  RC4 (Drop-{DROP}):          {e_rc4:.9f}")
print(f"  Enhanced RC4 (Drop-{DROP}): {e_enhanced:.9f}")
print()

# ── Chi-Square ─────────────────────────────────────────────────────────────────

chi_rc4, p_rc4           = chi_square(enc_rc4)
chi_enhanced, p_enhanced = chi_square(enc_enhanced)

print("Chi-Square Uniformity Test   — p > 0.05 means uniform (good)")
print(f"  RC4          Chi: {chi_rc4:.4f}   p: {p_rc4:.6f}")
print(f"  Enhanced RC4 Chi: {chi_enhanced:.4f}   p: {p_enhanced:.6f}")
print()

# ── Bit Independence ───────────────────────────────────────────────────────────

bi_rc4      = bit_independence(enc_rc4)
bi_enhanced = bit_independence(enc_enhanced)

print("Bit Independence             — ideal: 0.5")
print(f"  RC4:          {bi_rc4:.6f}")
print(f"  Enhanced RC4: {bi_enhanced:.6f}")
print()

# ── Summary table ─────────────────────────────────────────────────────────────

print("─" * 56)
print(f"{'Metric':<28} {'RC4':>12} {'Enhanced':>12}")
print("─" * 56)
print(f"{'Entropy (bits/byte)':<28} {e_rc4:>12.6f} {e_enhanced:>12.6f}")
print(f"{'Chi-square statistic':<28} {chi_rc4:>12.4f} {chi_enhanced:>12.4f}")
print(f"{'Chi-square p-value':<28} {p_rc4:>12.6f} {p_enhanced:>12.6f}")
print(f"{'Bit independence':<28} {bi_rc4:>12.6f} {bi_enhanced:>12.6f}")
print(f"{'Drop-N applied':<28} {DROP:>12} {EnhancedRC4.DROP:>12}")
print("─" * 56)
print(f"  Chaos seed (hex): {chaos_seed.hex()}")
print()

# ── Histograms ─────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

for ax, enc, label in [
    (axes[0], enc_rc4,      f"Standard RC4 (Drop-{DROP})"),
    (axes[1], enc_enhanced, f"Enhanced RC4 (Chaos KSA + Drop-{EnhancedRC4.DROP})"),
]:
    counts, edges, patches = ax.hist(
        np.frombuffer(enc, dtype=np.uint8),
        bins=256,
        color="#4C72B0",
        edgecolor="none",
        alpha=0.85,
    )
    ax.axhline(
        len(enc) / 256,
        color="red",
        linewidth=1.2,
        linestyle="--",
        label="Ideal uniform",
    )
    ax.set_title(label, fontsize=11)
    ax.set_xlabel("Byte value (0–255)")
    ax.set_ylabel("Frequency")
    ax.legend(fontsize=9)
    ax.set_xlim(0, 255)

plt.suptitle(
    "Keystream Byte Distribution Comparison",
    fontsize=13,
    fontweight="bold",
)
plt.tight_layout()
plt.savefig("comparison.png", dpi=150)
plt.close()

print("✓ Histogram saved to comparison.png")
