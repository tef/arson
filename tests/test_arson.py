import unittest
import base64
from datetime import datetime, timedelta, timezone
import arson

class ArsonTest(unittest.TestCase):
    def test_arson(self):
        # Run legacy tests
        self.assertTrue(arson.run_tests(arson.parse, arson.dump))

    def assertParse(self, str, value):
        if value == value:
            self.assertEqual(arson.parse(str), value)
        else: # NaN
            self.assertNotEqual(arson.parse(str), value)

    def assertDump(self, value, str):
        self.assertEqual(arson.dump(value), str)

    def assertRoundTrip(self, value0):
        buf0 = arson.dump(value0)
        value1 = arson.parse(buf0)
        self.assertEqual(value0, value1)
        buf1 = arson.dump(value1)
        self.assertEqual(buf0, buf1)
        value2 = arson.parse(buf1)
        self.assertEqual(value0, value2)

    def test_arson_parse(self):
        self.assertParse("0", 0)
        self.assertParse("0x0_1_2_3", 0x123)
        self.assertParse("0o0_1_2_3", 0o123)
        self.assertParse("0b0_1_0_1", 5)
        self.assertParse("0 #comment", 0)
        self.assertParse("""
"a\\
b"
        """, "ab")
        self.assertParse("0.0", 0.0)
        self.assertParse("-0.0", -0.0)
        self.assertParse("'foo'", "foo")
        self.assertParse(r"'fo\no'", "fo\no")
        self.assertParse("'\\\\'", "\\")
        self.assertParse(r"'\b\f\r\n\t\"\'\/'", "\b\f\r\n\t\"\'/")
        self.assertParse("''", "")
        self.assertParse(r'"\x20"', " ")
        self.assertParse(r'"\uF0F0"', "\uF0F0")
        self.assertParse(r'"\U0001F0F0"', "\U0001F0F0")
        self.assertParse("'\\\\'", "\\")
        self.assertParse("[1]", [1])
        self.assertParse("[1,]", [1])
        self.assertParse("[]", [])
        self.assertParse("[1 , 2 , 3 , 4 , 4 ]", [1, 2, 3, 4, 4])
        self.assertParse("{'a':1,'b':2}", dict(a=1, b=2))
        self.assertParse("@set [ 1 , 2 , 3 , 4 ]", set([1, 2, 3, 4]))
        self.assertParse("{ 'a':1 , 'b':2 }", dict(a=1, b=2))
        self.assertParse("@complex [1,2]", 1 + 2j)
        self.assertParse("@bytestring 'foo'", b"foo")
        self.assertParse("@base64 '{}'".format(
            base64.standard_b64encode(b'foo').decode('ascii')), b"foo")
        self.assertParse("@float 'NaN'", float('NaN'))
        self.assertParse("@float '-inf'", float('-Inf'))
        obj = datetime.now().astimezone(timezone.utc)
        self.assertParse('@datetime "{}"'.format(
            obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")), obj)
        obj = timedelta(seconds=666)
        self.assertParse('@duration {}'.format(obj.total_seconds()), obj)
        self.assertParse("@bytestring 'fo\x20o'", b"fo o")
        self.assertParse("@float '{}'".format((3000000.0).hex()), 3000000.0)
        self.assertParse(hex(123), 123)
        self.assertParse('@object "foo"', "foo")
        self.assertParse('@object 12', 12)

    def test_arson_dump(self):
        self.assertDump(1, "1")

    def test_arson_roundtrip(self):
        tests = [
            0, -1, +1,
            -0.0, +0.0, 1.9,
            True, False, None,
            "str", b"bytes",
            [1, 2, 3], {"c": 3, "a": 1, "b": 2, },
            set([1, 2, 3]),
            1 + 2j,
            datetime.now().astimezone(timezone.utc),
            timedelta(seconds=666),
        ]
        for t in tests:
            self.assertRoundTrip(t)


if __name__ == '__main__':
    unittest.main()
