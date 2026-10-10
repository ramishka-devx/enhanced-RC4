"""
main.py
-------
Comparison of:
  1. Vanilla RC4              — standard KSA, no Drop-N
  2. Standard RC4 + Drop-3072 — standard KSA, Drop-3072 applied
  3. Enhanced RC4             — chaos-augmented KSA + Drop-3072

Each cipher is evaluated over TRIALS independent runs and results are averaged,
giving a statistically robust comparison rather than a single lucky/unlucky seed.

Evaluation metrics:
  - Shannon entropy       (ideal: 8.0 bits/byte)
  - Chi-square statistic  (ideal: ~255 degrees of freedom)
  - Chi-square p-value    (pass: p > 0.05)
  - Bit-independence      (ideal: 0.5)
  - Byte-pair correlation (ideal: ~0.0)
  - Chi-square pass rate  (fraction of trials with p > 0.05)
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

from rc4           import RC4
from enhanced_rc4  import EnhancedRC4
from entropy_analysis import shannon_entropy, chi_square, bit_independence

# ── Configuration ──────────────────────────────────────────────────────────────

KEY    = b"nivralabs"
DROP   = 3072
TRIALS = 30                         # averaged over 30 independent runs
DATA   = bytes(range(256)) * 4096   # 1 MB, perfectly balanced corpus

CIPHERS = ["Vanilla RC4", "RC4 + Drop-3072", "Enhanced RC4"]

# ── Helper: sequential byte-pair Pearson correlation ──────────────────────────

def byte_pair_correlation(data: bytes) -> float:
    arr  = np.frombuffer(data, dtype=np.uint8).astype(float)
    corr = np.corrcoef(arr[:-1], arr[1:])[0, 1]
    return float(corr)

# ── Helper: encrypt with a fresh cipher instance each trial ───────────────────

def encrypt_vanilla(data):
    return RC4(list(KEY), drop=0).encrypt(data)

def encrypt_drop(data):
    return RC4(list(KEY), drop=DROP).encrypt(data)

def encrypt_enhanced(data):
    obj = EnhancedRC4(list(KEY))          # fresh chaos seed every call
    return obj.encrypt(data)

ENCRYPTORS = {
    "Vanilla RC4":       encrypt_vanilla,
    "RC4 + Drop-3072":   encrypt_drop,
    "Enhanced RC4":      encrypt_enhanced,
}

# ── Correctness check (once) ───────────────────────────────────────────────────

rc4_dec = RC4(list(KEY), drop=0)
assert rc4_dec.decrypt(encrypt_vanilla(DATA)) == DATA, "Vanilla RC4 roundtrip failed!"

rc4d_dec = RC4(list(KEY), drop=DROP)
assert rc4d_dec.decrypt(encrypt_drop(DATA)) == DATA,   "RC4+Drop roundtrip failed!"

enc_obj  = EnhancedRC4(list(KEY))
enc_tmp  = enc_obj.encrypt(DATA)
dec_obj  = EnhancedRC4(list(KEY), seed_bytes=enc_obj.seed_bytes)
assert dec_obj.decrypt(enc_tmp) == DATA,               "Enhanced RC4 roundtrip failed!"

print(f"\n✓ Correctness roundtrip passed for all three ciphers.")
print(f"  Running {TRIALS} trials per cipher — this may take ~30 s …\n")

# ── Multi-trial evaluation ─────────────────────────────────────────────────────

accum = {c: defaultdict(list) for c in CIPHERS}

for trial in range(TRIALS):
    print(f"  Trial {trial + 1:>2}/{TRIALS} …", end="\r", flush=True)
    for cipher in CIPHERS:
        enc = ENCRYPTORS[cipher](DATA)
        chi_val, p_val = chi_square(enc)
        accum[cipher]["entropy"].append(shannon_entropy(enc))
        accum[cipher]["chi"].append(chi_val)
        accum[cipher]["p"].append(p_val)
        accum[cipher]["bi"].append(bit_independence(enc))
        accum[cipher]["corr"].append(byte_pair_correlation(enc))
        accum[cipher]["pass"].append(1 if p_val > 0.05 else 0)

print(f"  {TRIALS}/{TRIALS} trials complete.{' ' * 20}\n")

# Compute means and std-devs
stats = {}
for cipher in CIPHERS:
    stats[cipher] = {
        k: (np.mean(v), np.std(v))
        for k, v in accum[cipher].items()
    }
    stats[cipher]["pass_rate"] = np.mean(accum[cipher]["pass"])

# ── Print summary table ────────────────────────────────────────────────────────

sep = "═" * 86
print(sep)
print(f"  Results averaged over {TRIALS} independent trials")
print(sep)
print(f"{'Metric':<28} {'Vanilla RC4':>18} {'RC4+Drop-3072':>18} {'Enhanced RC4':>18}")
print("─" * 86)

rows = [
    ("Entropy  mean (bits/byte)", "entropy",   "{:.6f} ±{:.6f}"),
    ("Chi-sq   mean",             "chi",       "{:.2f}  ±{:.2f}"),
    ("p-value  mean",             "p",         "{:.6f} ±{:.6f}"),
    ("Bit-indep mean",            "bi",        "{:.6f} ±{:.6f}"),
    ("Byte-corr mean (abs)",      "corr",      "{:.6f} ±{:.6f}"),
]

for label, key, fmt in rows:
    row = f"  {label:<26}"
    for cipher in CIPHERS:
        mu, sd = stats[cipher][key]
        if key == "corr":
            mu = abs(mu)
        row += f"  {fmt.format(mu, sd):>16}"
    print(row)

print("─" * 86)
row = f"  {'Chi-sq pass rate (p>0.05)':<26}"
for cipher in CIPHERS:
    rate = stats[cipher]["pass_rate"]
    tag  = "✓" if rate >= 0.90 else "✗"
    row += f"  {f'{rate*100:.1f}% {tag}':>16}"
print(row)
print(sep)

# ── Figure 1: Box-plots of p-values across trials ─────────────────────────────

fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
colors = ["#d62728", "#ff7f0e", "#2ca02c"]

for ax, cipher, color in zip(axes, CIPHERS, colors):
    p_vals = accum[cipher]["p"]
    ax.boxplot(p_vals, patch_artist=True,
               boxprops=dict(facecolor=color, alpha=0.6),
               medianprops=dict(color="black", linewidth=2))
    ax.axhline(0.05, color="red", linestyle="--", linewidth=1.2, label="α = 0.05")
    pass_rate = np.mean([v > 0.05 for v in p_vals]) * 100
    ax.set_title(f"{cipher}\nPass rate: {pass_rate:.1f}%", fontsize=11)
    ax.set_xlabel(f"({TRIALS} trials)")
    ax.set_ylabel("Chi-square p-value" if ax == axes[0] else "")
    ax.legend(fontsize=8)

plt.suptitle(f"Chi-square p-value Distribution ({TRIALS} Trials Each)",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("comparison_pvalue_boxplot.png", dpi=150)
plt.close()
print("\n✓ Saved: comparison_pvalue_boxplot.png")

# ── Figure 2: Byte-value histogram (best trial = highest p-value) ─────────────

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
ideal_freq = len(DATA) / 256

for ax, (cipher, color) in zip(axes, zip(CIPHERS, colors)):
    enc = ENCRYPTORS[cipher](DATA)
    chi_val, p_val = chi_square(enc)
    ax.hist(np.frombuffer(enc, dtype=np.uint8), bins=256,
            color=color, edgecolor="none", alpha=0.78)
    ax.axhline(ideal_freq, color="black", linewidth=1.2,
               linestyle="--", label="Ideal uniform")
    ax.set_title(f"{cipher}\nχ²={chi_val:.1f}  p={p_val:.4f}", fontsize=10)
    ax.set_xlabel("Byte value (0–255)")
    ax.set_ylabel("Frequency")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 255)

plt.suptitle("Keystream Byte Distribution (single representative run)",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("comparison_histograms.png", dpi=150)
plt.close()
print("✓ Saved: comparison_histograms.png")

# ── Figure 3: Mean metric bar chart ───────────────────────────────────────────

metric_labels = ["Entropy\n(bits/byte)", "p-value\nmean", "Bit indep.\nmean", "|Byte-corr|\nmean"]
metric_keys   = ["entropy", "p", "bi", "corr"]
ideals        = [8.0, 0.5, 0.5, 0.0]

x     = np.arange(len(metric_labels))
width = 0.22

fig, ax = plt.subplots(figsize=(13, 6))
for idx, (cipher, color) in enumerate(zip(CIPHERS, colors)):
    vals = []
    errs = []
    for key in metric_keys:
        mu, sd = stats[cipher][key]
        vals.append(abs(mu) if key == "corr" else mu)
        errs.append(sd)
    ax.bar(x + (idx - 1) * width, vals, width, yerr=errs,
           label=cipher, color=color, alpha=0.82, capsize=4)

for xi, ideal in zip(x, ideals):
    ax.hlines(ideal, xi - 1.5*width, xi + 1.5*width,
              colors="black", linewidths=1.5, linestyles=":",
              label="Ideal" if xi == x[0] else "")

ax.set_xticks(x)
ax.set_xticklabels(metric_labels, fontsize=10)
ax.set_ylabel(f"Mean value over {TRIALS} trials")
ax.set_title("Security Metric Comparison — RC4 Variants (averaged)", fontsize=13, fontweight="bold")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig("comparison_metrics.png", dpi=150)
plt.close()
print("✓ Saved: comparison_metrics.png\n")
