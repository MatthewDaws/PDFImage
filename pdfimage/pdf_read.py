"""
pdf_read.py
~~~~~~~~~~~

Read PDF files.  We try to support many files, but probably exotic PDF files
will break.
"""

from .pdf import *
import io as _io
from .pdf_parser import PDFParser, PullBytesStream, StreamParser, ParseDictionary

_EOL_SET = {b"\n", b"\r"}
_WHITESPACE_SET = {b"\x00", b"\x09", b"\x0a", b"\x0c", b"\x0d", b"\x20"}
_DELIMITERS = b"()<>[]{}/%"
_DIGITS = b"0123456789"

class PDFLineReader():
    """Wraps a file-like object and allows reading "lines" in the meaning of
    PDF files.  Maintains the file position pointer.

    :param file: File type object, opened in "rb" mode.  If not a file, then
      should be a `bytes` object.
    """
    def __init__(self, file):
        try:
            self._file = _io.BytesIO(file)
        except TypeError:
            self._file = file

    def read(self, n=-1):
        """Read the next `n` bytes without processing; if `n==-1` (the default)
        the read to the EOF."""
        return self._file.read(n)

    def readline(self):
        """Read a line using the PDF convention for when a line stops."""
        location = self._file.tell()
        chunk_size = 1024
        data = b""
        while True:
            x = self._file.read(chunk_size)
            if len(x) == 0:
                break
            i1 = x.find(b"\x0d")
            i2 = x.find(b"\x0a")
            if i1 != -1 or i2 != -1:
                if i1 == -1:
                    data = data + x[:i2+1]
                    break
                elif i2 == -1:
                    data = data + x[:i1+1]
                    break
                elif i2 == i1 + 1:
                    data = data + x[:i1+2]
                    break
                else:
                    data = data + x[:min(i1, i2)+1]
                    break
            data = data + x
        self._file.seek(location + len(data))
        return data


class PDFLineReaderComments(PDFLineReader):
    """Wraps a file-like object and allows reading "lines" in the meaning of
    PDF files.  Maintains the file position pointer.  Removes comments
    automatically.

    :param file: File type object, opened in "rb" mode.  If not a file, then
      should be a `bytes` object.
    """
    def __init__(self, file):
        super().__init__(file)

    def readline(self):
        self._last_line = super().readline()
        i = self._last_line.find(b"%")
        if i > -1:
            return self._last_line[:i]
        return self._last_line

    @property
    def last_raw_line(self):
        """The last line read, _without_ comments removed."""
        if not hasattr(self, "_last_line"):
            raise AttributeError("Haven't read any lines yet")
        return self._last_line


def split_by_whitespace(line):
    """Convert the passed `line` into an array of bytes objects, splitting on
    the PDF notion of whitespace."""
    out = []
    index = 0
    current_token = b""
    while index < len(line):
        if line[index:index+1] in _WHITESPACE_SET:
            if len(current_token) > 0:
                out.append(current_token)
                current_token = b""
        else:
            current_token += line[index:index+1]
        index += 1
    if len(current_token) > 0:
        out.append(current_token)
    return out


class PDF():
    """Read a PDF file.

    :param file: A filename or file like object (which needs to be opened in
      read and binary mode).
    """
    def __init__(self, file):
        try:
            self._file = open(file, "rb")
        except TypeError:
            self._file = file

        self._validate()
        self._read_tail()

    @property
    def version(self):
        """The version string of the PDF file."""
        return self._version

    @property
    def trailer(self):
        """The :class:`PDFDictionary` object which is the trailer."""
        return self._trailer_dictionary

    @property
    def object_lookup(self):
        """Dictionary from :class:`PDFObjectId` objects to location"""
        return self._obj_lookup

    def _decimal_number_from(self, data):
        out = b""
        i = 0
        while len(data) > i and data[i:i+1] in _DIGITS:
            out += data[i:i+1]
            i += 1
        if len(out) == 0:
            return None
        return out

    def _parse_object_header(self, stream):
        stream.skip_whitespace()
        obj_id = self._decimal_number_from(stream)
        if obj_id is None:
            return None
        stream.read(len(obj_id))

        stream.skip_whitespace()
        gen_id = self._decimal_number_from(stream)
        if gen_id is None:
            return None
        stream.read(len(gen_id))
        
        stream.skip_whitespace()
        if stream[:3] != b"obj":
            return None

        return obj_id, gen_id

    def object_at(self, location):
        """Read the object at the given location in the file.
        We have to handle streams, which we often cannot decode without reading
        another object.

        :return: List of PDF objects.  If the final object should be a stream,
            the final entry will be a placeholder, :class:`PDFStreamIndicator`.
        """
        self._file.seek(location)
        
        stream = PullBytesStream(self._file)
        header = self._parse_object_header(stream)
        if header is None:
            raise ValueError("Line at {} not an object definition".format(location))
        obj_id, gen_id = [int(x.decode()) for x in header]

        p = PDFParser(self._file)
        objects = list(p)
        if repr(objects[-1]).startswith("PDFDictionary") and p.stream[:6] == b"stream":
            objects.append(PDFStreamIndicator(p.stream.tell()))
        elif p.stream[:6] != b"endobj":
            raise ValueError("Finished parsing object, but not ended by endobj marker: {}".format(p.stream[:6]))
        return objects

    def read_stream(self, location, length):
        """Reads a stream, returning a stream object.

        :param location: Location in the PDF file where the stream is.
        :param length: Length of the stream.
        """
        self._file.seek(location)
        stream = PullBytesStream(self._file)
        parser = StreamParser(length)
        result = parser.parse(stream)
        if result is None:
            raise ValueError("Not a valid stream at this location: {}".format(location))
        return result[0]

    def full_object_at(self, location):
        """Read the object at the given location in the file.  Recursively
        follows references to "indirect objects" and adds streams.

        Note that it is quite allowed that PDF files can contain cyclic
        relations (thanks to the "/Parent" name, for example).  So care is
        required!

        :return: A single PDF object.
        """
        objs = self.object_at(location)
        if not (len(objs) == 1 or (len(objs) == 2 and isinstance(objs[1], PDFStreamIndicator))):
            raise ValueError("Not a single object...")
        obj = self._recurse_populate(objs[0])
        if len(objs) == 2:
            length = int(obj[PDFName("Length")].value)
            stream = self.read_stream(objs[1].location, length)
            return PDFStream(list(obj.items()), stream.contents)
        return obj

    def _recurse_populate(self, obj):
        def should_recurse(obj):
            return isinstance(obj, PDFArray) or isinstance(obj, PDFDictionary)
        
        def make_new_object(old_obj):
            if isinstance(old_obj, PDFObjectId):
                if old_obj not in self.object_lookup:
                    return PDFNull()
                location = self.object_lookup[old_obj]
                return self.full_object_at(location)
            elif should_recurse(old_obj):
                return self._recurse_populate(old_obj)
            return old_obj
        
        if isinstance(obj, PDFArray):
            return PDFArray([make_new_object(ob) for ob in obj])
        if isinstance(obj, PDFDictionary):
            return PDFDictionary([(k, make_new_object(ob)) for k, ob in obj.items()])
        return obj

    def _tail(self, chunk_size = 2048):
        """Return a chunk at the end of the file."""
        self._file.seek(0, 2)
        file_length = self._file.tell()
        if file_length <= chunk_size:
            self._file.seek(0)
            return self._file.read()
        self._file.seek(-chunk_size, 2)
        return self._file.read()

    @staticmethod
    def is_end_of_line(data, offset):
        return data[offset:offset+1] in _EOL_SET

    @staticmethod
    def find_last_occurance(data, bytes):
        reversed_data = data[::-1]
        reversed_index = -1
        while True:
            reversed_index = reversed_data.find(bytes[::-1], reversed_index+1)
            if reversed_index == -1:
                return -1
            index = len(data) - reversed_index - len(bytes)
            if PDF.is_end_of_line(data, index + len(bytes)):
                return index

    def _read_tail(self):
        data = self._tail()
        eof_index = self.find_last_occurance(data, b"%%EOF")
        startxref_index = self.find_last_occurance(data[:eof_index], b"startxref")
        lr = PDFLineReaderComments(data[startxref_index:])
        lr.readline()
        xref_offset = int(lr.readline().strip().decode())

        trailer_index = self.find_last_occurance(data[:eof_index], b"trailer")
        parser = PDFParser(_io.BytesIO(data[trailer_index+7:]))
        self._trailer_dictionary = list(parser)[0]
        if PDFName("Prev") in self._trailer_dictionary:
            raise ValueError("Files with more than one cross-reference not currently supported")

        self._read_xrefs(xref_offset)

    def _read_xrefs(self, offset):
        self._file.seek(offset)
        lr = PDFLineReaderComments(self._file)
        if lr.readline().strip() != b"xref":
            raise ValueError("Didn't find xref at {}", offset)
        objects = []
        while True:
            line = lr.readline().strip()
            try:
                start, count = [int(x) for x in line.decode().split(" ")]
            except:
                break
            for row in range(count):
                line = lr.readline().strip()
                location, generation, ty = line.decode().split(" ")
                location = int(location)
                generation = int(generation)
                if ty == "n":
                    objects.append((row+start, location, generation))
        self._obj_lookup = {PDFObjectId(n, g) : loc for n, loc, g in objects}

    def _validate(self):
        self._file.seek(0)
        data = self._file.read(9)
        if not data[:5] == b"%PDF-" or data[-1:] not in _WHITESPACE_SET:
            raise ValueError("Initial byte marker {} is not a PDF file".format(data))
        self._version = data[:8].decode()


class PDFStreamIndicator():
    def __init__(self, location):
        self._loc = location

    @property
    def location(self):
        """The location in the PDF file where the stream begins."""
        return self._loc
