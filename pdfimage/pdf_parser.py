"""
pdf_parser.py
~~~~~~~~~~~~~

Does the hard work of parsing low-level PDF into Python objects.
"""

from .pdf import *
import io as _io

_WHITESPACE = b"\x00\x09\x0a\x0c\x0d\x20"
_DELIMS = b"\x00\x09\x0a\x0c\x0d\x20()<>[]{}/%"


class PullBytesStream():
    """Wrap a file-like object, and allow access to the data as if it were a
    `bytes` object, buffering more data on demand."""
    def __init__(self, file):
        try:
            self._file = _io.BytesIO(file)
        except TypeError:
            self._file = file
        self._buffer = b""
        self._length = None

    def skip_whitespace(self):
        """Advance the position over any whitespace"""
        self.read(length_suffix_whitespace(self))

    def _length_left(self):
        location = self._file.tell()
        self._file.seek(0, 2)
        total_length = self._file.tell()
        self._file.seek(location)
        return total_length - location

    def tell(self):
        """The current effective file position."""
        return self._file.tell() - len(self._buffer)

    def read(self, n=-1):
        """Read the next `n` bytes without processing; if `n==-1` (the default)
        the read to the EOF."""
        if n < -1:
            raise ValueError()
        buf = self._buffer
        if n == -1:
            self._buffer = b""
            self._length = None
            return buf + self._file.read()
        if n <= len(buf):
            self._buffer = buf[n:]
            return buf[:n]
        self._buffer = b""
        self._length = None
        return buf + self._file.read(n - len(buf))

    def buffer(self, n):
        """Ensure we have `>= n` bytes in the internal buffer, if possible."""
        missing = n - len(self._buffer)
        if missing > 0:
            self._length = None
            self._buffer += self._file.read(missing)

    def __getitem__(self, place):
        if hasattr(place, "step"):
            places = list(range(len(self))[place])
            self.buffer(max(places) + 1)
            return bytes(self._buffer[p] for p in places)
        else:
            if place < 0:
                raise IndexError()
            self.buffer(place + 1)
            if place >= len(self._buffer):
                raise IndexError()
            return self._buffer[place]

    def __len__(self):
        if self._length is None:
            self._length = self._length_left()
        return self._length + len(self._buffer)


class ParseError(Exception):
    """Exception thrown on a parsing error."""
    def __init__(self, msg=None):
        super().__init__(msg)


def length_suffix_whitespace(data, start_index=0):
    """Return the length of whitespace at the start of the byte array `data`.
    
    :param data: Array-like object to look at
    :param start_index: Where to start looking, defaults to 0
    """
    index = start_index
    while True:
        if len(data) <= index:
            return index - start_index
        if data[index:index+1] not in _WHITESPACE:
            return index - start_index
        index += 1

def bytes_in_context(data, index):
    """Helper method to display a useful extract from a buffer."""
    start = max(0, index - 10)
    end = min(len(data), index + 15)
    return data[start:end]

def at_eol_marker(data, index):
    """Is the array at index indicating an end of line (eol)?

    :return: The number of bytes indicating the eol, or 0 if no eol.
    """
    if len(data) > index and data[index:index+1] == b"\x0a":
        return 1
    if len(data) > index+1 and data[index:index+2] == b"\x0d\x0a":
        return 2
    if len(data) > index and data[index:index+1] == b"\x0d":
        return 1
    return 0


class Parser():
    """Abstract base class for parsers."""
    def parse(self, data):
        """Parse the bytes buffer `data`

        :return: `None` if this token is not for us.

          Otherwise, pair `(obj, used)` where `obj` is a pdf object we have
          parsed, and `used` is the number of bytes consumed.  If `obj` is
          `None` then we expect :meth:`consumer` to return a consumer.
        """
        raise NotImplementedError()

    def consumer(self):
        """An object to route further generated objects to, or `None` to
        process directly.  Should be an instance of :class:`Consumer`"""
        return None


class BooleanParser(Parser):
    def parse(self, data):
        if len(data) >= 4 and data[:4] == b"true":
            if len(data) == 4 or data[4] in _DELIMS:
                return PDFBoolean(True), 4
        if len(data) >= 5 and data[:5] == b"false":
            if len(data) == 5 or data[5] in _DELIMS:
                return PDFBoolean(False), 5
        return None


class NumericParser(Parser):
    _NUMERICS = b"0123456789.+-"
    def parse(self, data):
        index = 0
        while index < len(data) and data[index] in self._NUMERICS:
            index += 1
        if index == 0:
            return None
        if index < len(data) and data[index] not in _DELIMS:
            raise ParseError("Number not ended by delimiter in {}".format(bytes_in_context(data, index)))
        try:
            return PDFNumeric(data[:index]), index
        except ValueError:
            raise ParseError("Not a valid numeric: {}".format(bytes_in_context(data, index)))


class StringParser(Parser):
    _OCT_DIGITS = b"01234567"

    def parse(self, data):
        if data[0:1] != b"(":
            return None
        out = b""
        index = 1
        while index < len(data):
            ch = data[index:index+1]
            if ch == b")":
                break
            elif ch == b"\n" or ch == b"\r":
                if index + 1 < len(data) and data[index:index+2] == b"\r\n":
                    index += 1
                out += b"\n"
            elif ch == b"\x5c": # Backslash
                if index + 1 == len(data):
                    raise ParseError("Backslash ends datastream")
                ch = data[index+1:index+2]
                if ch == b"\x0a" or ch == b"\x0d":
                    if ch == b"\x0d" and index + 2 < len(data) and data[index+2] == 10:
                        index += 2
                    else:
                        index += 1
                elif ch == b"n":
                    out += b"\x0a"
                    index += 1
                elif ch == b"r":
                    out += b"\x0d"
                    index += 1
                elif ch == b"t":
                    out += b"\t"
                    index += 1
                elif ch == b"b":
                    out += b"\b"
                    index += 1
                elif ch == b"f":
                    out += b"\f"
                    index += 1
                elif ch == b"(":
                    out += b"("
                    index += 1
                elif ch == b")":
                    out += b")"
                    index += 1
                elif ch == b"\\":
                    out += b"\\"
                    index += 1
                elif ch in self._OCT_DIGITS:
                    i = index + 1
                    while i < len(data) and data[i:i+1] in self._OCT_DIGITS and i - index < 4:
                        i += 1
                    octal = data[index+1:i]
                    decimal = 0
                    for x in octal:
                        digit = x - 48
                        decimal = 8 * decimal + digit
                    if decimal >= 256:
                        raise ParseError("Invalid octal: {}".format(bytes_in_context(data, index)))
                    out += bytes([decimal])
                    index = i - 1
                else:
                    pass
            else:
                out += ch
            index += 1
        if data[index:index+1] != b")":
            raise ParseError("String not closed with ')'")
        return PDFString(out), index+1


class HexStringParser(Parser):
    _HEX = b"0123456789ABCDEF"

    @staticmethod
    def _hex_to_bytes(hex_pair):
        decimal = 0
        for x in hex_pair.upper():
            digit = HexStringParser._HEX.find(x)
            if digit < 0:
                raise ParseError()
            decimal = 16 * decimal + digit
        return bytes([decimal])

    def parse(self, data):
        if data[0:1] != b"<":
            return None
        out = b""
        index = 1
        current_pair = b""
        while index < len(data):
            ch = data[index:index+1]
            try:
                if ch == b">":
                    if len(current_pair) == 1:
                        out += self._hex_to_bytes(current_pair + b"0")
                    break
                elif ch in _WHITESPACE:
                    pass
                elif ch.upper() in self._HEX:
                    current_pair += ch
                    if len(current_pair) == 2:
                        out += self._hex_to_bytes(current_pair)
                        current_pair = b""
                else:
                    raise ParseError()
            except ParseError:
                raise ParseError("Not a valid hex string: {}".format(bytes_in_context(data, index)))
            index += 1
        if index == len(data):
            raise ParseError("Not a valid hex string: {}".format(bytes_in_context(data, index)))
        return PDFString(out), index + 1
        

class ParseName(Parser):
    def parse(self, data):
        if data[:1] != b"/":
            return None
        out = b""
        index = 1
        while index < len(data):
            ch = data[index:index+1]
            if ch in _DELIMS:
                break
            if ch == b"#":
                if index + 2 >= len(data):
                    raise ParseError("Not a valid # code in name: {}".format(bytes_in_context(data, index)))
                out += HexStringParser._hex_to_bytes(data[index+1:index+3])
                index += 3
            else:
                out += ch
                index += 1
        return PDFName(out), index


class ParseNull(Parser):
    def parse(self, data):
        if len(data) < 4:
            return None
        if data[:4] != b"null":
            return None
        if len(data) > 4 and data[4:5] not in _DELIMS:
            return None
        return PDFNull(), 4


class ParseObjectId(Parser):
    _DIGITS = b"0123456789"
    
    def _parse_number(self, data, index):
        num_chs = b""
        while index < len(data) and data[index:index+1] in self._DIGITS:
            num_chs += data[index:index+1]
            index += 1
        if index == len(data):
            return None
        if data[index:index+1] not in _WHITESPACE:
            return None
        return int(num_chs.decode()), index+1
        
    def parse(self, data):
        idnum = self._parse_number(data, 0)
        if idnum is None:
            return None
        idnum, index = idnum
        gennum = self._parse_number(data, index)
        if gennum is None:
            return None
        gennum, index = gennum
        if index + 1 >= len(data):
            return None
        if data[index:index+1] == b"R" and data[index+1:index+2] in _DELIMS:
            return PDFObjectId(idnum, gennum), index + 1
        return None


class ParseArray(Parser):
    def parse(self, data):
        if len(data) > 0 and data[0:1] == b"[":
            return None, 1
        return None

    def consumer(self):
        return ArrayConsumer()


class Consumer():
    """Abstract base class for "consumers" which combine a number of objects"""
    def consume(self, obj):
        """Send constructed objects here."""
        raise NotImplementedError()

    def end(self, data):
        """Does the current `data` give a token which says that this container
        object is ended?
        
        :return: `None` to indicate we have not processed the stream; or an int
          count of how many bytes we consumed.
        """
        raise NotImplementedError()

    def build(self):
        """Return the container object."""
        raise NotImplementedError()


class ArrayConsumer(Consumer):
    def __init__(self):
        self._array = []

    def consume(self, obj):
        self._array.append(obj)

    def end(self, data):
        if len(data) > 0 and data[0:1] == b"]":
            return 1
        return None

    def build(self):
        return PDFArray(self._array)


class ParseDictionary(Parser):
    def parse(self, data):
        if len(data) > 1 and data[0:2] == b"<<":
            return None, 2
        return None

    def consumer(self):
        return DictionaryConsumer()


class DictionaryConsumer(Consumer):
    def __init__(self):
        self._dict_items = []
        self._current_key = None

    def consume(self, obj):
        if self._current_key is None:
            self._current_key = obj
        else:
            self._dict_items.append((self._current_key, obj))
            self._current_key = None

    def end(self, data):
        if len(data) > 1 and data[0:2] == b">>":
            return 2
        return None

    def build(self):
        return PDFDictionary(self._dict_items)


class StreamParser(Parser):
    """An annoying special case: should only be called immediately after
    building a dictionary.  Need to know the expected length!  This is even
    harder, because the length is allowed to be an indirect object, so this
    module cannot know the length.
    
    :param length: The number of bytes in this stream
    """
    def __init__(self, length):
        self._len = length

    def parse(self, data):
        if len(data) < 6 or data[:6] != b"stream":
            return None
        have_lf = (len(data) >=7 and data[6:7] == b"\x0a")
        have_cr_lf = (len(data) >=8 and data[6:8] == b"\x0d\x0a")
        if not(have_lf or have_cr_lf):
            return None
        if have_lf:
            index = 7
        else:
            index = 8
        
        expected_end = index + self._len
        if expected_end > len(data):
            raise ParseError("Not enough data to form the stream!")
        stream_data = data[index:expected_end]
        eolbytes = at_eol_marker(data, expected_end)
        if expected_end + eolbytes + 9 > len(data):
            raise ParseError("Not enough data to allow for endstream marker")
        if data[expected_end + eolbytes:expected_end + eolbytes + 9] != b"endstream":
            raise ParseError("Stream does not end with endstream marker")
        
        return PDFRawStream(stream_data), expected_end + eolbytes + 9


class PDFParser():
    """Does the hard work of parsing low-level code into PDF objects.
    
    :param file: file-like object to read bytes from.
    """
    def __init__(self, file):
        self._pbs = PullBytesStream(file)
        self._parsers = [BooleanParser(), ParseObjectId(), NumericParser(),
                StringParser(), ParseDictionary(), HexStringParser(),
                ParseName(), ParseNull(), ParseArray()]

    def __iter__(self):
        consumers = []
        while True:
            self._pbs.skip_whitespace()
            if len(self._pbs) == 0:
                return
            parser, obj, used_bytes = self._find_parser()
            if parser is None:
                while len(consumers) > 0:
                    consumer = consumers[-1]
                    used_bytes = consumer.end(self._pbs)
                    if used_bytes is not None:
                        self._pbs.read(used_bytes)
                        obj = consumer.build()
                        consumers.pop()
                if obj is not None:
                    yield obj
                    continue
                return

            self._pbs.read(used_bytes)
            if obj is None:
                consumers.append(parser.consumer())
                continue
            
            while len(consumers) > 0 and obj is not None:
                consumer = consumers[-1]
                consumer.consume(obj)
                self._pbs.skip_whitespace()
                used_bytes = consumer.end(self._pbs)
                if used_bytes is not None:
                    self._pbs.read(used_bytes)
                    obj = consumer.build()
                    consumers.pop()
                else:
                    obj = None
            if obj is not None:
                yield obj

    def _find_parser(self):
        for p in self._parsers:
            result = p.parse(self._pbs)
            if result is None:
                continue
            return (p, *result)
        return None, None, None

    @property
    def stream(self):
        """The stream reader object; for accessing the data stream in an
        array-like manner."""
        return self._pbs
