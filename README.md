# cesu_8_modifier_kit

Decodes CESU-8 encoded byte sequences into Python strings, reassembling the surrogate-pair representation of supplementary (non-BMP) characters.

```python
from cesu_8_modifier_kit import decode, CESU8DecodeError

# U+1F600 (😀) in CESU-8: two 3-byte surrogate sequences
data = b"\xed\xa0\x80\xed\xb0\x80"
print(decode(data))  # 😀

try:
    decode(b"\xed\xa0\x80")  # lone high surrogate
except CESU8DecodeError as e:
    print(e)
```

## Why this exists

CESU-8 is a compatibility encoding used historically by Java (modified UTF-8 in `DataInput`/`DataOutput`) and some CORBA systems. Supplementary characters are encoded as two 3-byte sequences carrying a UTF-16 surrogate pair, rather than a single 4-byte UTF-8 sequence. Standard Python `bytes.decode("utf-8")` rejects surrogate encodings and cannot read these streams. This library decodes them.

A strict interpretation is used: input must be well-formed CESU-8. Lone surrogates, overlong encodings, truncated sequences, and 4-byte sequences all raise `CESU8DecodeError`. The decoder does not attempt recovery.

## Edge cases

- A high surrogate sequence (e.g. `ED A0 80`) must be immediately followed by a low surrogate sequence (e.g. `ED B0 80`). Anything else between them is an error.
- 4-byte UTF-8 sequences (F0…) are rejected because CESU-8 never uses them; supplementary characters always come through as paired surrogates.
- `bytearray` is accepted as well as `bytes`.

## Exports

- `decode(data)` — decode `bytes` or `bytearray` to `str`.
- `CESU8DecodeError` — subclass of `ValueError`, raised on any malformation.
