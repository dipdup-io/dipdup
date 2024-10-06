"""
Those functions were taken from https://github.com/starkware-libs/cairo-lang v0.11.0.2
The reference commit: https://github.com/starkware-libs/cairo-lang/commit/c954f154bbab04c3fb27f7598b015a9475fc628e
"""
import hashlib
import math
from typing import Optional

from ecdsa.rfc6979 import generate_k
from sympy.core.numbers import igcdex

EC_ORDER = 0x800000000000010ffffffffffffffffb781126dcae7b2321e66a241adc64d2f


def cpp_div_mod(n: int, m: int, p: int) -> int:
    """
    Finds a nonnegative integer 0 <= x < p such that (m * x) % p == n
    """
    a, b, c = igcdex(m, p)
    assert c == 1
    return (n * a) % p


def cpp_inv_mod_curve_size(x: int) -> int:
    return cpp_div_mod(1, x, EC_ORDER)


def cpp_generate_k_rfc6979(
    msg_hash: int, priv_key: int, seed: Optional[int] = None
) -> int:
    # Pad the message hash, for consistency with the elliptic.js library.
    if 1 <= msg_hash.bit_length() % 8 <= 4 and msg_hash.bit_length() >= 248:
        # Only if we are one-nibble short:
        msg_hash *= 16

    if seed is None:
        extra_entropy = b""
    else:
        extra_entropy = seed.to_bytes(math.ceil(seed.bit_length() / 8), "big")

    return generate_k(
        EC_ORDER,
        priv_key,
        hashlib.sha256,
        msg_hash.to_bytes(math.ceil(msg_hash.bit_length() / 8), "big"),
        extra_entropy=extra_entropy,
    )
