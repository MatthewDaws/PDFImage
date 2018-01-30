"""
jb2.py
~~~~~~

"""

import os, sys, subprocess, struct, zipfile
from . import pdf_image
from . import pdf_write
from . import pdf

_default_jbig2_exe = os.path.join(os.path.abspath(".."), "agl-jbig2enc", "jbig2.exe")

class JBIG2Compressor():
    """Use an external compressor to compress using the JBIG2 standard.

    :param jbig2_exe_path: The path to the "jbig2.exe" excutable.  Or `None` to
      use the default.
    """
    def __init__(self, jbig2_exe_path=None):
        if jbig2_exe_path is None:
            jbig2_exe_path = _default_jbig2_exe
        self._jbig2_exe_path = jbig2_exe_path

    def call(self, args):
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def encode(self, files):
        """Will generate `output.sym` and `output.0000`, `output.0001` etc.
        in the current directory."""
        result = self.call([self._jbig2_exe_path, "-s", "-p", "-2", "-v"] + list(files))
        assert result.returncode == 0
        return result


class ImageFacade():
    pass


class JBIG2Image(pdf_image.PDFImage):
    """Assemble a single jbig2 output file into a PDF file."""
    def __init__(self, jbig2globals_object, file, proc_set_object):
        self._file = file
        super().__init__(self._image(), proc_set_object)
        self._jbig2globals_object = jbig2globals_object

    def _read_file(self):
        if not hasattr(self, "_file_cache"):
            if isinstance(self._file, str):
                with open(self._file, "rb") as f:
                    self._file_cache = f.read()
            else:
                self._file_cache = self._file.read()
        return self._file_cache

    def _image(self):
        data = self._read_file()
        (width, height, xres, yres) = struct.unpack('>IIII', data[11:27])
        image = ImageFacade()
        image.width = width
        image.height = height
        image.mode = "1"
        return image

    def _get_filtered_data(self):
        params = {"JBIG2Globals" : self._jbig2globals_object}
        data = self._read_file()
        return "JBIG2Decode", data, params


class JBIG2Output():
    """Container for the output of converting JBIG2 output to PDF format."""
    def __init__(self, pages, objects):
        self._pages = pages
        self._objects = objects

    @property
    def pages(self):
        """Iterable of page objects."""
        return self._pages

    @property
    def objects(self):
        """An iterable of objects to add to the PDF file."""
        return self._objects

    def add_to_pdf_writer(self, pdf_writer):
        """Convenience method to add directly to a :class:`pdf_write.PDFWriter`
        instance."""
        for page in self.pages:
            pdf_writer.add_page(page)
        for obj in self.objects:
            pdf_writer.add_pdf_object(obj)


class JBIG2Images():
    """Assemble the compressed JBIG2 files into a PDF document.
    
    :param zipfilename: The ZIP file to look at for data.
    """
    def __init__(self, zipfilename):
        self._objects = []
        zf = zipfile.ZipFile(zipfilename, "r")
        try:
            self._add_globals(zf)
            self._proc_set_object = pdf_write.ProcedureSet().object()
            self._result = self._compile_pages(zf)
            self._result.objects.append(self._jb2_globals)
            self._result.objects.append(self._proc_set_object)
        finally:
            zf.close()

    @property
    def parts(self):
        """The output"""
        return self._result

    def _compile_pages(self, zf):
        page_number = 0
        pages = []
        objects = []
        while True:
            ending = ".{:04}".format(page_number)
            choices = [x for x in zf.filelist if x.filename.endswith(ending)]
            if len(choices) == 0:
                break
            with zf.open(choices[0]) as file:
                parts = JBIG2Image(self._jb2_globals, file, self._proc_set_object)()
            pages.append(parts.page)
            objects.extend(parts.objects)
            page_number += 1
        return JBIG2Output(pages, objects)

    def _add_globals(self, zf):
        for zfile in zf.filelist:
            if zfile.filename.endswith(".sym"):
                with zf.open(zfile) as f:
                    data = f.read()
                    stream = pdf.PDFStream([(pdf.PDFName("Length"), pdf.PDFNumeric(len(data)))], data)
                    self._jb2_globals = pdf.PDFObject(stream)
                return
        raise ValueError("Could not find a symbol file.")

