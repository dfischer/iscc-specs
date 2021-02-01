# -*- coding: utf-8 -*-
"""Functions that measure haming distance of compact binary codes"""
from typing import Union
from bitarray import bitarray
from bitarray.util import count_xor, hex2ba
from iscc.codec import Code, read_header, decode_base32


# ISCC code in various possible representations
Icode = Union[str, bytes, int, Code]


def distance(a, b, mixed=False):
    # type: (Icode, Icode, bool) -> int
    """Calculate hamming distance for singular ISCC component codes of same type.

    I mixed is true, we allow for comparison of hashes with different length and
    subtypes. If components have different length we compute the hamming distance of
    the shorter code with the prefix of the longer code.

    ISCC Codes can be supplied in these formats:
    - Code: a codec.Code object
    - str: base32 encoded ISCC component(including header).
    - bytes: raw byte digest of ISCC component (without header).
    - int: integer representation of ISCC component (without header).
    """
    if isinstance(a, Code):
        return distance_code(a.code, b.code, mixed=mixed)
    if isinstance(a, str):
        return distance_code(a, b, mixed=mixed)
    if isinstance(a, bytes):
        if mixed:
            nbytes = min((len(a), len(b)))
            a, b = a[:nbytes], b[:nbytes]
        return distance_bytes(a, b)
    if isinstance(a, int):
        return distance_int(a, b)


def distance_code(a, b, mixed=False):
    # type: (str, str, bool) -> int
    """
    Calculate hamming distance for ISCC component codes.

    Component type, subtype, version and lenght must be the same if mixed is 'False'.
    If mixed is 'True' we allow for different subtypes and length. In case codes are of
    different length and mixed is 'true' we calculate common length prefix distance.
    """
    a, b = decode_base32(a), decode_base32(b)
    a, b = read_header(a), read_header(b)
    if mixed:
        assert a[0] == b[0] and a[2] == b[2], "Maintype and version do not match."
        # calculate common prefix length distance
        nbytes = min((a[3], b[3])) // 8
        return distance_bytes(a[-1][:nbytes], b[-1][:nbytes])
    else:
        assert a[:-1] == b[:-1], "Code header values do not match."
        # calculate strict distance (ignore subsequent codes)
        a = a[-1][: a[3] // 8]
        b = b[-1][: b[3] // 8]
        return distance_bytes(a, b)


def distance_int(a, b):
    # type: (int, int) -> int
    """Calculate hamming dinstance for integer hashes."""
    return bin(a ^ b).count("1")


def distance_bytes(a, b):
    # type: (bytes, bytes) -> int
    """Calculate hamming distance for bytes hash digests of equal length."""
    return count_xor(hex2ba(a.hex()), hex2ba(b.hex()))


def distance_hex(a, b):
    # type: (str, str) -> int
    """Calculate hamming distnace for hex encoded hashes of equal length."""
    return count_xor(hex2ba(a), hex2ba(b))


def distance_ba(a, b):
    # type: (bitarray, bitarray) -> int
    """Calculate hamming distance for bitarray objects of equal length."""
    return count_xor(a, b)
