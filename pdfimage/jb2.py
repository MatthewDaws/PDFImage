"""
jb2.py
~~~~~~

Use JBIG2, and an external compressor, for black and white images.
"""

import os, sys, subprocess, struct, zipfile, random
from . import pdf_image
from . import pdf_write
from . import pdf

_default_jbig2_exe = os.path.join(os.path.abspath(".."), "agl-jbig2enc", "jbig2.exe")

class JBIG2Compressor():
    """Use an external compressor to compress using the JBIG2 standard.

    :param jbig2_exe_path: The path to the "jbig2.exe" excutable.  Or `None` to
      use the default.
    :param oversample: Can be 1, 2 or 4.  Upsample by this amount before making b/w.
    """
    def __init__(self, jbig2_exe_path=None, oversample=2):
        if jbig2_exe_path is None:
            jbig2_exe_path = _default_jbig2_exe
        self._jbig2_exe_path = jbig2_exe_path
        self._upsample = oversample

    def call(self, args):
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def encode(self, files):
        """Will generate `output.sym` and `output.0000`, `output.0001` etc.
        in the current directory."""
        args = [self._jbig2_exe_path, "-s", "-p", "-v"]
        if self._upsample == 1:
            pass
        elif self._upsample == 2:
            args += ["-2"]
        elif self._upsample == 4:
            args += ["-4"]
        else:
            raise ValueError("{} is not supported for over-sampling".format(self._upsample))
        result = self.call(args + list(files))
        assert result.returncode == 0
        return result


class JBIG2CompressorToZip():
    """A higher-level version of :class:`JBIG2Compressor` which takes care of
    temporary output directories, and zipping the result.

    :param output_filename: The filename to write the ZIP file to.
    :param jbig2_exe_path: The path to the "jbig2.exe" excutable.  Or `None` to
      use the default.
    :param input_directory: The directory to find input files in, or `None` for
      the current directory.
    :param temporary_directory: The directory to write temporary files to, or
      `None` to auto-generated one (and delete at the end).
    :param oversample: Can be 1, 2 or 4.  Upsample by this amount before making b/w.
    :param split: Should we ask `jbig2.exe` to attempt to split out PNG files of
      graphics?  If so, `oversample==1` seems to be the only setting which works!
    """
    def __init__(self, output_filename, jbig2_exe_path=None, input_directory=None,
            temporary_directory=None, oversample=2, split=False):
        if jbig2_exe_path is None:
            jbig2_exe_path = _default_jbig2_exe
        self._jbig2_exe_path = os.path.abspath(jbig2_exe_path)

        self._in_dir = input_directory
        self._temp_dir = temporary_directory
        self._out_file = os.path.abspath(output_filename)
        self._upsample = oversample
        self._split = split

    def _random_dir_name(self):
        return "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(8))

    def _call(self, args):
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _cleanup(self):
        if self._old_directory is not None:
            os.chdir(self._old_directory)
            return
        files = list(os.listdir())
        for f in files:
            try:
                os.remove(f)
            except:
                pass
        os.chdir("..")
        try:
            os.rmdir(self._temp_dir)
        except:
            pass

    def _make_temp_dir(self):
        if self._temp_dir is not None:
            self._old_directory = os.path.abspath(os.curdir)
            os.chdir(self._temp_dir)
        else:
            self._old_directory = None
            self._temp_dir = self._random_dir_name()
            os.mkdir(self._temp_dir)
            os.chdir(self._temp_dir)

    def _write_zip_file(self):
        zf = zipfile.ZipFile(self._out_file, "w")
        try:
            files = list(os.listdir())
            for f in files:
                with open(f, "rb") as file:
                    data = file.read()
                with zf.open(f, "w") as file:
                    file.write(data)
        finally:
            zf.close()
            self._cleanup()

    def encode(self, files):
        """Encode the files, all to be found in the input directory."""
        if self._in_dir is not None:
            files = [os.path.join(self._in_dir, x) for x in files]
        files = [os.path.abspath(f) for f in files]

        self._make_temp_dir()
        args = [self._jbig2_exe_path, "-s", "-p", "-v"]
        if self._split:
            args.append("-S")
        if self._upsample == 1:
            pass
        elif self._upsample == 2:
            args += ["-2"]
        elif self._upsample == 4:
            args += ["-4"]
        else:
            raise ValueError("{} is not supported for over-sampling".format(self._upsample))
        result = self._call(args + list(files))
        if not result.returncode == 0:
            self._cleanup()
            raise Exception("Failed to compress files", result)
        
        self._write_zip_file()


class ImageFacade():
    pass


class JBIG2Image(pdf_image.PDFImage):
    """Assemble a single jbig2 output file into a PDF file."""
    def __init__(self, jbig2globals_object, file, proc_set_object, dpi=1):
        self._file = file
        super().__init__(self._image(), proc_set_object, dpi)
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

    def _get_filtered_data(self, image):
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
    def __init__(self, zipfilename, dpi=1):
        self._objects = []
        self._dpi = dpi
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
                parts = JBIG2Image(self._jb2_globals, file, self._proc_set_object, self._dpi)()
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

