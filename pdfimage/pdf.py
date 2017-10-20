"""
pdf.py
~~~~~~

(Very) simple I/O for PDF files.  I am fairly confident it produces well-formed
output, but it cannot parse all input files.

Some resources:

- https://stackoverflow.com/questions/10935091/imagemagick-generate-raw-image-data-for-pdf-flate-embedding
- https://www.prepressure.com/pdf/basics/compression
- https://www.adobe.com/devnet/pdf/pdf_reference.html
"""

import collections as _collections
import re as _re

class OBJ():
    """The main building block of a PDF file.
    
    :param n:
    :param m:
    :param contents:
    """
    def __init__(self, n, m, contents):
        self._n = n
        self._m = m
        self._contents = contents

    @property
    def n(self):
        return self._n

    @property
    def m(self):
        return self._m

    @property
    def contents(self):
        return self._contents

class XREF():
    """The PDF index is composed of these objects."""
    def __init__(self, offset, generation, inuse):
        self._offset = offset
        self._generation = generation
        self._inuse = inuse

    @property
    def offset(self):
        return self._offset

    @property
    def generation(self):
        return self._generation

    @property
    def inuse(self):
        return self._inuse




class LineReader():
    """Read "lines" from a file.

    :param file: A file-like object, opened in _binary_ mode.
    :param delimeters: An iterable of objects which form the end-of-lines.
      Should be convertible to `bytes` or be a string (have an `encode`
      method).
    """
    def __init__(self, file, delimeters = ["\n", "\r", "\r\n"]):
        self._file = file
        self._waiting = []
        self._delimeters = []
        for x in delimeters:
            try:
                self._delimeters.append(bytes(x))
            except:
                self._delimeters.append(x.encode())
        self._delimeters.sort(key = lambda x : -len(x))

    def readline(self):
        """Read the next line, _including_ the end of line delimeter.
        
        :return: The next lines as a `bytes` object, or empty `bytes`
          (` == b""`) otherwise.
        """
        if len(self._waiting) > 0:
            x = self._waiting.pop(0)
            return x
        self._buffer()
        if len(self._waiting) == 0:
            return b""
        return self.readline()

    def pushback(self, line):
        """Inject `line` into the top of the queue."""
        self._waiting.insert(0, line)

    def _buffer(self):
        line = self._file.readline()
        while len(line) > 0:
            part, line = self._split(line)
            if part is None:
                self._waiting.append(line)    
                break
            self._waiting.append(part)

    def _split(self, line):
        for i in range(len(line)):
            for de in self._delimeters:
                if i + len(de) > len(line):
                    continue
                if line[i:i+len(de)] == de:
                    return line[:i+len(de)], line[i+len(de):]
        return None, line

class FormatError(Exception):
    """Generally unexpected structure in the input file."""
    pass

class EOF(Exception):
    """Unexpected end of file."""
    pass

class ObjReader():
    """Parse OBJ objects out of a file.
    
    :param line: The next line of input.
    :param reader: The :class:`LineReader` object to grab data from, if
      necessary.
    """
    def __init__(self, line, reader):
        line = line.decode()
        matcher = ObjReader._obj_pattern.match(line)
        if matcher is None:
            raise FormatError("Line does not start as an object: '{}'".format(line))
        n = int(matcher.group(1))
        m = int(matcher.group(2))
        data = matcher.group(3)

        lines = self._get_lines(reader, data)
        self._obj = OBJ(n, m, lines)

    @property
    def obj(self):
        """The parsed OBJ object"""
        return self._obj

    def _get_lines(self, reader, data):
        lines = []
        if len(data) > 0:
            lines.append(data.encode())
        while True:
            line = reader.readline()
            if len(line) == 0:
                raise EOF()
            if line.strip() == b"endobj":
                break
            if line.strip().endswith(b"endobj"):
                line = line.strip()[:-6]
                lines.append(line)
                break
            if line[:6] == b"endobj":
                # TODO: Extract the rest of line if not just whitespace, and "push back" to line reader!!
                pass
            lines.append(line)
        return lines

    _obj_pattern = _re.compile("(\d+)\s(\d+)\sobj\s*(.*)", flags=_re.DOTALL)


class PDF():
    """Open a (minimal) PDF file, and parse into objects.

    A PDF file is assumed to have the following structure:

    - Each line is delimeted by `\n`, `\r` or `\r\n`
    - The first line is the version string, like `%PDF-1.5`
    - The 2nd line is some magic values, see :meth:`_check_binary`
    - The file ends with `%%EOF`
    - The file mostly consists of OBJ objects:
      - These start with `n m obj` where `n`, `m` are numbers.
      - There might now be a newline; or a space.
      - Then data which we grab verbatim
      - Ends with a line `endobj` or just the line ending `endobj`.
      - See :class:`ObjReader`
    - 

    :param file: A filename, or a file-like object (openned in _binary_ mode).
    """
    def __init__(self, file):
        should_close_file = False
        try:
            file = open(file, "rb")
            should_close_file = True
        except:
            pass
        try:
            file = LineReader(file)
            self._read_version(file)
            self._objects = []
            while True:
                line = file.readline().strip()
                if len(line) == 0:
                    continue
                if line == b"%%EOF":
                    break
                if line[0:1] == b"%":
                    self._check_binary(line)
                    continue
                if line == b"xref":
                    self._read_xref(file)
                    continue
                if line == b"trailer":
                    self._read_trailer(file)
                    continue
                if line == b"startxref":
                    line = file.readline()
                    self._xref_offset = int(line.decode("UTF8").strip())
                    continue
                self._objects.append( ObjReader(line, file).obj )
        finally:
            if should_close_file:
                file.close()

    def _read_version(self, file):
        line = file.readline()
        self._version = line.decode("UTF8").strip()

    @property
    def version(self):
        """Version string of the PDF, like '%PDF-1.3'"""
        return self._version

    def _read_trailer(self, file):
        # Assume starts/ends with << and >>
        line = file.readline()
        if line.strip()[:2] != b"<<":
            raise Exception("Unexpected start of trailer section: '{}'".format(line))
        line = line.strip()[2:]
        self._trailer = []
        if len(line) > 0:
            self._trailer.append(line.decode("UTF8"))
        while True:
            line = file.readline()
            if line.strip() == b">>":
                return
            if len(line) == 0:
                raise Exception("Unexpected end of file")
            self._trailer.append(line.decode("UTF8").strip())

    def _read_xref(self, file):
        # https://blog.idrsolutions.com/2011/05/understanding-the-pdf-file-format-%E2%80%93-pdf-xref-tables-explained/
        parts = file.readline().decode("UTF8").strip().split(" ")
        count = int(parts[1])
        self._xref_range = (int(parts[0]), count)
        self._xrefs = []
        for _ in range(count):
            parts = file.readline().decode("UTF8").strip().split(" ")
            xref = XREF(int(parts[0]), int(parts[1]), parts[2])
            self._xrefs.append(xref)

    def _check_binary(self, line):
        assert line[0:1] == b"%"
        if len(line.strip()) != 5:
            raise Exception("Unknown start of file: '{}'".format(line))
        for x in line.strip()[1:]:
            if x < 128:
                raise Exception("Unknown start of file: '{}'".format(line))

    @property
    def xref_range(self):
        """Returns pair (start, count)"""
        return self._xref_range

    @property
    def xref_offset(self):
        """Position in the file where the xref table starts"""
        return self._xref_offset

    @property
    def xrefs(self):
        return self._xrefs

    @property
    def trailer(self):
        if hasattr(self, "_trailer"):
            return self._trailer
        return []

    @property
    def objects(self):
        """List of :class:`OBJ` objects."""
        return self._objects

    def pretty_print(self):
        out = [self.version + "\n"]
        for obj in self.objects:
            out.append("{} {} obj\n".format(obj.n, obj.m))
            stream = None
            for i, line in enumerate(obj.contents):
                if stream is None:
                    try:
                        s = line.decode()
                    except:
                        s = str(line)
                    out.append("   " + s)
                    if s.strip() == "stream":
                        stream = b""
                else:
                    if line.strip() == b"endstream":
                        out.append("   " + str(stream[:min(50,len(stream))]) + "\n")
                        out.append("   " + line.decode())
                        stream = None
                    else:
                        if len(stream) < 50:
                            stream += line
        out.append("trailer:\n")
        for line in self.trailer:
            out.append("   "+line)
        return "".join(out)
