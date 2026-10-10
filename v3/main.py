"""
main.py
-------
Comparison of:
  1. Vanilla RC4        — standard KSA, no Drop-N
  2. Standard RC4 Drop-3072 — standard KSA, Drop-3072 applied
  3. Enhanced RC4       — chaos-augmented KSA + Drop-3072

Showing the full progression makes the chaos-augmentation benefit visible.

Evaluation metrics:
  - Shannon entropy      (ideal: 8.0 bits/byte)
  - Chi-square test      (p > 0.05 → statistically uniform)
  - Bit-independence     (ideal: 0.5)
  - Byte-pair correlation (ideal: ~0.0)
  - Correctness check    (encrypt → decrypt roundtrip)
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter

from rc4           import RC4
from enhanced_rc4  import EnhancedRC4
from entropy_analysis import shannon_entropy, chi_square, bit_independence


# ── Configuration ──────────────────────────────────────────────────────────────

KEY  = b"nivralabs"
DROP = 3072

# 1 MB test corpus: all 256 byte values repeated equally → maximally fair
DATA = bytes(range(256)) * 4096

BOLD  = "\033[1m"
GREEN = "\033[92m"
CYAN  = "\033[96m"
RED   = "\033[91m"
RESET = "\033[0m"

# ── Helper: sequential byte-pair correlation ───────────────────────────────────

def byte_pair_correlation(data: bytes) -> float:
    """
    Pearson correlation between consecutive byte pairs.
    Ideal: ~0.0  (uncorrelated).  High values reveal keystream structure.
    """
    arr = np.frombuffer(data, dtype=np.uint8).astype(float)
    x, y = arr[:-1], arr[1:]
    corr = np.corrcoef(x, y)[0, 1]
    return float(corr)


# ── 1. Vanilla RC4 (no drop) ───────────────────────────────────────────────────

rc4_vanilla     = RC4(list(KEY), drop=0)
enc_vanilla     = rc4_vanilla.encrypt(DATA)
rc4_vanilla_dec = RC4(list(KEY), drop=0)
assert rc4_vanilla_dec.decrypt(enc_vanilla) == DATA, "Vanilla RC4 roundtrip failed!"

# ── 2. Standard RC4 with Drop-3072 ────────────────────────────────────────────

rc4_drop     = RC4(list(KEY), drop=DROP)
enc_drop     = rc4_drop.encrypt(DATA)
rc4_drop_dec = RC4(list(KEY), drop=DROP)
assert rc4_drop_dec.decrypt(enc_drop) == DATA, "RC4+Drop roundtrip failed!"

# ── 3. Enhanced RC4 (chaos KSA + Drop-3072) ────────────────────────────────────

enc_obj      = EnhancedRC4(list(KEY))
enc_enhanced = enc_obj.encrypt(DATA)
chaos_seed   = enc_obj.seed_bytes

dec_obj = EnhancedRC4(list(KEY), seed_bytes=chaos_seed)
assert dec_obj.decrypt(enc_enhanced) == DATA, "Enhanced RC4 roundtrip failed!"

print(f"\n{GREEN}✓ Correctness roundtrip passed for all three ciphers.{RESET}\n")

# ── Compute all metrics ────────────────────────────────────────────────────────

results = {}
for label, enc in [
    ("Vanilla RC4",        enc_vanilla),
    ("RC4 + Drop-3072",    enc_drop),
    ("Enhanced RC4",       enc_enhanced),
]:
    results[label] = {
        "entropy": shannon_entropy(enc),
        "chi":     chi_square(enc),
        "bi":      bit_independence(enc),
        "corr":    byte_pair_correlation(enc),
    }

# ── Print results ──────────────────────────────────────────────────────────────

W = 22   # column width

def fmt_p(p):
    colour = GREEN if p > 0.05 else RED
    return f"{colour}{p:.6f}{RESET}"

def fmt_bi(v):
    colour = GREEN if abs(v - 0.5) < 0.002 else RED
    return f"{colour}{v:.6f}{RESET}"

def fmt_corr(v):
    colour = GREEN if abs(v) < 0.002 else RED
    return f"{colour}{v:.6f}{RESET}"

sep = "─" * 80
print(sep)
print(f"{'Metric':<30} {'Vanilla RC4':>{W}} {'RC4+Drop-3072':>{W}} {'Enhanced RC4':>{W}}")
print(sep)

for label, key, ideal, fmtfn in [
    ("Entropy (bits/byte)",    "entropy", "8.0",   lambda v: f"{v:.6f}"),
    ("Chi-square statistic",   "chi",     "~255",  lambda v: f"{v[0]:.4f}"),
    ("Chi-square p-value",     "chi",     ">0.05", lambda v: fmt_p(v[1])),
    ("Bit independence",       "bi",      "0.5",   lambda v: fmt_bi(v)),
    ("Byte-pair correlation",  "corr",    "~0.0",  lambda v: fmt_corr(v)),
]:
    row = f"{label:<30}"
    for cipher in ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]:
        val = results[cipher][key]
        row += f" {fmtfn(val):>{W}}"
    print(row)

print(sep)
print(f"\n  Chaos seed (hex): {CYAN}{chaos_seed.hex()}{RESET}")
print(f"  Drop-N applied  : {DROP} (RC4+Drop and Enhanced RC4)\n")

# ── Plain summary table (no ANSI) for log files ───────────────────────────────

print("=" * 80)
print(f"{'Metric':<30} {'Vanilla RC4':>18} {'RC4+Drop-3072':>18} {'Enhanced RC4':>18}")
print("=" * 80)
for label, key, getter in [
    ("Entropy (bits/byte)",   "entropy", lambda v: f"{v:.9f}"),
    ("Chi-square statistic",  "chi",     lambda v: f"{v[0]:.4f}"),
    ("Chi-square p-value",    "chi",     lambda v: f"{v[1]:.6f}"),
    ("Bit independence",      "bi",      lambda v: f"{v:.6f}"),
    ("Byte-pair correlation", "corr",    lambda v: f"{v:.8f}"),
]:
    row = f"{label:<30}"
    for cipher in ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]:
        val = results[cipher][key]
        row += f" {getter(val):>18}"
    print(row)
print("=" * 80)

# ── Figure 1: Byte-value histograms (3 subplots) ──────────────────────────────

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

ideal_freq = len(DATA) / 256

for ax, (label, enc) in zip(axes, [
    ("Vanilla RC4\n(no Drop)",                enc_vanilla),
    (f"Standard RC4\n(Drop-{DROP})",          enc_drop),
    (f"Enhanced RC4\n(Chaos KSA + Drop-{DROP})", enc_enhanced),
]):
    ax.hist(
        np.frombuffer(enc, dtype=np.uint8),
        bins=256,
        color="#4C72B0",
        edgecolor="none",
        alpha=0.82,
    )
    ax.axhline(ideal_freq, color="red", linewidth=1.4,
               linestyle="--", label="Ideal uniform")
    chi_val, p_val = chi_square(enc)
    ax.set_title(f"{label}\nχ²={chi_val:.1f}  p={p_val:.4f}", fontsize=10)
    ax.set_xlabel("Byte value (0–255)")
    ax.set_ylabel("Frequency")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 255)

plt.suptitle("Keystream Byte Distribution: Vanilla RC4 → RC4+Drop → Enhanced RC4",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("comparison_histograms.png", dpi=150)
plt.close()
print("\n✓ Saved: comparison_histograms.png")

# ── Figure 2: Metric bar-chart comparison ─────────────────────────────────────

metrics_plot = {
    "Entropy\n(bits/byte)": [results[c]["entropy"] for c in
                              ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]],
    "Chi-square\np-value":  [results[c]["chi"][1] for c in
                              ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]],
    "Bit\nIndependence":    [results[c]["bi"] for c in
                              ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]],
    "Byte-pair\nCorrelation\n(abs)": [abs(results[c]["corr"]) for c in
                              ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]],
}

labels    = ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]
colors    = ["#d62728", "#ff7f0e", "#2ca02c"]
x         = np.arange(len(metrics_plot))
width     = 0.22

fig, ax = plt.subplots(figsize=(13, 6))
for idx, (cipher, colour) in enumerate(zip(labels, colors)):
    vals = [v[idx] for v in metrics_plot.values()]
    bars = ax.bar(x + (idx - 1) * width, vals, width,
                  label=cipher, color=colour, alpha=0.85)

ideals = [8.0, 0.05, 0.5, 0.0]
for xi, ideal in zip(x, ideals):
    ax.hlines(ideal, xi - 1.5*width, xi + 1.5*width,
              colors="black", linewidths=1.2, linestyles=":",
              label="Ideal" if xi == x[0] else "")

ax.set_xticks(x)
ax.set_xticklabels(list(metrics_plot.keys()), fontsize=10)
ax.set_ylabel("Metric value")
ax.set_title("Security Metric Comparison: RC4 Variants", fontsize=13, fontweight="bold")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig("comparison_metrics.png", dpi=150)
plt.close()
print("✓ Saved: comparison_metrics.png")

# ── Figure 3: Sequential byte scatter (correlation visualisation) ──────────────

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
sample_n  = 5000   # plot first 5 000 byte-pairs for clarity

for ax, (label, enc) in zip(axes, [
    ("Vanilla RC4",         enc_vanilla),
    (f"RC4 + Drop-{DROP}", enc_drop),
    ("Enhanced RC4",        enc_enhanced),
]):
    arr  = np.frombuffer(enc[:sample_n + 1], dtype=np.uint8)
    corr = np.corrcoef(arr[:-1].astype(float), arr[1:].astype(float))[0, 1]
    ax.scatter(arr[:-1], arr[1:], s=0.5, alpha=0.3, color="#4C72B0")
    ax.set_title(f"{label}\nr = {corr:.5f}", fontsize=10)
    ax.set_xlabel("byte[i]")
    ax.set_ylabel("byte[i+1]")
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)

plt.suptitle("Sequential Byte Correlation  (ideal: random scatter, r ≈ 0)",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig("comparison_correlation.png", dpi=150)
plt.close()
print("✓ Saved: comparison_correlation.png\n")
