"""
pdf_image.py
~~~~~~~~~~~~

"""

from . import pdf_write
from . import pdf
import zlib as _zlib
from . import png as _png

class PDFImage():
    """Constructs single pages of PDF files using images.  Base class which is
    extended to implement specific compression algorithms.

    To describe an image, we need to specify:
      - The "page" which needs to be a :class:`pdf_write.Page` instance
      - The actual image data, which this class generates, with the help of an
        :class:`pdf_write.ImageDictionary` instance
      - The instructions, in PDF syntax, for drawing the image.  We use
        :class:`pdf_write.ImageDrawer`
      - (For historial reasons) the "ProcSet" used.  This can be shared.

    To use, just invoke as a callable.

    :param image: The :class:`PIL.Image` object to encode.
    :param proc_set_object: A :class:`PDFObject` pointing to the standard
      "Proc Set", or `None` to generate a new one.
    """
    def __init__(self, image, proc_set_object):
        self._image = image
        self._proc_set = proc_set_object

    def _make_page(self, contents_object, xobject, proc_set):
        mediabox = pdf_write.Rectangle(xmin=0, xmax=self._image.width,
                ymin=0, ymax=self._image.height)
        resources = pdf.PDFSimpleDict()
        resources["ProcSet"] = proc_set
        xob = pdf.PDFSimpleDict()
        xob["Im0"] = xobject
        resources["XObject"] = xob.to_dict()
        return pdf_write.Page(mediabox, resources.to_dict(), contents_object)

    def _make_contents_object(self):
        transforms = [pdf_write.ImageScale(xscale=self._image.width, yscale=self._image.height)]
        return pdf_write.ImageDrawer(transforms, "Im0").object()

    def _adjust_bw_case(self):
        if self._image.mode != "P":
            return
        mode, flat_palette = self._image.palette.getdata()
        if mode != "RGB":
            raise ValueError("Expected RGB palette")
        if len(flat_palette) == 6:
            self._image = self._image.convert("1")

    def _make_xobject(self):
        self._adjust_bw_case()

        if self._image.mode == "1":
            colour_space = pdf_write.ColourSpaceGrey()
            bpp = 1
        elif self._image.mode == "L":
            colour_space = pdf_write.ColourSpaceGrey()
            bpp = 8
        elif self._image.mode == "RGB":
            colour_space = pdf_write.ColourSpaceRGB()
            bpp = 8
        elif self._image.mode == "P":
            mode, flat_palette = self._image.palette.getdata()
            if mode != "RGB":
                raise ValueError("Expected RGB palette")
            if len(flat_palette) != 3 * 256:
                raise ValueError("Expected 256 colours!")
            palette = []
            i = 0
            while i < len(flat_palette):
                rgb = flat_palette[i], flat_palette[i+1], flat_palette[i+2]
                palette.append(rgb)
                i += 3
            colour_space = pdf_write.ColourSpaceIndexed(palette)
            bpp = 8
        else:
            raise ValueError("Image mode {} not supported".format(self._image.mode))
        image = pdf_write.ImageDictionary(self._image.width, self._image.height,
            colour_space, bpp)
        image.add_filtered_data(*self._get_filtered_data())
        return image.object()

    def _get_filtered_data(self):
        """Absract method.

        :return: A triple `(filter_name_string, data, parameters)` where
          `parameters` may be `None`.
        """
        raise NotImplementedError()

    def __call__(self):
        objects = []
        if self._proc_set is None:
            proc_set = pdf_write.ProcedureSet().object()
            objects.append(proc_set)
        else:
            proc_set = self._proc_set
        contents = self._make_contents_object()
        objects.append(contents)
        xobject = self._make_xobject()
        objects.append(xobject)
        page = self._make_page(contents, xobject, proc_set)
        return PDFImageParts(page, objects)


class PDFImageParts():
    """Container for the output of encoding an image."""
    def __init__(self, page, objects):
        self._page = page
        self._objects = objects

    @property
    def page(self):
        """The page object."""
        return self._page

    @property
    def objects(self):
        """An iterable of objects to add to the PDF file."""
        return self._objects
    
    def add_to_pdf_writer(self, pdf_writer):
        """Convenience method to add directly to a :class:`pdf_write.PDFWriter`
        instance."""
        pdf_writer.add_page(self.page)
        for obj in self.objects:
            pdf_writer.add_pdf_object(obj)


class UncompressedImage(PDFImage):
    """Mainly for testing; no compression."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self):
        data = self._image.tobytes()
        return None, data, None


class FlateImage(PDFImage):
    """Use "Flate" compression; same as PNG without any "predictor"."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self):
        data = self._image.tobytes()
        return "FlateDecode", _zlib.compress(data, 9), None


class PNGImage(PDFImage):
    """Use PNG compression."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self):
        params = {"Predictor": 15, "Columns": self._image.width}
        if self._image.mode == "RGB":
            params["Colors"] = 3
        elif self._image.mode == "L":
            params["Colors"] = 1
        else:
            raise ValueError("Mode {} not supported for PNG".format(self._image.mode))

        data = _zlib.compress(_png.png_heuristic_predictor(self._image), 9)

        return "FlateDecode", data, params


class TIFFImage(PDFImage):
    """Use TIFF compression.  Usually PNG is still optimal."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self):
        params = {"Predictor": 2, "Columns": self._image.width}
        if self._image.mode == "RGB":
            params["Colors"] = 3
        elif self._image.mode == "L":
            params["Colors"] = 1
        else:
            raise ValueError("Mode {} not supported for PNG".format(self._image.mode))

        data = _zlib.compress(_png.tiff_predictor(self._image), 9)

        return "FlateDecode", data, params
