"""
pdf.py
~~~~~~

Common data structures for PDF files.
"""

import collections as _collections

class PDFObjectId():
    """Identified for a PDF object.

    :param number: The number of the object
    :param generation: The "generation" of the object
    """
    def __init__(self, number, generation):
        self._num = number
        self._gen = generation
        if self._num <=0 or self._gen < 0:
            raise ValueError()

    @property
    def number(self):
        return self._num

    @property
    def generation(self):
        return self._gen
    
    def __eq__(self, other):
        return isinstance(other, PDFObjectId) and self._num == other._num and self._gen == other._gen

    def __hash__(self):
        return hash(str(self._num) + str(self._gen))

    def __repr__(self):
        return "PDFObjectId({}, {})".format(self._num, self._gen)

    def __bytes__(self):
        return "{} {} R".format(self._num, self._gen).encode()


class PDFObject(PDFObjectId):
    """A PDF object.

    :param number: The number of the object
    :param generation: The "generation" of the object
    :param data: Contents of the object.
    """
    def __init__(self, number, generation, data):
        super().__init__(number, generation)
        self._data = data

    @property
    def data(self):
        return self._data

    def __repr__(self):
        return "PDFObject({}, {})".format(self._num, self._gen)

    def __bytes__(self):
        raise NotImplementedError()


class PDFBoolean():
    def __init__(self, value):
        self._v = value

    @property
    def value(self):
        return self._v

    def __bool__(self):
        return self._v == True

    def __eq__(self, other):
        return isinstance(other, PDFBoolean) and self._v == other._v

    def __hash__(self):
        return hash(bytes(self))

    def __repr__(self):
        return "PDFBoolean({})".format(bool(self))

    def __bytes__(self):
        if bool(self):
            return b"true"
        return b"false"


class PDFNumeric():
    """A numeric object.  Initialise with an int, a float, or a string or bytes.
    Raises `ValueError` on failure to convert."""
    def __init__(self, value):
        if isinstance(value, bytes):
            value = value.decode()
        if isinstance(value, str):
            if "." in value:
                value = float(value)
            else:
                value = int(value)
        self._v = value

    @property
    def value(self):
        return self._v

    def __eq__(self, other):
        return isinstance(other, PDFNumeric) and  self._v == other._v

    def __hash__(self):
        return hash(self._v)

    def __int__(self):
        return int(self._v)

    def __float__(self):
        return float(self._v)

    def __repr__(self):
        return "PDFNumeric({})".format(self._v)

    def __bytes__(self):
        return str(self._v).encode()


class PDFString():
    """Actually a _bytes_ string!"""
    def __init__(self, value):
        try:
            self._v = bytes(value)
        except TypeError:
            self._v = value.encode()

    @property
    def value(self):
        return self._v

    def __eq__(self, other):
        return isinstance(other, PDFString) and self._v == other._v

    def __hash__(self):
        return hash(self._v)

    def __repr__(self):
        return "PDFString({})".format(self._v)

    def __bytes__(self):
        out = b"("
        for i in range(len(self._v)):
            x = self._v[i:i+1]
            if x == b"\n":
                out += b"\\n"
            elif x == b"\r":
                out += b"\\r"
            elif x == b"\t":
                out += b"\\t"
            elif x == b"\b":
                out += b"\\b"
            elif x == b"\f":
                out += b"\\f"
            elif x == b"(":
                out += b"\\("
            elif x == b")":
                out += b"\\)"
            elif x == b"\\":
                out += b"\\\\"
            else:
                out += x
        return out + b")"


class PDFName():
    def __init__(self, name):
        try:
            self._v = bytes(name)
        except TypeError:
            self._v = name.encode()

    @property
    def name(self):
        return self._v

    def __eq__(self, other):
        return isinstance(other, PDFName) and self._v == other._v

    def __hash__(self):
        return hash(self._v)

    def __repr__(self):
        return "PDFName({})".format(self._v)

    def __bytes__(self):
        out = b"/"
        for x in self._v:
            if x >= 33 and x <= 126:
                out += bytes([x])
            elif x == 0:
                raise ValueError("Cannot have 0 byte in name")
            else:
                h = hex(x)[2:].upper().encode()
                if len(h) == 1:
                    h = b"0" + h
                out += b"#" + h
        return out


class PDFNull():
    def __eq__(self, other):
        return isinstance(other, PDFNull)

    def __repr__(self):
        return "PDFNull()"

    def __bytes__(self):
        return b"null"


class PDFArray():
    def __init__(self, entries=[]):
        self._v = list(entries)

    def __getitem__(self, i):
        return self._v[i]

    def __eq__(self, other):
        return isinstance(other, PDFArray) and self._v == other._v

    def __hash__(self):
        return hash(self._v)

    def __repr__(self):
        return "PDFArray({})".format(self._v)

    def __bytes__(self):
        out = b" ".join(bytes(x) for x in self._v)
        return b"[" + out + b"]"


class PDFDictionary(_collections.UserDict):
    def __init__(self, entry_pairs=[]):
        super().__init__()
        for k, v in entry_pairs:
            self.data[k] = v

    def __hash__(self):
        return hash(self.data)

    def __eq__(self, other):
        return isinstance(other, PDFDictionary) and self.data == other.data

    def __repr__(self):
        return "PDFDictionary({})".format(self.data)

    def __bytes__(self):
        out = b"\n".join(b" ".join([bytes(k) for k in x]) for x in self.data.items())
        return b"<<" + out + b">>"


class PDFRawStream():
    """Raw because the associated dictionary is not present."""
    def __init__(self, data):
        self._v = bytes(data)

    @property
    def contents(self):
        return self._v

    def __eq__(self, other):
        return isinstance(other, PDFRawStream) and self._v == other._v

    def __hash__(self):
        return hash(self._v)

    def __repr__(self):
        return "PDFRawStream(length={})".format(len(self._v))

    def __bytes__(self):
        return b"stream\n" + self._v + b"\nendstream"


class PDFStream(PDFDictionary):
    """Combines a dictionary and the associated stream."""
    def __init__(self, entry_pairs, stream_data):
        super().__init__(entry_pairs)
        self._stream_data = stream_data

    @property
    def stream_contents(self):
        return self._stream_data

    def __hash__(self):
        return hash(self.data) + hash(self._stream_data)

    def __eq__(self, other):
        return (isinstance(other, PDFStream) and self.data == other.data
            and self._stream_data == other._stream_data)

    def __repr__(self):
        return "PDFDictionary({}, stream length={})".format(self.data, len(self._stream_data))

    def __bytes__(self):
        out = b"\n".join(b" ".join([bytes(k) for k in x]) for x in self.data.items())
        out = b"<<" + out + b">>"
        return out + b"\n" + b"stream\n" + self._stream_data + b"\nendstream"
