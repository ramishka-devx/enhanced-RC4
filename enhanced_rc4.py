from double_pendulum import generate_entropy_bytes


class EnhancedRC4:

    def __init__(self, key):

        self.key = key

        self.S = list(range(256))

        self.chaos = generate_entropy_bytes(256)

        self.ksa()

    def ksa(self):

        j = 0

        for i in range(256):

            chaos_byte = self.chaos[i]

            j = (
                j
                + self.S[i]
                + (
                    self.key[i % len(self.key)]
                    ^ chaos_byte
                )
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

            yield self.S[
                (
                    self.S[i]
                    + self.S[j]
                )
                % 256
            ]

    def encrypt(self, plaintext):

        stream = self.prga()

        # RC4 Drop-3072

        for _ in range(3072):
            next(stream)

        return bytes(
            p ^ next(stream)
            for p in plaintext
        )