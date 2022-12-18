# ARSON: A Restructured Object Notation

ARSON is JSON, with a little bit of sugar: Comments, Commas, and Tags.

> This is version 1 of the specification, dated 2022-12-18. This specification
is still being drafted, but is pretty much feature complete. Please contact
us if you're implementing a library and find something unclear.

A full example of ARSON:

```
{
    "numbers": +0123.0,       # Can have leading zeros
    "octal": 0o10,            # Oh, and comments too
    "hex": 0xFF,              # Numbers don't have to be decimal
    "binary": 0b1000_0001,    # and numbers can have _'s too

    "lists": [1,2,3,],        # Lists can have trailing commas

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

Types outside of the basic arson types (int, float, string, object, list) are optional parts of RSON, but every parser MUST be able to parse a file containing tagged literals.

# ARSON vs JSON:

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

Non-printable characters (or Control Codes) are defined as C0 and C1 blocks in unicode. This includes the tab character.

# ARSON Object Model and Syntax

ARSON has the following types of literals:

 - `null`, `true`, `false`
 - Numbers (Floating Point, and integer literals: decimal, binary, octal, hex)
 - Strings (using single or double quotes)
 - Lists
 - Records (a JSON object with ordering and without duplicate keys)
 - Tagged Literals

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

# RSON objects

## ARSON singletons (mandatory)

- `true`, `false`, `null`
- names are case sensitive and lowercase
- true/false can be tagged `@bool true`
- true, false, null can be tagged `@object`

## ARSON strings (mandatory): 

 - use either ''s or ""s
 - escape codepoints with `\xFF` or `\u00FF`, or `\UFFFFFFFF`  
 - `\b \n \r \t \f \\ \/ \"` plus `\'` too
 - no surrogate pairs allowed in strings
 - no unprintables/control chars (no tabs, del, c0, or c1)
 - can be tagged `@string "test"` 
 - can be a tagged list `@string ["te", "st",]`

## ARSON numbers (mandatory):

 - allows unary minus, plus
 - allows leading zero
 - allows underscores between digits (except leading digits)
 - binary ints start with `0b`: `0b1010`
 - octal ints start with `0c`: `0o777`
 - hex ints start with `0x`: `0xFF` 
 - limits on size are implementation defined, parsers MAY reject numbers that are too big to represent.
 - can be sent as tagged numeric literal `@int 123` (not a tagged string)

## ARSON floating point numbers (mandatory):

 - floating point: `1.123e-10` `-0.0` `+0.0`  
 - allows unary minus, plus
 - allows leading zero
 - allows underscores between digits (except leading digits)
 - limits on size are implementation defined, parsers MAY reject numbers that are too big to represent.
 - parser must support special floating point values (nan, inf)
 - special floating point types can only be sent as tagged trings (nan, inf)
 - parser MUST ignore capitalization: NaN or nan,Inf,inf,+Inf,-Inf,+inf,-inf
 - only hex floats and special values can be sent as tagged string `@float "nan"`

## ARSON lists (mandatory):

 - use `[` and `]`
 - allow trailing commas
 - lists of same size and items are same
 - can be tagged `@list [1,2,3,]`

 Two keys are the same if

 - both strings and same codepoints (unnormalized)
 - same numerical value i.e `1` and `1.0` and `1.0e0` are the same key, `+0.0`, `-0.0` are the same key

Note: Semantics of `NaN` keys, or collections containing them are implementation defined.

## ARSON records (mandatory) 

 - akin to JSON objects, uses `{` and `}`
 - insertion order must be preserved
 - no duplicate keys: parser MUST reject
 - allow trailing commas
 - implementations MUST support string keys
 - records of same size and key-value pairs are same, ignoring order
 - can be tagged `@record {"a":1}`

 Two keys are the same if

 - both strings and same codepoints (unnormalized)
 - same numerical value i.e `1` and `1.0` and `1.0e0` are the same key, `+0.0`, `-0.0` are the same key
 
Note: Semantics of `NaN` keys, or collections containing them are implementation defined.

## ARSON tagged objects (mandatory):

 - contain a name and an untagged arson literal.
 - tagged objects do not nest, `@foo @bar {}` is an error.
 - space between tag name and object is *mandatory*, must not be tab or newline or bom
 - tag name is any ascii letter followed by letters, digits or `_`
 - parsers MAY support unicode tag names, but MUST support ascii ones
 - every type has a reserved tag name
 - `@int 1`, `@string "two"` are just `1` and `"two"`
 - parsers MAY support optional types but MUST support mandatory types in tagged form
 - parsers MAY reject unknown, or return a wrapped object 

### ARSON C99 float strings (optional, recommended):

 - floats can be sent as tagged strings
 - string can contain decimal or hexidecimal format strings
 - no underscores allowed in hexadecimal floats
 - special floating point types can only be sent as strings (nan, inf)
 - parser MUST ignore capitalization: NaN or nan,Inf,inf,+Inf,-Inf,+inf,-inf
 - hex floats are C99 style, sprintf('%a') format
 - `<sign>0x<hex mantissa>p<sign><decimal exponent>` or `...1x...` for subnormals.

### ARSON sets (optional, recommended):

 - `@set [1,2,3]`
 - always a tagged list
 - no duplicate items, same rules as records
 - ordering does not matter when comparing
 - equality rules are same as other collections
 - sort order is only defined for keys of the same type

### ARSON dicts (optional, recommended):

This is for compatibility with hash tables without insertion order preservation.

 - `@dict {"a":1}` 
 - keys must be emitted in lexical order, must round trip in same order.
 - keys must all be the same type: number or string 
 - no duplicate items, same rules as records
 - a `@dict` is equal to a record if it has same keys, ignoring order.
 - sort order is only defined for keys of the same type


### ARSON datetimes/periods (optional, recommended):

 - Datetimes are sent as tagged strings.
 - `@datetime "2017-11-22T23:32:07.100497Z"`
 - Periods are sent as tagged numbers.
 - `@duration 60` (in seconds, float or int)
 - Datetimes are in RFC 3339 format in UTC, (i.e 'Zulu time')
 - UTC MUST use `Z` suffix
 - Implementations SHOULD convert times to UTC, or reject them outright.

Note: local timestamps, or other timezone formats are not covered by this spec. They
may be added in future versions, likely via a different tag.

### ARSON bytestrings (optional, recommended):

 - bytestrings are arrays of bytes without an encoding
 - parser SHOULD return a bytestring type if possible
 - `@bytestring "....\xff"` 
 - same escape as strings, but can't have `\u` `\U` escapes > 0xFF
 - like strings, C0, C1 must be escaped.
 - parsers SHOULD escape all non-ascii chracters too
 - parsers MAY encode bytestrings using base64 `@base64 "...=="`

### ARSON complex numbers: (optional, recommended)

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

## Builtin/Reserved Tagged literals:

Pass throughs (i.e `@foo bar` is `bar`):

 - `@object` on any literal
 - `@bool` on true, or false (not strings)
 - `@int` on ints
 - `@float` on ints or floats
 - `@string` on strings
 - `@list` on lists
 - `@record` on records

Tags that transform the literal:

 - @float on strings (for C99 hex floats, including NaN, -Inf, +Inf)
 - @string on lists of strings (joins them into one string)
 - @dict on records
 - @duration on numbers (returns seconds)
 - @datetime on strings (utc timestamp)
 - @base64 on strings (into a bytesting)
 - @bytestring on strings (into a bytestring)
 - @set on lists 
 - @complex on lists
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


# ARSON Grammar

Note: This is still being drafted, if this conflicts with the spec above, the spec is right.

```
arson_whitespace <--- (' ' | '\t' | '\r' | '\n' | '\uFEFF')*

newline <--- '\n' | end_of_file

arson_comment <---
    (arson_whitespace, '#', not(newline)*, newline)*,
    arson_whitespace

arson_document <---
    arson_comment, arson_value, arson_comment

arson_value <---
    ( '@', arson_tag, ' '*, arson_literal) | arson_literal
 
arson_tag <---
    range('a-z', 'A-Z'),
    (range('0-9', 'a-z', 'A-Z') | '_')*

arson_literal <---
    'true' | 'false' | 'null'
    arson_number | arson_string |
    arson_list | arson_ object

arson_number <---
    arson_hex_number | arson_octal_number |
    arson_binary_number | arson_decimal_number |
    arson_float_number

arson_hex_number <---
    ('+'|'-')?, '0x', range('0-9', 'A-F', 'a-f'),
    range('0-9', 'A-F', 'a-f','_')*

arson_octal_number <---
    ('+'|'-')?, '0o', range('0-7'),
    range('0-7','_')*

arson_binary_number <--
    ('+'|'-')?, '0b', range('0-1'),
    range('0-1','_')*

arson_decimal_number <---
    ('+'|'-')?,  range('0-9'),
    range('0-9','_')*

arson_float_number <---
    ('+'|'-')?,  range('0-9'), range('0-9','_')*,
    ( ".", range('0-9','_')* )?,
    ("e" | "E"), ('+'|'-')?, range('0-9','_') )?
    
arson_string <---
    ( "'", arson_single_quoted_string "'") |
    ( '"', arson_double_quoted_string, '"')

arson_single_quoted_string <--
    ( 
        not(range("\x00-\x1f", "\\", "\'", "\uD800-\uDFFF")) |
        arson_string_escape
    )*
    
arson_double_quoted_string <--
    ( 
        not(range('\x00-\x1f', '\\', '\"', "\uD800-\uDFFF")) |
        arson_string_escape
    )*

arson_string_escape <--
    ('\\', ("\""|"\\"|"/"|"b"|"f"|"n"|"r"|"t"|"'"|"\n")) |
    ('\\x', range("0-9", "a-f", "A-F"){2}) |
    ('\\u', range("0-9", "a-f", "A-F"){4}) |
    ('\\U', range("0-9", "a-f", "A-F"){8})

arson_list <---
    '[', 
        arson_comment, 
        ( arson_value, 
            (arson_comment, ',', arson_comment, arson_value)*,
            arson_comment,
            (',', arson_comment)?
        )?,
    ']'

arson_object <---
    '{', 
        arson_comment, 
        ( arson_object_entry,
            (arson_comment, ',', arson_comment, arson_object_entry)*,
            arson_comment,
            (',', arson_comment)?
        )?,
    '}'

arson_object_entry <---
    arson_string, arson_comment, ':', arson_comment, arson_value
```

