class RC4:
    """
    Standard RC4 stream cipher with Drop-N support.

    Parameters
    ----------
    key : list[int]
        Key bytes as a list of integers 0-255.
    drop : int
        Number of initial keystream bytes to discard (Drop-N).
        Defaults to 0 for vanilla RC4; use 3072 to match Enhanced RC4
        for a fair comparison.
    """

    def __init__(self, key: list, drop: int = 0):
        self.key  = key
        self.drop = drop
        self.S    = list(range(256))
        self._ksa()

    def _ksa(self):
        """Key Scheduling Algorithm."""
        j = 0
        for i in range(256):
            j = (
                j
                + self.S[i]
                + self.key[i % len(self.key)]
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
        """Encrypt (or decrypt) plaintext bytes."""
        stream = self._prga()
        # Discard Drop-N bytes
        for _ in range(self.drop):
            next(stream)
        return bytes(p ^ next(stream) for p in plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt ciphertext bytes (identical to encrypt for RC4)."""
        return self.encrypt(ciphertext)
