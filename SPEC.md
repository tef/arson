# ARSON: A Restructured Object Notation

ARSON is JSON, with a little bit of sugar: Comments, Commas, and Tags.

This is version 1 of the specification, dated 2022-12-10.

For example:

```
{
    "numbers": +0123.0,       # Can have leading zeros
    "octal": 0o10,            # Oh, and comments too
    "hex": 0xFF,              # Numbers don't have to be decimal
    "binary": 0b1000_0001,    # and numbers can have _'s too

    "lists": [1,2,3],         # Lists can have trailing commas

    "strings": "At least \x61 \u0061 and \U00000061 work now",
    "or": 'a string',         # Strings use either "" or ''.

    "records": {
        "a": 1,               # Records Must have unique keys
        "b": 2,               # and the order must be preserved, too
    },
}
```

Along with some sugar atop JSON, ARSON supports tagging literals to represent types outside of JSON:

- `@datetime "2017-11-22T23:32:07.100497Z"`, a tagged RFC 3339 datestamp
- `@duration 60` (a duration in seconds, float or int)
- `@base64 "...=="`, a base64 encoded bytestring
- `@set`, `@dict`, `@complex`, `@bytestring`


## JSON in a nutshell:

 - A unicode text file (in utf-8), without a Byte Order Mark
 - Whitespace is `\t`, `\r`, `\n`, `\x20`
 - JSON document is either list, or object
 - Lists are `[]`, `[obj]`, `[ obj, obj ]`, ...
 - Objects: `{ "key": value}`, only string keys, order not preserved, duplicate handling undefined.
 - Built-ins: `true`, `false`, `null`
 - `"ucs-2 unicode strings"` with escapes `\" \\ \/ \b \f \n \r \t \uFFFF`, and no control codes unecaped.
 - floating point numbers (unary minus, no leading zeros, except for `0.xxx`)
 - No Comments
 - No Trailing commas in collections
 - Astral plane characters may need to be escaped using surrogate pairs
 - Integers may need to be represented as strings if longer than 53 bits

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

Along with optional tags for fixed-width numerics:

 - Signed integers: `@i8`, `@i16`, `@i32`, `@i64`, `@i128` 
 - Unsigned integers: `@u8`, `@u16`, `@u32`, `@u64`, `@u128` 
 - Floating point: `@f8`, `@f16`, `@f32`, `@f64`, `@f128` 

## ARSON strings: 

 - use ''s or ""s
 - json escapes, and `\xFF` (as `\u00FF`), `\UFFFFFFFF`  `\'` too
 - no surrogate pairs, no unprintables

## ARSON numbers:

 - allow unary minus, plus
 - allow leading zero
 - allow underscores (except leading digits)
 - binary ints: `0b1010`
 - octal ints `0o777`
 - hex ints: `0xFF` 
 - floating point: `1.123e-10` `-0.0` `+0.0` 
 - limits on size are implementation defined, parsers MAY reject numbers that are too big to represent.

Special floating point values `NaN`, `+Infinity` are represented using tagged literals, `@float "NaN"`, `@float "+Inf"`, `@float "-Inf"`

## ARSON lists:

 - allow trailing commas

## ARSON records (aka, JSON objects):

 - no duplicate keys: parser MUST reject
 - insertion order must be preserved, but not considered in equality
 - allow trailing commas
 - implementations MUST support string keys

 Two keys are the same if

 - both strings and same codepoints (unnormalized)
 - same numerical value i.e `1` and `1.0` and `1.0e0` are the same key, `+0.0`, `-0.0` are the same key,
 - lists of same size and items are same
 - records of same size and key-value pairs are same, ignoring order
 
Note: Semantics of `NaN` keys, or collections containing them are implementation defined.

## ARSON tagged objects:

 - `@foo.foo {"foo":1}` name is any unicode letter/digit, `_`or a `.`
 - `@int 1`, `@string "two"` are just `1` and `"two"`
 - do not nest,
 - whitespace between tag name and object is *mandatory*
 - every type has a reserved tag name
 - parsers MAY reject unknown, or return a wrapped object 

### ARSON C99 float strings (optional):

 - `@float "0x0p0"` C99 style, sprintf('%a') format
 - `@float "NaN"` or nan,Inf,inf,+Inf,-Inf,+inf,-inf
 -  no underscores allowed

`<sign>0x<hex mantissa>p<sign><decimal exponent>` or `...1x...` for subnormals.

### ARSON sets (optional):

 - `@set [1,2,3]`
 - always a tagged list
 - no duplicate items, same rules as records
 - ordering does not matter when comparing

### ARSON dicts (optional):

This is for compatibility with hash tables without insertion order preservation.

 - `@dict {"a":1}` 
 - keys must be emitted in lexical order, must round trip in same order.
 - keys must all be the same type: number or string 
 - no duplicate items, same rules as records
 - a `@dict` is equal to a record if it has same keys, ignoring order.

sort order is only defined for keys of the same type

### ARSON datetimes/periods (optional):

 - RFC 3339 format in UTC, (i.e 'Zulu time')
 - `@datetime "2017-11-22T23:32:07.100497Z"`
 - `@duration 60` (in seconds, float or int)
 - UTC MUST be supported, using `Z` suffix
 - implementations should support subset of RFC 3339

### ARSON bytestrings (optional):

 - `@bytestring "....\xff"` 
 - `@base64 "...=="`
 - returns a bytestring if possible
 - can't have `\u` `\U` escapes > 0xFF
 - all non printable ascii characters must be escaped: `\xFF`

### ARSON complex numbers: (optional)

 - `@complex [0,1]` (real, imaginary)

### ARSON fixed width numerics (optional)

Numeric literals can be tagged with a desired width.

 - `@u8 255`
 - `@i8 -127`
 - `@f32 0.0`

Additionally, fixed width floating points (i.e `@f8`) work like `@float`, and accept C99 hex-floats, along with `"NaN"` etc.

Implementations MUST error if the floats are too wide, but may choose to store a `f32` in a `f64`, for example.

### ARSON numeric arrays (optional)

An array of numeric literals can be tagged:

 - `@u8 [2,5,5]` is the same as `[@u8 2, @u8 5, @u8 5]`
 - `@i8 [-1,2,7]` is the same as `[@u8 -1, @u8 2, @u8 7]`
 - `@f32 [0.0, -1.0, 1.0]` is the same as `[@f32 0.0, @f32 -1.0, @f32 1.0]`

### Builtin ARSON Tags:

Pass throughs (i.e `@foo bar` is `bar`):

 - `@object` on any 
 - `@bool` on true, or false
 - `@int` on ints
 - `@float` on ints or floats
 - `@string` on strings
 - `@list` on lists
 - `@record` on records

Tags that transform the literal:

 - @float on strings (for C99 hex floats, including NaN, -Inf, +Inf)
 - @duration on numbers (seconds)
 - @datetime on strings (utc timestamp)
 - @base64 on strings (into a bytesting)
 - @bytestring on strings (into a bytestring)
 - @set on lists 
 - @complex on lists
 - @string on lists of strings (joins them into one string)
 - @dict on records
 - @u8, @f8, @i8 on lists

Reserved:

 - `@unknown`

Any other use of a builtin tag is an error and MUST be rejected.

# ARSON Test Vectors

## MUST parse
```
@object null
@bool true
false
0
@float 0.0
-0.0
"test-\x32-\u0032-\U00000032"
'test \" \''
[]
[1,]
{"a":"b",}
```

## MUST not parse

```
_1
0b0123
0o999
0xGHij
@set {}
@dict []
[,]
{"a"}
{"a":1, "a":2}
@object @object {}
"\uD800\uDD01"
```

