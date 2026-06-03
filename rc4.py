class RC4:

    def __init__(self, key):

        self.key = key
        self.S = list(range(256))

        self.ksa()

    def ksa(self):

        j = 0

        for i in range(256):

            j = (
                j
                + self.S[i]
                + self.key[i % len(self.key)]
            ) % 256

            self.S[i], self.S[j] = (
                self.S[j],
                self.S[i]
            )

    def prga(self):

        i = 0
        j = 0

        while True:

            i = (i + 1) % 256

            j = (
                j + self.S[i]
            ) % 256

            self.S[i], self.S[j] = (
                self.S[j],
                self.S[i]
            )

            K = self.S[
                (
                    self.S[i]
                    + self.S[j]
                )
                % 256
            ]

            yield K

    def encrypt(self, plaintext):

        stream = self.prga()

        return bytes(
            p ^ next(stream)
            for p in plaintext
        )