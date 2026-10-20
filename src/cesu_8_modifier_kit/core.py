"""Core CESU-8 decoder.

CESU-8 is a compatibility encoding that represents supplementary (non-BMP)
characters as two consecutive 3-byte UTF-8-like sequences, one for the
high surrogate and one for the low surrogate, mirroring the UTF-16
surrogate-pair mechanism. Standard UTF-8 forbids encoding surrogates, so
CESU-8 is needed to read byte streams produced by older Java and CORBA
systems.

Interpretation chosen: a well-formed CESU-8 byte sequence contains only
1-byte, 2-byte, and 3-byte encodings (never 4-byte sequences). This is
strict CESU-8 as described in the Unicode Technical Report. If a 4-byte
UTF-8 sequence is encountered it is treated as an error.

Two strictness rules are enforced:
  - Lone surrogates (a high surrogate without a following low, or a low
    surrogate not preceded by a high) raise CESU8DecodeError.
  - Overlong encodings (e.g. a NUL byte encoded as a 2-byte sequence)
    raise CESU8DecodeError.

Nothing is relaxed or best-effort: an error means the input is not valid
CESU-8 and the caller gets a clear exception.
"""


class CESU8DecodeError(ValueError):
    """Raised when a byte sequence is not valid CESU-8."""


def _is_high_surrogate(cp: int) -> bool:
    return 0xD800 <= cp <= 0xDBFF


def _is_low_surrogate(cp: int) -> bool:
    return 0xDC00 <= cp <= 0xDFFF


def _decode_one(buf: bytes, pos: int):
    """Decode a single CESU-8 code unit starting at *pos*.

    Returns a tuple of (code_point, new_position, is_surrogate).
    *is_surrogate* is True when the decoded code point is a surrogate
    (D800–DFFF); the caller assembles surrogate pairs.
    """
    b0 = buf[pos]

    if b0 < 0x80:
        return b0, pos + 1, False

    if b0 < 0xC0:
        # Continuation byte where a lead is expected.
        raise CESU8DecodeError(
            f"unexpected continuation byte 0x{b0:02X} at position {pos}"
        )

    if b0 < 0xE0:
        # 2-byte sequence: U+0080..U+07FF
        if pos + 1 >= len(buf):
            raise CESU8DecodeError(f"truncated 2-byte sequence at position {pos}")
        b1 = buf[pos + 1]
        if b1 & 0xC0 != 0x80:
            raise CESU8DecodeError(
                f"invalid continuation byte 0x{b1:02X} at position {pos + 1}"
            )
        cp = ((b0 & 0x1F) << 6) | (b1 & 0x3F)
        if cp < 0x80:
            raise CESU8DecodeError(
                f"overlong encoding for U+{cp:04X} at position {pos}"
            )
        return cp, pos + 2, False

    if b0 < 0xF0:
        # 3-byte sequence. In CESU-8 this is used both for BMP characters
        # and for surrogate code points (D800–DFFF), which are never used
        # in plain UTF-8.
        if pos + 2 >= len(buf):
            raise CESU8DecodeError(f"truncated 3-byte sequence at position {pos}")
        b1 = buf[pos + 1]
        b2 = buf[pos + 2]
        if b1 & 0xC0 != 0x80:
            raise CESU8DecodeError(
                f"invalid continuation byte 0x{b1:02X} at position {pos + 1}"
            )
        if b2 & 0xC0 != 0x80:
            raise CESU8DecodeError(
                f"invalid continuation byte 0x{b2:02X} at position {pos + 2}"
            )
        cp = ((b0 & 0x0F) << 12) | ((b1 & 0x3F) << 6) | (b2 & 0x3F)
        if cp < 0x800:
            raise CESU8DecodeError(
                f"overlong encoding for U+{cp:04X} at position {pos}"
            )
        is_surrogate = _is_high_surrogate(cp) or _is_low_surrogate(cp)
        return cp, pos + 3, is_surrogate

    raise CESU8DecodeError(
        f"4-byte sequences are not valid CESU-8 (byte 0x{b0:02X} at position {pos})"
    )


def decode(data) -> str:
    """Decode CESU-8 bytes into a Python string.

    *data* may be ``bytes`` or ``bytearray``.

    A well-formed CESU-8 stream uses 3-byte sequences to carry surrogate
    code points; a supplementary character is two such sequences in order:
    high surrogate then low surrogate. This function reassembles them into
    the corresponding astral code point.

    Raises ``CESU8DecodeError`` for any malformation, including lone
    surrogates, overlong encodings, truncated sequences, and 4-byte UTF-8
    sequences (which CESU-8 does not use).
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(
            f"expected bytes or bytearray, got {type(data).__name__}"
        )

    buf = bytes(data)
    out = []
    pos = 0
    length = len(buf)

    while pos < length:
        cp, new_pos, is_surrogate = _decode_one(buf, pos)

        if is_surrogate:
            if _is_high_surrogate(cp):
                # Must be followed by a low surrogate.
                if new_pos >= length:
                    raise CESU8DecodeError(
                        f"trailing high surrogate U+{cp:04X} at end of input"
                    )
                lo_cp, after, lo_is_surr = _decode_one(buf, new_pos)
                if not lo_is_surr or not _is_low_surrogate(lo_cp):
                    raise CESU8DecodeError(
                        f"high surrogate U+{cp:04X} not followed by low surrogate"
                    )
                # Reassemble the supplementary code point.
                full = 0x10000 + (((cp & 0x3FF) << 10) | (lo_cp & 0x3FF))
                out.append(chr(full))
                pos = after
            else:
                # Low surrogate without a preceding high surrogate.
                raise CESU8DecodeError(
                    f"unpaired low surrogate U+{cp:04X} at position {pos}"
                )
        else:
            out.append(chr(cp))
            pos = new_pos

    return "".join(out)
