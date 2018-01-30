"""
pdf_image.py
~~~~~~~~~~~~

Produce PDF pages based on images.
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
    :param dpi: Scaling; defaults to 1 so images appear at one-to-one
      size, which is typically too large.
    """
    def __init__(self, image, proc_set_object, dpi=1):
        self._image = self._adjust_bw_case(image)
        self._proc_set = proc_set_object
        self._dpi = dpi

    @property
    def dpi(self):
        return self._dpi

    @dpi.setter
    def dpi(self, d):
        self._dpi = d

    def _make_page(self, contents_object, xobjects, proc_set):
        mediabox = pdf_write.Rectangle(xmin=0, xmax=self._image.width / self._dpi,
                ymin=0, ymax=self._image.height / self._dpi)
        resources = pdf.PDFSimpleDict()
        resources["ProcSet"] = proc_set
        xob = pdf.PDFSimpleDict()
        for count, xobject in enumerate(xobjects):
            xob["Im{}".format(count)] = xobject
        resources["XObject"] = xob.to_dict()
        return pdf_write.Page(mediabox, resources.to_dict(), contents_object)

    def _make_contents_object(self):
        transforms = [pdf_write.ImageScale(xscale=self._image.width / self._dpi,
                yscale=self._image.height / self._dpi)]
        return pdf_write.ImageDrawer(transforms, "Im0").object()

    def _adjust_bw_case(self, image):
        if image.mode != "P":
            return image
        mode, flat_palette = image.palette.getdata()
        if mode != "RGB":
            raise ValueError("Expected RGB palette")
        if len(flat_palette) == 6:
            image = image.convert("1")
        return image

    def _make_one_xobject_dict(self, image):
        if image.mode == "1":
            colour_space = pdf_write.ColourSpaceGrey()
            bpp = 1
        elif image.mode == "L":
            colour_space = pdf_write.ColourSpaceGrey()
            bpp = 8
        elif image.mode == "RGB":
            colour_space = pdf_write.ColourSpaceRGB()
            bpp = 8
        elif image.mode == "P":
            mode, flat_palette = image.palette.getdata()
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
            raise ValueError("Image mode {} not supported".format(image.mode))
        imagedict = pdf_write.ImageDictionary(image.width, image.height, colour_space, bpp)
        imagedict.add_filtered_data(*self._get_filtered_data(image))
        return imagedict

    def _make_xobjects(self):
        image = self._make_one_xobject_dict(self._image)
        for k, v in self._get_extra_image_dictionary_entries().items():
            image.add_dictionary_entry(k, v)
        return [image.object()]

    def _get_filtered_data(self, image):
        """Abstract method to compress the image data.

        :param image: The image to compress.

        :return: A triple `(filter_name_string, data, parameters)` where
          `parameters` may be `None`.
        """
        raise NotImplementedError()

    def _get_extra_image_dictionary_entries(self):
        """Optionally override to add extra entries to the dictionary."""
        return dict()

    def __call__(self):
        objects = []
        if self._proc_set is None:
            proc_set = pdf_write.ProcedureSet().object()
            objects.append(proc_set)
        else:
            proc_set = self._proc_set
        contents = self._make_contents_object()
        objects.append(contents)
        xobjects = self._make_xobjects()
        objects.extend(xobjects)
        page = self._make_page(contents, xobjects, proc_set)
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


class PDFMultipleImage(PDFImage):
    """Construct a single page by combining multiple images.  Typical use
    case is to combine a black+white image (highly compressed) with a colour
    image showing illustrations and photos, etc.

    :param base_image: The :class:`PIL.Image` object to encode.
    :param proc_set_object: A :class:`PDFObject` pointing to the standard
      "Proc Set", or `None` to generate a new one.
    :param base_scale: Scaling; defaults to 1 so images appear at one-to-one
      size, which is typically too large.
    """
    def __init__(self, base_image, proc_set_object, base_scale=1):
        super().__init__(base_image, proc_set_object, base_scale)
        self._other_images = []
    
    def add_top_image(self, image, position, size, mask=None):
        """Add a new image on top of the current image stack.  The MediaBox
        of the page is defined by the base image, and the dpi/scaling.

        :param image: The :class:`PIL.Image`
        :param position: The _lower left_ corner of the image, in the
          coordinate space defined by the page MediaBox; as a pair `(x, y)`
        :param size: The size `(width, height)` of the image, in the
          coordinate space defined by the page MediaBox
        :param mask: `None` for no masking, or otherwise a tuple
          `(min, max)` for a black/white image, or `(min_1, max_1, ...,
          min_3, max_3)` for a RGB image.  This indicates the range of pixel
          values which will not be drawn.  For example, `(255, 255)` will not
          draw white, in a grey-scale image, and `(1, 1)` will do the same in
          a 1-bit black and white image.
        """
        image = self._adjust_bw_case(image)
        self._other_images.append((image, position, size, mask))

    def _make_contents_object(self):
        transforms = [pdf_write.ImageScale(xscale=self._image.width / self._dpi,
                yscale=self._image.height / self._dpi)]
        stream = pdf_write.ImageDrawer(transforms, "Im0").make_stream()

        for count, (image, pos, size, mask) in enumerate(self._other_images):
            transforms = [pdf_write.ImageTranslation(*pos),
                    pdf_write.ImageScale(*size)]
            stream += b"\n"
            stream += pdf_write.ImageDrawer(transforms, "Im{}".format(count+1)).make_stream()

        obj = pdf.PDFStream([(pdf.PDFName("Length"), pdf.PDFNumeric(len(stream)))], stream)
        return pdf.PDFObject(obj)

    def _make_xobjects(self):
        xobjs = [self._make_one_xobject_dict(self._image).object()]
        for image, pos, size, mask in self._other_images:
            image = self._make_one_xobject_dict(image)
            if mask is not None:
                image.add_dictionary_entry("Mask", pdf.PDFArray([pdf.PDFNumeric(x) for x in mask]))
            xobjs.append(image.object())
        return xobjs


class UncompressedImage(PDFImage):
    """Mainly for testing; no compression."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self, image):
        data = image.tobytes()
        return None, data, None


class FlateImage(PDFImage):
    """Use "Flate" compression; same as PNG without any "predictor"."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self, image):
        data = image.tobytes()
        return "FlateDecode", _zlib.compress(data, 9), None


class FlateMultiImage(PDFMultipleImage):
    """Flate compression of multiple images."""
    def __init__(self, base_image, proc_set_object, base_scale=1):
        super().__init__(base_image, proc_set_object, base_scale)

    def _get_filtered_data(self, image):
        data = image.tobytes()
        return "FlateDecode", _zlib.compress(data, 9), None


class PNGImage(PDFImage):
    """Use PNG compression."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self, image):
        params = {"Predictor": 15, "Columns": image.width}
        if image.mode == "RGB":
            params["Colors"] = 3
        elif image.mode == "L":
            params["Colors"] = 1
        else:
            raise ValueError("Mode {} not supported for PNG".format(image.mode))

        data = _zlib.compress(_png.png_heuristic_predictor(image), 9)

        return "FlateDecode", data, params


class TIFFImage(PDFImage):
    """Use TIFF compression.  Usually PNG is still optimal."""
    def __init__(self, image, proc_set_object=None):
        super().__init__(image, proc_set_object)

    def _get_filtered_data(self, image):
        params = {"Predictor": 2, "Columns": image.width}
        if image.mode == "RGB":
            params["Colors"] = 3
        elif image.mode == "L":
            params["Colors"] = 1
        else:
            raise ValueError("Mode {} not supported for PNG".format(image.mode))

        data = _zlib.compress(_png.tiff_predictor(image), 9)

        return "FlateDecode", data, params
