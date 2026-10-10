from double_pendulum import generate_entropy_bytes


class EnhancedRC4:
    """
    Enhanced RC4 stream cipher.

    Improvements over standard RC4
    --------------------------------
    1. Chaos-augmented KSA: each KSA swap uses
       ``key[i % len(key)] XOR chaos[i]`` instead of the raw key byte,
       injecting high-entropy chaotic perturbations into the initial
       state permutation.
    2. Drop-3072: the first 3072 bytes of keystream are discarded,
       eliminating the well-known RC4 early-byte bias weakness.

    Parameters
    ----------
    key : list[int]
        Key bytes as a list of integers 0-255.
    seed_bytes : bytes, optional
        8-byte chaos seed.  Pass the same seed for decryption.
        When None (default, encryption mode) a fresh os.urandom(8)
        seed is generated automatically.

    Attributes
    ----------
    seed_bytes : bytes
        The chaos seed used.  **Must be stored/transmitted alongside
        the ciphertext** so the receiver can reconstruct the same
        chaos stream during decryption.
    """

    DROP = 3072

    def __init__(self, key: list, seed_bytes: bytes = None):
        self.key   = key
        self.S     = list(range(256))

        # Generate chaotic entropy; store seed for the caller
        self.chaos, self.seed_bytes = generate_entropy_bytes(
            256, seed_bytes
        )

        self._ksa()

    def _ksa(self):
        """Chaos-augmented Key Scheduling Algorithm."""
        j = 0
        for i in range(256):
            # XOR key byte with chaos byte before mixing
            j = (
                j
                + self.S[i]
                + (self.key[i % len(self.key)] ^ self.chaos[i])
            ) % 256
            self.S[i], self.S[j] = self.S[j], self.S[i]

    def _prga(self):
        """Pseudo-Random Generation Algorithm (generator)."""
        i = 0
        j = 0
        S = self.S[:]           # work on a copy so the object is reusable
        while True:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            yield S[(S[i] + S[j]) % 256]

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt plaintext, returning (ciphertext, seed_bytes)."""
        stream = self._prga()
        # Drop-3072: discard early biased bytes
        for _ in range(self.DROP):
            next(stream)
        ciphertext = bytes(p ^ next(stream) for p in plaintext)
        return ciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt ciphertext.

        The EnhancedRC4 instance must have been constructed with the
        same key AND the same seed_bytes that were used during encryption.
        """
        return self.encrypt(ciphertext)
