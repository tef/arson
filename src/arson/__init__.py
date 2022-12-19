#!/usr/bin/env python3
"""a restructured object notation, or arson

(in effect, json with tagged objects)

- allows bom, trailing commas, any object as root, and comments
- bytestrings, datetimes, sugar for numbers too

"""

import re
import io
import base64
import sys

if sys.version_info.minor > 6 or sys.version_info.minor == 6 and sys.implementation.name == 'cpython':
    OrderedDict = dict
    from collections import namedtuple
else:
    from collections import namedtuple, OrderedDict

from datetime import datetime, timedelta, timezone

CONTENT_TYPE="application/arson"
__version__="0.0.5"

# ARSON tags

reserved_tags = set("""
        bool int float complex
        string bytestring base64
        duration datetime
        set list dict object
        i8 i16 i32 i64 i128
        u8 u16 u32 u64 u128
        f8 f16 f32 f64 f128
        unknown
""".split())

allowed_tags_for_object = set("""
        object record dict
""".split())

allowed_tags_for_list = set("""
        object list set
        complex string
        i8 i16 i32 i64 i128
        u8 u16 u32 u64 u128
""".split())

allowed_tags_for_string = set("""
        object string 
        float datetime
        bytestring base64
""".split())

allowed_tags_for_number = set("""
        object int float duration
        i8 i16 i32 i64 i128
        u8 u16 u32 u64 u128
""".split())

allowed_tags_for_bool = set("""
        object bool
""".split())

number_widths = {
    "u8": (0, 2**8-1),
    "u16": (0, 2**16-1),
    "u32": (0, 2**32-1),
    "u64": (0, 2**64-1),
    "u128": (0, 2**128-1),

    "i8": (-2**7, 2**7-1),
    "i16": (-2**15, 2**15-1),
    "i32": (-2**31, 2**31-1),
    "i64": (-2**63, 2**63-1),
    "i128": (-2**127, 2**127-1),

    "f8": None,   # 'minifloat'
    "f16": None,  # half
    "f32": None,  # single
    "f64": None,  # double
    "f128": None, # quadruple 
}

# Regular Expressions for Tokenizing Input

whitespace = re.compile(r"(?:\ |\t|\uFEFF|\r|\n|#[^\r\n]*(?:\r?\n|$))+")

int_b2 = re.compile(r"0b[01][01_]*")
int_b8 = re.compile(r"0o[0-7][0-7_]*")
int_b10 = re.compile(r"\d[\d_]*")
int_b16 = re.compile(r"0x[0-9a-fA-F][0-9a-fA-F_]*")

flt_b10 = re.compile(r"\.[\d_]+")
exp_b10 = re.compile(r"[eE](?:\+|-)?[\d+_]")

string_dq = re.compile(
    r'"(?:[^"\\\n\x00-\x1F\x7F-\x9F\uD800-\uDFFF]|\\(?:[\'"\\/bfnrt]|\r?\n|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*"')
string_sq = re.compile(
    r"'(?:[^'\\\n\x00-\x1F\x7F-\x9F\uD800-\uDFFF]|\\(?:[\"'\\/bfnrt]|\r?\n|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*'")

tag_name = re.compile(r"@(?!\d)\w+[ ]+")
identifier = re.compile(r"(?!\d)[\w\.]+")

c99_flt = re.compile(
    r"NaN|nan|[-+]?Inf|[-+]?inf|[-+]?0x[0-9a-fA-F][0-9a-fA-F]*\.[0-9a-fA-F]+[pP](?:\+|-)?[\d]+")

str_escapes = {
    'b': '\b',
    'n': '\n',
    'f': '\f',
    'r': '\r',
    't': '\t',
    '/': '/',
    '"': '"',
    "'": "'",
    '\\': '\\',
}

byte_escapes = {
    'b': b'\b',
    'n': b'\n',
    'f': b'\f',
    'r': b'\r',
    't': b'\t',
    '/': b'/',
    '"': b'"',
    "'": b"'",
    '\\': b'\\',
}

escaped = {
    '\b': '\\b',
    '\n': '\\n',
    '\f': '\\f',
    '\r': '\\r',
    '\t': '\\t',
    '"': '\\"',
    "'": "\\'",
    '\\': '\\\\',
}

builtin_names = {'null': None, 'true': True, 'false': False}
builtin_values = {None: 'null', True: 'true', False: 'false'}

# names -> Classes (take name, value as args)
def parse_datetime(v):
    if v[-1] == 'Z':
        if '.' in v:
            return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        else:
            return datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    else:
        raise NotImplementedError()


def format_datetime(obj):
    obj = obj.astimezone(timezone.utc)
    return obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

class ParserErr(Exception):
    def __init__(self, buf, pos, reason=None):
        self.buf = buf
        self.pos = pos
        if reason is None:
            nl = buf.rfind(' ', pos - 10, pos)
            if nl < 0:
                nl = pos - 5
            reason = "Unknown Character {} (context: {})".format(
                repr(buf[pos]), repr(buf[pos - 10:pos + 5]))
        Exception.__init__(self, "{} (at pos={})".format(reason, pos))


class Codec:
    content_type = CONTENT_TYPE

    def __init__(self, object_to_tagged, tagged_to_object):
        self.object_to_tagged = object_to_tagged
        self.tagged_to_object = tagged_to_object

    def parse(self, buf, transform=None):
        obj, pos = self.parse_arson(buf, 0, transform)

        m = whitespace.match(buf, pos)
        if m:
            pos = m.end()
            m = whitespace.match(buf, pos)

        if pos != len(buf):
            raise ParserErr(buf, pos, "Trailing content: {}".format(
                repr(buf[pos:pos + 10])))

        return obj


    def dump(self, obj, transform=None):
        buf = io.StringIO('')
        self.dump_arson(obj, buf, transform)
        return buf.getvalue()

    def parse_arson(self, buf, pos, transform=None):
        m = whitespace.match(buf, pos)
        if m:
            pos = m.end()

        peek = buf[pos]
        name = None
        if peek == '@':
            m = tag_name.match(buf, pos)
            if m:
                pos = m.end()
                name = buf[m.start() + 1:pos].rstrip()
            else:
                raise ParserErr(buf, pos)

        peek = buf[pos]

        if peek == '@':
            raise ParserErr(buf, pos, "Cannot nest tags")

        elif peek == '{':
            if name in reserved_tags:
                if name not in allowed_tags_for_object:
                    raise ParserErr(
                        buf, pos, "{} can't be used on objects".format(name))

            if name == 'dict':
                out = dict()
            else:
                out = OrderedDict()

            pos += 1
            m = whitespace.match(buf, pos)
            if m:
                pos = m.end()

            while buf[pos] != '}':
                key, pos = self.parse_arson(buf, pos, transform)

                if key in out:
                    raise SemanticErr('duplicate key: {}, {}'.format(key, out))

                m = whitespace.match(buf, pos)
                if m:
                    pos = m.end()

                peek = buf[pos]
                if peek == ':':
                    pos += 1
                    m = whitespace.match(buf, pos)
                    if m:
                        pos = m.end()
                else:
                    raise ParserErr(
                        buf, pos, "Expected key:value pair but found {}".format(repr(peek)))
                    
                item, pos = self.parse_arson(buf, pos, transform)

                out[key] = item

                m = whitespace.match(buf, pos)
                if m:
                    pos = m.end()

                peek = buf[pos]
                
                if peek == ',':
                    pos += 1
                    m = whitespace.match(buf, pos)
                    if m:
                        pos = m.end()
                elif peek != '}':
                    raise ParserErr(
                        buf, pos, "Expecting a ',', or a '}}' but found {}".format('{}',repr(peek)))
            if name in (None, 'object', 'record', 'dict'):
                pass
            elif name in reserved_tags:
                raise ParserErr(
                    buf, pos, "{} has no meaning for {}".format(repr(name), item))
            else:
                out = self.tagged_to_object(name,  out)

            if transform is not None:
                out = transform(out)
            return out, pos + 1

        elif peek == '[':
            if name in reserved_tags:
                if name not in allowed_tags_for_list:
                    raise ParserErr(
                        buf, pos, "{} can't be used on lists".format(name))

            if name == 'set':
                out = set()
            else:
                out = []

            pos += 1

            m = whitespace.match(buf, pos)
            if m:
                pos = m.end()

            while buf[pos] != ']':
                item, pos = self.parse_arson(buf, pos, transform)
                if name == 'set':
                    if item in out:
                        raise SemanticErr('duplicate item in set: {}'.format(item))
                    else:
                        out.add(item)
                else:
                    out.append(item)

                m = whitespace.match(buf, pos)
                if m:
                    pos = m.end()

                peek = buf[pos]
                if peek == ',':
                    pos += 1
                    m = whitespace.match(buf, pos)
                    if m:
                        pos = m.end()
                elif peek != ']':
                    raise ParserErr(
                        buf, pos, "Expecting a ',', or a ']' but found {}".format(repr(peek)))

            pos += 1

            if name in (None, 'object', 'list', 'set'):
                pass
            elif name == 'complex':
                out = complex(*out)
            elif name == 'string':
                out = "".join(out)
            elif name in ('u8', 'u16', 'u32', 'u64', 'u128',):
                n_min, n_max = number_widths[name]
                if not all(isinstance(i, int) and i >= n_min and i <= n_max for i in out):
                    raise ParserErr(buf, pos, "Expecing an array of positive ints")
            elif name in ('i8', 'i16', 'i32', 'i64', 'i128',):
                n_min, n_max = number_widths[name]
                if not all(isinstance(i, int) and i >= n_min and i <= n_max for i in out):
                    raise ParserErr(buf, pos, "Expecing an array of ints")
            elif name in ('f8', 'f16', 'f32', 'f64', 'f128',):
                raise ParserErr(buf, pos, "Unsupported tag {}:".format(repr(name)))
            elif name in reserved_tags:
                raise ParserErr(
                    buf, pos, "{} has no meaning for {}".format(repr(name), item))
            else:
                out = self.tagged_to_object(name,  out)

            if transform is not None:
                out = transform(out)
            return out, pos

        elif peek == "'" or peek == '"':
            if name in reserved_tags:
                if name not in allowed_tags_for_string:
                    raise ParserErr(
                        buf, pos, "{} can't be used on strings".format(name))

            if name == 'bytestring':
                s = bytearray()
                ascii = True
            else:
                s = io.StringIO()
                ascii = False

            # validate string
            if peek == "'":
                m = string_sq.match(buf, pos)
                if m:
                    end = m.end()
                else:
                    raise ParserErr(buf, pos, "Invalid single quoted string")
            else:
                m = string_dq.match(buf, pos)
                if m:
                    end = m.end()
                else:
                    raise ParserErr(buf, pos, "Invalid double quoted string")

            lo = pos + 1  # skip quotes
            while lo < end - 1:
                hi = buf.find("\\", lo, end)
                if hi == -1:
                    if ascii:
                        s.extend(buf[lo:end - 1].encode('ascii'))
                    else:
                        s.write(buf[lo:end - 1])  # skip quote
                    break

                if ascii:
                    s.extend(buf[lo:hi].encode('ascii'))
                else:
                    s.write(buf[lo:hi])

                esc = buf[hi + 1]
                if esc in str_escapes:
                    if ascii:
                        s.extend(byte_escapes[esc])
                    else:
                        s.write(str_escapes[esc])
                    lo = hi + 2
                elif esc == 'x':
                    n = int(buf[hi + 2:hi + 4], 16)
                    if ascii:
                        s.append(n)
                    else:
                        s.write(chr(n))
                    lo = hi + 4
                elif esc == 'u':
                    n = int(buf[hi + 2:hi + 6], 16)
                    if ascii:
                        if n > 0xFF:
                            raise ParserErr(
                                buf, hi, 'bytestring cannot have escape > 255')
                        s.append(n)
                    else:
                        if 0xD800 <= n <= 0xDFFF:
                            raise ParserErr(
                                buf, hi, 'string cannot have surrogate pairs')
                        s.write(chr(n))
                    lo = hi + 6
                elif esc == 'U':
                    n = int(buf[hi + 2:hi + 10], 16)
                    if ascii:
                        if n > 0xFF:
                            raise ParserErr(
                                buf, hi, 'bytestring cannot have escape > 255')
                        s.append(n)
                    else:
                        if 0xD800 <= n <= 0xDFFF:
                            raise ParserErr(
                                buf, hi, 'string cannot have surrogate pairs')
                        s.write(chr(n))
                    lo = hi + 10
                elif esc == '\n':
                    lo = hi + 2
                elif (buf[hi + 1:hi + 3] == '\r\n'):
                    lo = hi + 3
                else:
                    raise ParserErr(
                        buf, hi, "Unkown escape character {}".format(repr(esc)))

            if name == 'bytestring':
                out = s
            else:
                out = s.getvalue()

                if name in (None, 'string', 'object'):
                    pass
                elif name == 'base64':
                    try:
                        out = base64.standard_b64decode(out)
                    except Exception as e:
                        raise ParserErr(buf, pos, "Invalid base64") from e
                elif name == 'datetime':
                    try:
                        out = parse_datetime(out)
                    except Exception as e:
                        raise ParserErr(
                            buf, pos, "Invalid datetime: {}".format(repr(out))) from e
                elif name == 'float':
                    m = c99_flt.match(out)
                    if m:
                        out = float.fromhex(out)
                    else:
                        raise ParserErr(
                            buf, pos, "invalid C99 float literal: {}".format(out))
                elif name in reserved_tags:
                    raise ParserErr(
                        buf, pos, "{} has no meaning for {}".format(repr(name), item))
                else:
                    out = self.tagged_to_object(name,  out)

            if transform is not None:
                out = transform(out)
            return out, end

        elif peek in "-+0123456789":
            if name in reserved_tags:
                if name not in allowed_tags_for_number:
                    raise ParserErr(
                        buf, pos, "{} can't be used on numbers".format(name))

            flt_end = None
            exp_end = None

            sign = +1

            if buf[pos] in "+-":
                if buf[pos] == "-":
                    sign = -1
                pos += 1
            peek = buf[pos:pos + 2]

            if peek in ('0x', '0o', '0b'):
                if peek == '0x':
                    base = 16
                    m = int_b16.match(buf, pos)
                    if m:
                        end = m.end()
                    else:
                        raise ParserErr(
                            buf, pos, "Invalid hexadecimal number (0x...)")
                elif peek == '0o':
                    base = 8
                    m = int_b8.match(buf, pos)
                    if m:
                        end = m.end()
                    else:
                        raise ParserErr(buf, pos, "Invalid octal number (0o...)")
                elif peek == '0b':
                    base = 2
                    m = int_b2.match(buf, pos)
                    if m:
                        end = m.end()
                    else:
                        raise ParserErr(
                            buf, pos, "Invalid hexadecimal number (0x...)")

                out = sign * int(buf[pos + 2:end].replace('_', ''), base)
            else:
                m = int_b10.match(buf, pos)
                if m:
                    int_end = m.end()
                    end = int_end
                else:
                    raise ParserErr(buf, pos, "Invalid number")

                t = flt_b10.match(buf, end)
                if t:
                    flt_end = t.end()
                    end = flt_end

                e = exp_b10.match(buf, end)
                if e:
                    exp_end = e.end()
                    end = exp_end

                if flt_end or exp_end:
                    out = sign * float(buf[pos:end].replace('_', ''))
                else:
                    out = sign * int(buf[pos:end].replace('_', ''), 10)

            if name is None or name == 'object':
                pass
            elif name == 'duration':
                out = timedelta(seconds=out)
            elif name == 'int':
                if flt_end or exp_end:
                    raise ParserErr(
                        buf, pos, "Can't tag floating point with @int")
            elif name == 'float':
                if not isinstance(out, float):
                    out = float(out)
            elif name in ('u8', 'u16', 'u32', 'u64', 'u128',):
                if not isinstance(out, int) or out <= 0:
                    raise ParserErr(buf, pos, "Expecing a positive int")
            elif name in ('i8', 'i16', 'i32', 'i64', 'i128',):
                if not isinstance(out, int):
                    raise ParserErr(buf, pos, "Expecing an int")
            elif name in ('f8', 'f16', 'f32', 'f64', 'f128',):
                raise ParserErr(buf, pos, "Unsupported tag {}:".format(repr(name)))
            elif name in reserved_tags:
                raise ParserErr(
                    buf, pos, "{} has no meaning for {}".format(repr(name), item))
            else:
                out = self.tagged_to_object(name, out)

            if transform is not None:
                out = transform(out)
            return out, end

        else:
            m = identifier.match(buf, pos)
            if m:
                end = m.end()
                item = buf[pos:end]
            else:
                raise ParserErr(buf, pos)

            if item not in builtin_names:
                raise ParserErr(
                    buf, pos, "{} is not a recognised built-in".format(repr(item)))

            out = builtin_names[item]

            if name is None or name == 'object':
                pass
            elif name == 'bool':
                if item not in allowed_tags_for_bool:
                    raise ParserErr(buf, pos, '@bool can only true or false')
            elif name in reserved_tags:
                raise ParserErr(
                    buf, pos, "{} has no meaning for {}".format(repr(name), item))
            else:
                out = self.tagged_to_object(name,  out)

            if transform is not None:
                out = transform(out)
            return out, end

        raise ParserErr(buf, pos)



    def dump_arson(self, obj, buf, transform=None):
        if transform:
            obj = transform(obj)
        if obj is True or obj is False or obj is None:
            buf.write(builtin_values[obj])
        elif isinstance(obj, str):
            buf.write('"')
            for c in obj:
                if c in escaped:
                    buf.write(escaped[c])
                elif ord(c) < 0x20:
                    buf.write('\\x{:02X}'.format(ord(c)))
                else:
                    buf.write(c)
            buf.write('"')
        elif isinstance(obj, int):
            buf.write(str(obj))
        elif isinstance(obj, float):
            hex = obj.hex()
            if hex.startswith(('0', '-')):
                buf.write(str(obj))
            else:
                buf.write('@float "{}"'.format(hex))
        elif isinstance(obj, complex):
            buf.write("@complex [{}, {}]".format(obj.real, obj.imag))
        elif isinstance(obj, (bytes, bytearray)):
            buf.write('@base64 "')
            # assume no escaping needed
            buf.write(base64.standard_b64encode(obj).decode('ascii'))
            buf.write('"')
        elif isinstance(obj, (list, tuple)):
            buf.write('[')
            first = True
            for x in obj:
                if first:
                    first = False
                else:
                    buf.write(", ")
                self.dump_arson(x, buf, transform)
            buf.write(']')
        elif isinstance(obj, set):
            buf.write('@set [')
            first = True
            for x in obj:
                if first:
                    first = False
                else:
                    buf.write(", ")
                self.dump_arson(x, buf, transform)
            buf.write(']')
        elif isinstance(obj, OrderedDict): # must be before dict
            buf.write('{')
            first = True
            for k, v in obj.items():
                if first:
                    first = False
                else:
                    buf.write(", ")
                self.dump_arson(k, buf, transform)
                buf.write(": ")
                self.dump_arson(v, buf, transform)
            buf.write('}')
        elif isinstance(obj, dict): # if dict is pre 3.7, then no order preserving
            buf.write('@dict {')
            first = True
            for k in sorted(obj.keys()):
                if first:
                    first = False
                else:
                    buf.write(", ")
                self.dump_arson(k, buf, transform)
                buf.write(": ")
                self.dump_arson(obj[k], buf, transform)
            buf.write('}')
        elif isinstance(obj, datetime):
            buf.write('@datetime "{}"'.format(format_datetime(obj)))
        elif isinstance(obj, timedelta):
            buf.write('@duration {}'.format(obj.total_seconds()))
        else:
            nv = self.object_to_tagged(obj)
            name, value = nv
            if not isinstance(value, OrderedDict) and isinstance(value, dict):
                value = OrderedDict(value)
            buf.write('@{} '.format(name))
            self.dump_arson(value, buf, transform)  # XXX: prevent @foo @foo

codec = Codec(None, None)

parse = codec.parse
dump = codec.dump


def run_tests(parse, dump):
    def test_parse(buf, obj):
        out = parse(buf)

        if (obj != obj and out == out) or (obj == obj and obj != out):
            raise AssertionError('{!r} != {!r}'.format(obj, out))


    def test_dump(obj, buf):
        out = dump(obj)
        if buf != out:
            raise AssertionError('{} != {}'.format(buf, out))


    def test_parse_err(buf, exc):
        try:
            obj = parse(buf)
        except Exception as e:
            if isinstance(e, exc):
                return
            else:
                raise AssertionError(
                    '{} did not cause {}, but {}'.format(buf, exc, e)) from e
        else:
            raise AssertionError(
                '{} did not cause {}, parsed:{}'.format(buf, exc, obj))


    def test_dump_err(obj, exc):
        try:
            buf = dump(obj)
        except Exception as e:
            if isinstance(e, exc):
                return
            else:
                raise AssertionError(
                    '{} did not cause {}, but '.format(obj, exc, e))
        else:
            raise AssertionError(
                '{} did not cause {}, dumping: {}'.format(obj, exc, buf))


    test_parse("0", 0)
    test_parse("0x0_1_2_3", 0x123)
    test_parse("0o0_1_2_3", 0o123)
    test_parse("0b0_1_0_1", 5)
    test_parse("0 #comment", 0)
    test_parse("""
"a\\
b"        
    """, "ab")
    test_parse("0.0", 0.0)
    test_parse("-0.0", -0.0)
    test_parse("'foo'", "foo")
    test_parse(r"'fo\no'", "fo\no")
    test_parse("'\\\\'", "\\")
    test_parse(r"'\b\f\r\n\t\"\'\/'", "\b\f\r\n\t\"\'/")
    test_parse("''", "")
    test_parse(r'"\x20"', " ")
    test_parse(r'"\uF0F0"', "\uF0F0")
    test_parse(r'"\U0001F0F0"', "\U0001F0F0")
    test_parse("'\\\\'", "\\")
    test_parse("[1]", [1])
    test_parse("[1,]", [1])
    test_parse("[]", [])
    test_parse("[1 , 2 , 3 , 4 , 4 ]", [1, 2, 3, 4, 4])
    test_parse("{'a':1,'b':2}", dict(a=1, b=2))
    test_parse("@set [ 1 , 2 , 3 , 4 ]", set([1, 2, 3, 4]))
    test_parse("{ 'a':1 , 'b':2 }", dict(a=1, b=2))
    test_parse("@complex [1,2]", 1 + 2j)
    test_parse("@bytestring 'foo'", b"foo")
    test_parse("@base64 '{}'".format(
        base64.standard_b64encode(b'foo').decode('ascii')), b"foo")
    test_parse("@float 'NaN'", float('NaN'))
    test_parse("@float '-inf'", float('-Inf'))
    obj = datetime.now().astimezone(timezone.utc)
    test_parse('@datetime "{}"'.format(
        obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")), obj)
    obj = timedelta(seconds=666)
    test_parse('@duration {}'.format(obj.total_seconds()), obj)
    test_parse("@bytestring 'fo\x20o'", b"fo o")
    test_parse("@float '{}'".format((3000000.0).hex()), 3000000.0)
    test_parse(hex(123), 123)
    test_parse('@object "foo"', "foo")
    test_parse('@object 12', 12)

    test_dump(1, "1")

    test_parse_err('"foo', ParserErr)
    test_parse_err('"\uD800\uDD01"', ParserErr)
    test_parse_err(r'"\uD800\uDD01"', ParserErr)

    tests = [
        0, -1, +1,
        -0.0, +0.0, 1.9,
        True, False, None,
        "str", b"bytes",
        [1, 2, 3], {"c": 3, "a": 1, "b": 2, }, set(
            [1, 2, 3]), OrderedDict(a=1, b=2),
        1 + 2j, float('NaN'),
        datetime.now().astimezone(timezone.utc),
        timedelta(seconds=666),
    ]

    for obj in tests:
        buf0 = dump(obj)
        obj1 = parse(buf0)
        buf1 = dump(obj1)

        out = parse(buf1)

        if obj != obj1:
            if buf0 != buf1 or obj1 == obj1 or out == out:
                raise AssertionError('{} != {}'.format(obj, out))
        else:
            if buf0 != buf1:
                raise AssertionError(
                    'mismatched output {} != {}'.format(buf0, buf1))
            if obj != obj1:
                raise AssertionError(
                    'failed first trip {} != {}'.format(obj, obj1))
            if obj != out:
                raise AssertionError(
                    'failed second trip {} != {}'.format(obj, out))
    return True


if __name__ == '__main__':
    if run_tests(parse, dump):
        print('tests passed')

