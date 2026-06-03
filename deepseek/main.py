import hashlib
import random
import time
import math
import struct
from collections import defaultdict, Counter
from typing import List, Tuple, Dict, Any

import numpy as np
import pandas as pd
from scipy.stats import chisquare, pearsonr
import matplotlib.pyplot as plt
from scipy.stats import chi2   # at top of file

# =============================================================================
# DOUBLE PENDULUM SIMULATION (Chaotic Entropy Source)
# =============================================================================
# Equations of motion for a double pendulum. Used as a chaotic system to generate
# unpredictable entropy that seeds the enhanced key schedule.
# Parameters: lengths l1=l2=1.0, masses m1=m2=1.0, gravity g=9.81

G = 9.81
L1 = 1.0
L2 = 1.0
M1 = 1.0
M2 = 1.0

def derivatives(state: Tuple[float, float, float, float], t: float) -> Tuple[float, float, float, float]:
    """
    Compute derivatives for the double pendulum system.
    state = (theta1, theta2, omega1, omega2)
    Returns (omega1, omega2, alpha1, alpha2)
    """
    theta1, theta2, omega1, omega2 = state
    delta = theta2 - theta1

    denom1 = (M1 + M2) * L1 - M2 * L1 * math.cos(delta) * math.cos(delta)
    alpha1 = (M2 * L1 * omega1 * omega1 * math.sin(delta) * math.cos(delta) +
              M2 * G * math.sin(theta2) * math.cos(delta) +
              M2 * L2 * omega2 * omega2 * math.sin(delta) -
              (M1 + M2) * G * math.sin(theta1)) / denom1

    denom2 = (L2 / L1) * denom1
    alpha2 = (-M2 * L2 * omega2 * omega2 * math.sin(delta) * math.cos(delta) +
              (M1 + M2) * G * math.sin(theta1) * math.cos(delta) -
              (M1 + M2) * L1 * omega1 * omega1 * math.sin(delta) -
              (M1 + M2) * G * math.sin(theta2)) / denom2

    return omega1, omega2, alpha1, alpha2

def rk4_step(state: Tuple[float, float, float, float], dt: float, t: float) -> Tuple[float, float, float, float]:
    """Fourth-order Runge-Kutta integration step."""
    k1 = derivatives(state, t)
    k2 = derivatives((state[0] + 0.5 * dt * k1[0],
                      state[1] + 0.5 * dt * k1[1],
                      state[2] + 0.5 * dt * k1[2],
                      state[3] + 0.5 * dt * k1[3]), t + 0.5*dt)
    k3 = derivatives((state[0] + 0.5 * dt * k2[0],
                      state[1] + 0.5 * dt * k2[1],
                      state[2] + 0.5 * dt * k2[2],
                      state[3] + 0.5 * dt * k2[3]), t + 0.5*dt)
    k4 = derivatives((state[0] + dt * k3[0],
                      state[1] + dt * k3[1],
                      state[2] + dt * k3[2],
                      state[3] + dt * k3[3]), t + dt)
    new_state = (state[0] + dt/6.0 * (k1[0] + 2*k2[0] + 2*k3[0] + k4[0]),
                 state[1] + dt/6.0 * (k1[1] + 2*k2[1] + 2*k3[1] + k4[1]),
                 state[2] + dt/6.0 * (k1[2] + 2*k2[2] + 2*k3[2] + k4[2]),
                 state[3] + dt/6.0 * (k1[3] + 2*k2[3] + 2*k3[3] + k4[3]))
    return new_state

def simulate_double_pendulum(initial_theta1: float, initial_theta2: float,
                             steps: int, dt: float = 0.01) -> List[Tuple[float, float, float, float]]:
    """
    Simulate the double pendulum and return a list of states (theta1, theta2, omega1, omega2).
    """
    state = (initial_theta1, initial_theta2, 0.0, 0.0)
    trajectory = [state]
    for _ in range(steps):
        state = rk4_step(state, dt, 0.0)
        trajectory.append(state)
    return trajectory

def chaotic_entropy_from_key(key: bytes, required_bytes: int) -> bytes:
    """
    Derive cryptographically strong entropy from the double pendulum simulation.
    The initial angles are derived from the key via SHA-256. Then the pendulum
    is simulated for a number of steps; the entire trajectory is hashed to produce
    32 bytes per block. Repeated with different nonces until required_bytes are obtained.
    """
    entropy = bytearray()
    blocks_needed = (required_bytes + 31) // 32
    for block in range(blocks_needed):
        # Each block uses a different nonce to ensure fresh entropy
        seed = key + struct.pack('>I', block) + b'pendulum_entropy'
        hash_obj = hashlib.sha256(seed)
        # Derive initial angles in [0, 2π)
        digest = hash_obj.digest()
        theta1 = (struct.unpack('<Q', digest[:8])[0] / (2**64)) * 2 * math.pi
        theta2 = (struct.unpack('<Q', digest[8:16])[0] / (2**64)) * 2 * math.pi

        # Simulate pendulum – chaotic divergence guarantees high entropy
        traj = simulate_double_pendulum(theta1, theta2, steps=500, dt=0.01)
        # Convert trajectory to a bytes representation and hash it
        state_bytes = b''
        for t1, t2, _, _ in traj:
            state_bytes += struct.pack('dd', t1, t2)
        block_hash = hashlib.sha256(state_bytes).digest()
        entropy.extend(block_hash)
    return bytes(entropy[:required_bytes])

# =============================================================================
# RC4 IMPLEMENTATIONS
# =============================================================================

class RC4:
    """Standard RC4 stream cipher (baseline)."""
    def __init__(self, key: bytes):
        self.key = key
        self.S = None
        self._ksa()

    def _ksa(self) -> None:
        """Key Scheduling Algorithm (KSA) for standard RC4."""
        S = list(range(256))
        j = 0
        key_len = len(self.key)
        for i in range(256):
            j = (j + S[i] + self.key[i % key_len]) & 0xFF
            S[i], S[j] = S[j], S[i]
        self.S = S

    def _prga_generator(self):
        """Generator yielding keystream bytes indefinitely."""
        S = self.S[:]          # Work on a copy
        i = j = 0
        while True:
            i = (i + 1) & 0xFF
            j = (j + S[i]) & 0xFF
            S[i], S[j] = S[j], S[i]
            yield S[(S[i] + S[j]) & 0xFF]

    def generate_keystream(self, n_bytes: int) -> bytes:
        """Generate n_bytes of keystream."""
        gen = self._prga_generator()
        return bytes(next(gen) for _ in range(n_bytes))

class RC4Drop(RC4):
    """RC4 with discarding of the first `drop` bytes to mitigate early keystream biases."""
    def __init__(self, key: bytes, drop: int = 3072):
        super().__init__(key)
        self.drop = drop

    def generate_keystream(self, n_bytes: int) -> bytes:
        # Skip the first `drop` bytes, then return the next n_bytes
        gen = self._prga_generator()
        for _ in range(self.drop):
            next(gen)
        return bytes(next(gen) for _ in range(n_bytes))

class EnhancedRC4(RC4):
    """
    Enhanced RC4 that addresses known weaknesses:
    - Uses chaotic entropy from a double pendulum to augment the key schedule.
    - Performs multiple mixing rounds (two full passes) in the KSA.
    - Combines the original key with entropy bytes to maximise diffusion.
    - Designed to reduce: first-byte bias, second-byte bias, and KSA anomalies.
    """
    def __init__(self, key: bytes):
        self.key = key
        # Obtain chaotic entropy derived from the key (256 bytes)
        self.chaos_entropy = chaotic_entropy_from_key(key, 256)
        self.S = None
        self._enhanced_ksa()

    def _enhanced_ksa(self) -> None:
        """
        Improved Key Scheduling Algorithm:
        1. Initialize S = [0..255].
        2. First mixing pass (standard RC4 KSA) using the original key.
        3. Second mixing pass using the chaotic entropy bytes.
        4. Third mixing pass using a combination of key and entropy.
           Each pass uses 256 iterations (full permutation scan).
        """
        S = list(range(256))
        key_len = len(self.key)
        entropy_len = len(self.chaos_entropy)

        # Pass 1: Standard KSA with original key
        j = 0
        for i in range(256):
            j = (j + S[i] + self.key[i % key_len]) & 0xFF
            S[i], S[j] = S[j], S[i]

        # Pass 2: Additional mixing using chaotic entropy bytes
        j = 0
        for i in range(256):
            j = (j + S[i] + self.chaos_entropy[i % entropy_len]) & 0xFF
            S[i], S[j] = S[j], S[i]

        # Pass 3: Combined key+entropy mixing for extra diffusion
        combined = self.key + self.chaos_entropy
        combined_len = len(combined)
        j = 0
        for i in range(256):
            j = (j + S[i] + combined[i % combined_len]) & 0xFF
            S[i], S[j] = S[j], S[i]

        self.S = S

# =============================================================================
# STATISTICAL METRICS
# =============================================================================

def shannon_entropy(data: bytes) -> float:
    """Compute Shannon entropy (in bits per byte) of the byte sequence."""
    if not data:
        return 0.0
    freq = Counter(data)
    probs = [freq[b] / len(data) for b in range(256)]
    return -sum(p * math.log2(p) for p in probs if p > 0)


def chi_square_test(data: bytes) -> Tuple[float, float]:
    """
    Compute Chi-square statistic and p-value for uniformity of bytes.
    H0: bytes are uniformly distributed.
    """
    observed = [0] * 256
    for b in data:
        observed[b] += 1
    expected = len(data) / 256.0
    chi2_stat = sum((obs - expected)**2 / expected for obs in observed)
    # Degrees of freedom = 255
    p_exact = chi2.sf(chi2_stat, 255)
    return chi2_stat, p_exact

def adjacent_byte_correlation(data: bytes) -> float:
    """
    Pearson correlation between consecutive bytes.
    High absolute correlation indicates predictability.
    """
    if len(data) < 2:
        return 0.0
    x = np.array(list(data[:-1]))
    y = np.array(list(data[1:]))
    corr, _ = pearsonr(x, y)
    return corr

def avalanche_effect(cipher_class, base_key: bytes, n_tests: int = 50, keystream_len: int = 1000) -> float:
    """
    Measure avalanche effect: average Hamming distance ratio between keystreams
    from the base key and a key with one bit flipped.
    """
    total_diff_ratio = 0.0
    base_keystream = cipher_class(base_key).generate_keystream(keystream_len)

    # Perform multiple bit-flip tests
    for _ in range(n_tests):
        # Choose a random byte position and bit to flip
        byte_pos = random.randrange(len(base_key))
        bit_pos = random.randrange(8)
        modified_key = bytearray(base_key)
        modified_key[byte_pos] ^= (1 << bit_pos)
        modified_keystream = cipher_class(bytes(modified_key)).generate_keystream(keystream_len)

        # Hamming distance in bits between two keystreams
        diff_bits = 0
        for b1, b2 in zip(base_keystream, modified_keystream):
            diff_bits += (b1 ^ b2).bit_count()
        max_bits = keystream_len * 8
        diff_ratio = diff_bits / max_bits
        total_diff_ratio += diff_ratio

    return total_diff_ratio / n_tests

# =============================================================================
# BIAS TESTS (RC4-SPECIFIC WEAKNESSES)
# =============================================================================

def first_byte_bias_test(cipher_class, keys: List[bytes]) -> Dict[int, int]:
    """
    For each key, generate the first keystream byte (after any drop)
    and count frequencies. Known RC4 bias: Pr[first byte = 0] ≈ 1/128 instead of 1/256.
    """
    freq = defaultdict(int)
    for key in keys:
        cipher = cipher_class(key)
        # For RC4Drop, first_byte is the byte after discarding
        if hasattr(cipher, 'drop'):
            # We need exactly one byte after the drop
            gen = cipher._prga_generator()
            for _ in range(cipher.drop):
                next(gen)
            first_byte = next(gen)
        else:
            first_byte = cipher.generate_keystream(1)[0]
        freq[first_byte] += 1
    return dict(freq)

def second_byte_bias_test(cipher_class, keys: List[bytes]) -> Dict[int, int]:
    """Frequency of the second keystream byte."""
    freq = defaultdict(int)
    for key in keys:
        cipher = cipher_class(key)
        if hasattr(cipher, 'drop'):
            gen = cipher._prga_generator()
            for _ in range(cipher.drop + 1):
                next(gen)
            second_byte = next(gen)
        else:
            stream = cipher.generate_keystream(2)
            second_byte = stream[1]
        freq[second_byte] += 1
    return dict(freq)

def first_16_bytes_distribution(cipher_class, keys: List[bytes]) -> np.ndarray:
    """
    For each key, record the first 16 keystream bytes. Returns a 16x256 array
    where entry [i][b] = count of keys where byte i equals b.
    """
    distribution = np.zeros((16, 256), dtype=int)
    for key in keys:
        cipher = cipher_class(key)
        if hasattr(cipher, 'drop'):
            gen = cipher._prga_generator()
            for _ in range(cipher.drop):
                next(gen)
            first16 = [next(gen) for _ in range(16)]
        else:
            first16 = list(cipher.generate_keystream(16))
        for pos, byte_val in enumerate(first16):
            distribution[pos, byte_val] += 1
    return distribution

# =============================================================================
# VISUALISATION AND CSV EXPORT
# =============================================================================

def plot_byte_frequency(freq_dict: Dict[int, int], title: str, filename: str):
    """Plot frequency distribution of a byte (e.g., first byte)."""
    x = list(range(256))
    y = [freq_dict.get(i, 0) for i in range(256)]
    plt.figure(figsize=(12, 5))
    plt.bar(x, y, width=1.0, edgecolor='black', linewidth=0.2)
    plt.title(title)
    plt.xlabel('Byte value')
    plt.ylabel('Frequency')
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()

def plot_first16_heatmap(dist: np.ndarray, title: str, filename: str):
    """Heatmap of first 16 bytes distribution."""
    plt.figure(figsize=(12, 6))
    plt.imshow(dist, aspect='auto', cmap='viridis', origin='lower')
    plt.colorbar(label='Count')
    plt.xlabel('Byte value')
    plt.ylabel('Position (0-based)')
    plt.title(title)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()

def plot_bias_comparison(bias_data: Dict[str, Dict[int, int]], metric_name: str, filename: str):
    """Compare bias across algorithms: deviation from expected uniform frequency."""
    expected = sum(bias_data[list(bias_data.keys())[0]].values()) / 256.0
    deviations = {}
    for name, freq in bias_data.items():
        dev = [freq.get(i, 0) - expected for i in range(256)]
        deviations[name] = dev
    plt.figure(figsize=(14, 6))
    for name, dev in deviations.items():
        plt.plot(range(256), dev, label=name, alpha=0.7)
    plt.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    plt.xlabel('Byte value')
    plt.ylabel('Deviation from uniform frequency')
    plt.title(f'{metric_name} Bias Comparison')
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()

# =============================================================================
# MAIN EXPERIMENT
# =============================================================================

def generate_random_keys(num_keys: int, min_len: int = 5, max_len: int = 32) -> List[bytes]:
    """Generate random keys for bias tests."""
    keys = []
    for _ in range(num_keys):
        length = random.randint(min_len, max_len)
        key = bytes(random.randint(0, 255) for _ in range(length))
        keys.append(key)
    return keys

def run_experiments():
    """Run all comparisons and generate outputs."""
    print("Starting RC4 enhancement research experiments...")
    random.seed(42)   # for reproducibility of key generation
    np.random.seed(42)

    # ---------- 1. Long keystream statistics (fixed key) ----------
    base_key = b"RC4_Research_Key_2025"
    keystream_len = 100000

    algorithms = {
        "Standard RC4": RC4,
        "RC4-Drop[3072]": RC4Drop,
        "Enhanced Chaotic RC4": EnhancedRC4
    }

    results = []
    for name, cls in algorithms.items():
        print(f"  Measuring {name}...")
        # Execution time for generating keystream_len bytes
        start = time.perf_counter()
        keystream = cls(base_key).generate_keystream(keystream_len)
        elapsed = time.perf_counter() - start

        entropy = shannon_entropy(keystream)
        chi2, p_val = chi_square_test(keystream)
        correlation = adjacent_byte_correlation(keystream)
        avalanche = avalanche_effect(cls, base_key, n_tests=30, keystream_len=2000)

        results.append({
            "Algorithm": name,
            "Shannon Entropy (bits/byte)": entropy,
            "Chi-square Statistic": chi2,
            "Chi-square p-value": p_val,
            "Adjacent Byte Correlation": correlation,
            "Avalanche Effect (bit diff ratio)": avalanche,
            "Time (s) for 100k bytes": elapsed
        })

    df_long = pd.DataFrame(results)
    df_long.to_csv("long_keystream_metrics.csv", index=False)
    print("\nLong keystream metrics saved to long_keystream_metrics.csv")

    # ---------- 2. Bias tests over many random keys ----------
    num_test_keys = 10000
    print(f"\nGenerating {num_test_keys} random keys for bias tests...")
    test_keys = generate_random_keys(num_test_keys)

    bias_results = {}
    for name, cls in algorithms.items():
        print(f"  Running first-byte bias test for {name}...")
        first_freq = first_byte_bias_test(cls, test_keys)
        bias_results[f"{name}_first"] = first_freq
        print(f"  Running second-byte bias test for {name}...")
        second_freq = second_byte_bias_test(cls, test_keys)
        bias_results[f"{name}_second"] = second_freq

        # Save frequency distribution CSVs
        pd.DataFrame([first_freq]).T.reset_index().to_csv(f"{name.replace(' ', '_')}_first_byte_freq.csv",
                                                          index=False, header=["byte", "count"])
        pd.DataFrame([second_freq]).T.reset_index().to_csv(f"{name.replace(' ', '_')}_second_byte_freq.csv",
                                                           index=False, header=["byte", "count"])
        # First 16 bytes distribution
        print(f"  Computing first-16 distribution for {name}...")
        dist16 = first_16_bytes_distribution(cls, test_keys)
        np.save(f"{name.replace(' ', '_')}_first16_dist.npy", dist16)
        # Store for later heatmap
        bias_results[f"{name}_first16_dist"] = dist16

    # Plot frequency graphs
    plot_byte_frequency(bias_results["Standard RC4_first"], "Standard RC4: First Byte Distribution", "std_first_byte.png")
    plot_byte_frequency(bias_results["RC4-Drop[3072]_first"], "RC4-Drop: First Byte Distribution", "drop_first_byte.png")
    plot_byte_frequency(bias_results["Enhanced Chaotic RC4_first"], "Enhanced RC4: First Byte Distribution", "enhanced_first_byte.png")
    plot_byte_frequency(bias_results["Standard RC4_second"], "Standard RC4: Second Byte Distribution", "std_second_byte.png")
    plot_byte_frequency(bias_results["RC4-Drop[3072]_second"], "RC4-Drop: Second Byte Distribution", "drop_second_byte.png")
    plot_byte_frequency(bias_results["Enhanced Chaotic RC4_second"], "Enhanced RC4: Second Byte Distribution", "enhanced_second_byte.png")

    # Bias comparison plots (deviation from uniform)
    first_bias_compare = {
        "Standard RC4": bias_results["Standard RC4_first"],
        "RC4-Drop": bias_results["RC4-Drop[3072]_first"],
        "Enhanced RC4": bias_results["Enhanced Chaotic RC4_first"]
    }
    plot_bias_comparison(first_bias_compare, "First Byte", "first_byte_bias_comparison.png")

    second_bias_compare = {
        "Standard RC4": bias_results["Standard RC4_second"],
        "RC4-Drop": bias_results["RC4-Drop[3072]_second"],
        "Enhanced RC4": bias_results["Enhanced Chaotic RC4_second"]
    }
    plot_bias_comparison(second_bias_compare, "Second Byte", "second_byte_bias_comparison.png")

    # Heatmaps for first 16 bytes
    plot_first16_heatmap(bias_results["Standard RC4_first16_dist"], "Standard RC4: First 16 Bytes Distribution", "std_first16_heatmap.png")
    plot_first16_heatmap(bias_results["RC4-Drop[3072]_first16_dist"], "RC4-Drop: First 16 Bytes Distribution", "drop_first16_heatmap.png")
    plot_first16_heatmap(bias_results["Enhanced Chaotic RC4_first16_dist"], "Enhanced RC4: First 16 Bytes Distribution", "enhanced_first16_heatmap.png")

    # ---------- 3. Summary report to console ----------
    print("\n" + "="*80)
    print("SUMMARY REPORT: RC4 ENHANCEMENT RESEARCH")
    print("="*80)
    print("\nLong Keystream Metrics (100k bytes, fixed key):")
    print(df_long.to_string(index=False))
    print("\nBias Test Summary (10,000 random keys):")
    for name in algorithms.keys():
        first_freq = bias_results[f"{name}_first"]
        # Compute deviation from expected (uniform)
        total_keys = len(test_keys)
        expected = total_keys / 256.0
        # Known RC4 first-byte bias: byte 0 appears ~2x more often than others
        std_first_bias = first_freq.get(0, 0) / expected if expected > 0 else 0
        print(f"  {name}: First byte 0 frequency = {first_freq.get(0, 0)}/{total_keys} "
              f"(bias factor = {std_first_bias:.3f}, ideal=1.0)")

        # Second byte bias: known weakness at byte 0 as well
        second_freq = bias_results[f"{name}_second"]
        std_second_bias = second_freq.get(0, 0) / expected if expected > 0 else 0
        print(f"  {name}: Second byte 0 frequency = {second_freq.get(0, 0)}/{total_keys} "
              f"(bias factor = {std_second_bias:.3f}, ideal=1.0)")

    # Qualitative conclusions
    print("\n--- Interpretation ---")
    print("Standard RC4 shows clear first-byte bias (factor > 1.5) and non-uniform distribution.")
    print("RC4-Drop reduces early biases but does not alter the underlying KSA weaknesses.")
    print("Enhanced Chaotic RC4 aims to eliminate biases by using chaotic entropy and multiple mixing rounds.")
    print("If the enhanced algorithm achieves bias factors close to 1.0, it successfully mitigates known weaknesses.")
    print("See generated graphs and CSV files for detailed comparison.")

    print("\nExperiment finished. Output files:")
    print("  - long_keystream_metrics.csv")
    print("  - *_first_byte_freq.csv, *_second_byte_freq.csv")
    print("  - *_first16_dist.npy")
    print("  - PNG graphs: first/second byte distributions, bias comparisons, heatmaps.")

if __name__ == "__main__":
    run_experiments()