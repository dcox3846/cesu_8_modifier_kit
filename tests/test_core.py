import unittest

from cesu_8_modifier_kit import CESU8DecodeError, decode


class TestASCII(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(decode(b""), "")

    def test_ascii(self):
        self.assertEqual(decode(b"Hello"), "Hello")

    def test_ascii_includes_nul(self):
        self.assertEqual(decode(b"\x00abc"), "\x00abc")


class TestBMP(unittest.TestCase):
    def test_two_byte(self):
        # U+00E9 (é) → C3 A9
        self.assertEqual(decode(b"\xc3\xa9"), "\u00e9")

    def test_three_byte_bmp(self):
        # U+20AC (€) → E2 82 AC
        self.assertEqual(decode(b"\xe2\x82\xac"), "\u20ac")

    def test_mixed_ascii_and_bmp(self):
        self.assertEqual(decode(b"price: \xe2\x82\xac5"), "price: \u20ac5")


class TestSupplementary(unittest.TestCase):
    def test_supplementary_emoji(self):
        # U+1F600 (😀)
        # UTF-16 surrogate pair: D83D DE00
        # High surrogate D83D → ED A0 BD
        # Low  surrogate DE00 → ED B8 80
        self.assertEqual(decode(b"\xed\xa0\xbd\xed\xb8\x80"), "\U0001F600")

    def test_supplementary_cjk(self):
        # U+20000 (CJK extension B)
        # UTF-16 surrogate pair: D840 DC00
        # High surrogate D840 → ED A1 80
        # Low  surrogate DC00 → ED B0 80
        self.assertEqual(decode(b"\xed\xa1\x80\xed\xb0\x80"), "\U00020000")

    def test_supplementary_between_bmp(self):
        # BMP char, emoji, BMP char
        data = b"\xe2\x82\xac" + b"\xed\xa0\xbd\xed\xb8\x80" + b"\xc3\xa9"
        self.assertEqual(decode(data), "\u20ac\U0001F600\u00e9")


class TestErrors(unittest.TestCase):
    def test_lone_high_surrogate(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xed\xa0\x80")

    def test_high_surrogate_then_bmp(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xed\xa0\x80\xe2\x82\xac")

    def test_lone_low_surrogate(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xed\xb0\x80")

    def test_low_before_high(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xed\xb0\x80\xed\xa0\x80")

    def test_truncated_two_byte(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xc3")

    def test_truncated_three_byte(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xe2\x82")

    def test_truncated_high_surrogate(self):
        # High surrogate, then only one byte of the low surrogate sequence.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xed\xa0\x80\xed\xb0")

    def test_overlong_two_byte(self):
        # Overlong encoding of U+007F as a 2-byte sequence.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xc1\xbf")

    def test_overlong_three_byte(self):
        # Overlong encoding of U+07FF as a 3-byte sequence.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xe0\x9f\xbf")

    def test_four_byte_rejected(self):
        # CESU-8 does not use 4-byte sequences.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xf0\x90\x80\x80")

    def test_bad_continuation_byte(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xc3\x00")

    def test_continuation_as_lead(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\x80")

    def test_type_error_on_str(self):
        with self.assertRaises(TypeError):
            decode("not bytes")


class TestByteArray(unittest.TestCase):
    def test_bytearray_accepted(self):
        self.assertEqual(decode(bytearray(b"\xed\xa0\xbd\xed\xb8\x80")), "\U0001F600")


if __name__ == "__main__":
    unittest.main()
