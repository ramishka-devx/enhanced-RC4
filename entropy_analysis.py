import math

from collections import Counter

from scipy.stats import chisquare


def shannon_entropy(data):

    counts = Counter(data)

    entropy = 0

    for count in counts.values():

        p = count / len(data)

        entropy -= p * math.log2(p)

    return entropy


def chi_square(data):

    counts = Counter(data)

    observed = [
        counts.get(i, 0)
        for i in range(256)
    ]

    expected = [
        len(data) / 256
    ] * 256

    chi, p = chisquare(
        observed,
        expected
    )

    return chi, p