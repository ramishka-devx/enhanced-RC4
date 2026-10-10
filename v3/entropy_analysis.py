import math
from collections import Counter
from scipy.stats import chisquare


def shannon_entropy(data: bytes) -> float:
    """
    Compute the Shannon entropy (bits per byte) of a byte sequence.

    Maximum value is 8.0, indicating a perfectly uniform distribution.

    Parameters
    ----------
    data : bytes
        Byte sequence to analyse.

    Returns
    -------
    float
        Entropy in bits per symbol.
    """
    n      = len(data)
    counts = Counter(data)
    entropy = -sum(
        (c / n) * math.log2(c / n)
        for c in counts.values()
    )
    return entropy


def chi_square(data: bytes):
    """
    Chi-square uniformity test against a uniform distribution over
    all 256 byte values.

    For a good cipher output:
    - The chi-square statistic should be close to 255 (the number of
      degrees of freedom).
    - The p-value should be > 0.05, indicating the distribution is
      not significantly different from uniform.

    Parameters
    ----------
    data : bytes
        Byte sequence to analyse.

    Returns
    -------
    chi : float
        Chi-square test statistic.
    p : float
        p-value.
    """
    counts   = Counter(data)
    observed = [counts.get(i, 0) for i in range(256)]
    expected = [len(data) / 256]  * 256
    chi, p   = chisquare(observed, expected)
    return chi, p


def bit_independence(data: bytes) -> float:
    """
    Estimate bit-independence by computing the fraction of bits equal
    to 1 across the entire byte sequence.  Ideal value is 0.5 (each
    bit is equally likely to be 0 or 1).

    Parameters
    ----------
    data : bytes
        Byte sequence to analyse.

    Returns
    -------
    float
        Fraction of bits set to 1 (ideal ≈ 0.5).
    """
    total_bits = len(data) * 8
    ones       = sum(bin(b).count("1") for b in data)
    return ones / total_bits
