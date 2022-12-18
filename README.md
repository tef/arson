# ARSON: A Restructured Object Notation

ARSON is JSON, with a little bit of sugar: Comments, Commas, and Tags.

For example:

```
{
    "numbers": +0123.0,       # Can have leading zeros
    "octal": 0o10,            # Oh, and comments too
    "hex": 0xFF,              #
    "binary": 0b1000_0001,     # Number literals can have _'s 

    "lists": [1,2,3],         # Lists can have trailing commas

    "strings": "At least \x61 \u0061 and \U00000061 work now",
    "or": 'a string',          # both "" and '' work.

    "records": {
        "a": 1,               # Must have unique keys
        "b": 2,               # and the order must be kept
    },
}
```

Along with some sugar atop JSON, ARSON supports tagging literals to represent types outside of JSON:

- `@datetime "2017-11-22T23:32:07.100497Z"`, a tagged RFC 3339 datestamp
- `@duration 60` (a duration in seconds, float or int)
- `@base64 "...=="`, a base64 encoded bytestring
- `@set`, `@dict`, `@complex`, `@bytestring`

# Quickstart

Use `pip install arson` to get the latest copy of the python library. The `arson` library
has two methods, `parse` and `dump`.

```
import arson

print(arson.parse(arson.dump([1,2,3])))
```

If you want to use your own tagged object types, you can create a custom `Codec`:

```
import arson

class Example:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"Example {self.value}"

def object_to_tagged(obj):
    if isinstance(obj, Example):
        return "Example", {"value": obj.value}
    else:
        raise NotImplementedError()

def tagged_to_object(name, value):
    if name == "Example":
        return Example(value['value'])
    else:
        raise NotImplementedError()
        
codec = arson.Codec(object_to_tagged, tagged_to_object)

print(codec.parse(codec.dump(Example(1))))
```

## ARSON in a Nutshell

 - File MUST be utf-8, not cesu-8/utf-16/utf-32, without surrogate pairs.
 - Use `#.... <end of line>` for comments
 - Byte Order Mark is treated as whitespace (along with `\x09`, `\x0a`, `\x0d`, `\x20`)
 - ARSON Document is any ARSON Object, (i.e `1` is a valid ARSON file).
 - Lists are `[]`, `[obj]`, `[obj,]`, `[obj, obj]` ... (trailing comma optional)
 - Records are `{ "key": value}`, keys must be unique, order must be preserved. 
 - Built-ins: `true`, `false`, `null`
 - `"unicode strings"` with escapes `\" \\ \/ \b \f \n \r \t \uFFFF \UFFFFFFFF`, no control codes unecaped, and `''` can be used instead of `""`.
 - int/float numbers (unary plus or minus, allowleading zeros, hex, octal, and binary integer liters)
 - Tagged literals: `@name [1,2,3]` for any other type of value.

 Errors are fatal. A record with duplicate keys, or a string too long, or a number to big to represent MUST cause the parse to fail outright.

# ARSON Object Model and Syntax

ARSON has the following types of literals:

 - `null`, `true`, `false`
 - Numbers (Floating Point, and integer literals: decimal, binary, octal, hex)
 - Strings (using single or double quotes)
 - Lists
 - Records (a JSON object with ordering and without duplicate keys)
 - Tagged Literal

ARSON has a number of built-in tags:
 - `@object`, `@bool`, `@int`, `@float`, `@string`, `@list`, `@record`

As well as optional tags for other types:

 - `@bytestring`, or `@base64` for bytestrings
 - `@float "0x0p0"`, for C99 Hex Floating Point Literals
 - `@dict` for unordered key-value maps
 - `@set` for sets, `@complex` for complex numbers
 - `@datetime`, `@duration` for time as point or measurement.

The ARSON spec reserves a few more optional tags for fixed-width numerics, which are currently not implemented in this library.

 - Signed integers: `@i8`, `@i16`, `@i32`, `@i64`, `@i128` 
 - Unsigned integers: `@u8`, `@u16`, `@u32`, `@u64`, `@u128` 
 - Floating point: `@f8`, `@f16`, `@f32`, `@f64`, `@f128` 

