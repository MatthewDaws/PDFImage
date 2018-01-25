"""
pdf_read.py
~~~~~~~~~~~

Read PDF files.  We try to support many files, but probably exotic PDF files
will break.
"""

from .pdf import *
import io as _io

_EOL_SET = {b"\n", b"\r"}
_WHITESPACE_SET = {b"\x00", b"\x09", b"\x0a", b"\x0c", b"\x0d", b"\x20"}
_DELIMITERS = b"()<>[]{}/%"

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
    def object_lookup(self):
        """Dictionary from :class:`PDFObjectId` objects to location"""
        return self._obj_lookup

    def object_at(self, location):
        """Read the object at the given location in the file."""
        self._file.seek(location)
        lr = PDFLineReaderComments(self._file)
        header = split_by_whitespace(lr.readline())
        if len(header) != 3 or header[2] != b"obj":
            raise ValueError("Line at {} not an object definition: '{}'".format(location, header))
        try:
            obj_id = int(header[0])
            gen_id = int(header[1])
        except ValueError:
            raise ValueError("Line at {} not a valid object definition: '{}'".format(location, header))
        # TODO

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
        # TODO: Read the trailer dictionary
        # CHECK for Prev

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

