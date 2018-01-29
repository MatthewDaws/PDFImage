"""
pdf_write.py
~~~~~~~~~~~~

Supports writing (simple) PDF files.
"""

from .pdf import *
import datetime as _datetime
import hashlib as _hashlib

class DocumentEntity():
    """Base class for each typed document member."""

    def object(self):
        """Returns a full :class:`PDFObject` instance, with no id data
        initialised."""
        raise NotImplementedError()


class DocumentCatalog(DocumentEntity):
    """The root document object, giving details about the pages.
    
    :param page_tree_object: Instance of :class:`PageTree` describing the
      (main) page tree.
    """
    def __init__(self, page_tree_object):
        self._page_object = page_tree_object

    def object(self):
        out = PDFSimpleDict()
        out["Type"] = "Catalog"
        out["Pages"] = self._page_object
        return PDFObject(out.to_dict())


class PageTree(DocumentEntity):
    """We only support trees of depth 1, so there is one parent node, and all
    other nodes are actual pages.  When the underlying `object` is generated,
    each page will have its "parent" set to the generated object."""
    def __init__(self):
        self._pages = []

    def add_page(self, page):
        """Add a :class:`Page` object."""
        self._pages.append(page)

    def object(self):
        pages_object = PDFObject()

        out = PDFSimpleDict()
        out["Type"] = "Pages"
        pages = []
        for page in self._pages:
            page.parent = pages_object
            pages.append(page.object())
        out["Kids"] = PDFArray(pages)
        out["Count"] = len(pages)
        pages_object.data = out.to_dict()

        return pages_object


class Page(DocumentEntity):
    """An individual page.  Designed mainly for images.
    
    :param mediabox: A :class:`Rectangle` instance of the bounding box of the
      media.
    :param resources: A :class:`PDFDictionary` of resources; or
      :class:`PDFObjectId` reference.
    :param contents: A :class:`PDFObjectId` of the contents of the page
    """
    def __init__(self, mediabox, resources, contents):
        self._mediabox = mediabox
        self._resources = resources
        self._contents = contents
        self._object = PDFObject()

    @property
    def parent(self):
        """The :class:`PDFObjectId` which is this page's parent.
        Always :class:`PageTree` for us."""
        return self._parent

    @parent.setter
    def parent(self, p):
        self._parent = p

    def object(self):
        out = PDFSimpleDict()
        out["Type"] = "Page"
        out["Parent"] = self._parent
        out["Resources"] = self._resources
        out["MediaBox"] = self._mediabox()
        out["Contents"] = self._contents
        self._object.data = out.to_dict()
        return self._object
        

class InfoObject(DocumentEntity):
    """A PDF Info object.

    :param title: The title of the PDF file.
    """
    def __init__(self, title):
        self._title = title
        self._others = []

    def add_entry(self, name, value):
        """Add an entry to the info object."""
        self._others.append( (name, value) )

    def object(self):
        out = PDFSimpleDict()
        out["Title"] = PDFString(self._title.encode())
        dt = DateTime(_datetime.datetime.now())
        out["CreationDate"] = dt()
        return PDFObject(out.to_dict())


class ColourSpace():
    """The colour spaces we support."""
    def __call__(self):
        raise NotImplementedError()


class ColourSpaceRGB(ColourSpace):
    """PDF DeviceRGB."""
    def __call__(self):
        return PDFName("DeviceRGB")
    

class ColourSpaceGrey(ColourSpace):
    """PDF DeviceRGB."""
    def __call__(self):
        return PDFName("DeviceGray")


class ColourSpaceIndexed(ColourSpace):
    """Indexed or Palette based colour scheme.  We only support RGB palettes,
    of 256 entries.

    :param palette: An iterable of 256 tuples specifying RGB values (between 0
      and 255 inclusive).
    """
    def __init__(self, palette):
        self._palette = [tuple(x) for x in palette]

    def __call__(self):
        ar = [PDFName("Indexed"), PDFName("DeviceRGB"), PDFNumeric(255)]
        flat_palette = []
        for rgb in self._palette:
            for comp in rgb:
                flat_palette.append(comp)
        ar.append(PDFString(flat_palette))
        return PDFArray(ar)


class ImageDictionary(DocumentEntity):
    """Describes an image.

    :param width:
    :param height: Integers describing the image size
    :param colour_space: Instance of :class:`ColourSpace` giving the colour
      space.
    :param bits: Bits per component; typically 1 or 8.
    :param interpolate: Should we specify interpolation?
    """
    def __init__(self, width, height, colour_space, bits, interpolate=True):
        self._size = (width, height)
        self._cs = colour_space
        self._bpc = bits
        self._interpolate = interpolate

    def add_filtered_data(self, filter_name_string, data, parameters=None):
        """Add the actual data, encoded using the given filter name.
        
        :param filter_name_string: String of the filter name used.  May be
          `None` to indicate no filter.
        :param data: Bytes object of the encoded data.
        :param parameters: Optional Python dictionary from strings to integers
          (or string to PDFObject) giving needed parameters for the filter.
        """
        self._filter = filter_name_string
        self._data = data
        self._params = parameters

    def object(self):
        out = PDFSimpleDict()
        out["Subtype"] = "Image"
        out["Width"] = self._size[0]
        out["Height"] = self._size[1]
        out["ColorSpace"] = self._cs()
        out["BitsPerComponent"] = self._bpc
        out["Interpolate"] = PDFBoolean(self._interpolate)
        if self._filter is not None:
            out["Filter"] = self._filter
        out["Length"] = len(self._data)
        if self._params is not None:
            for k, v in self._params.items():
                out[k] = v
        stream = PDFStream(out.to_dict().items(), self._data)
        return PDFObject(stream)


class ImageTransformation():
    """Abstract base class for image transformations."""
    def __call__(self):
        raise NotImplementedError()


class ImageScale(ImageTransformation):
    """Scale an image."""
    def __init__(self, xscale=1.0, yscale=1.0):
        self._x = xscale
        self._y = yscale

    def __call__(self):
        return "{} 0 0 {} 0 0 cm".format(self._x, self._y)


class ImageDrawer(DocumentEntity):
    """The object which transforms and draws the image.  Will be the "contents"
    of a page.
    
    :param transformations: Iterable of :class:`ImageTransformation` objects.
    :param image_name: Name of the image.
    """
    def __init__(self, transformations, image_name):
        self._trans = transformations
        self._image_name = image_name

    def object(self):
        data = [b"q"] + [x().encode() for x in self._trans]
        data.append(bytes(PDFName(self._image_name)) + b" Do")
        data.append(b"Q")
        data = b"\n".join(data)
        obj = PDFStream([(PDFName("Length"), PDFNumeric(len(data)))], data)
        return PDFObject(obj)


class ProcedureSet(DocumentEntity):
    """Although depricated, it is still recommended to include these.
    """
    def __init__(self):
        self._sets = ["PDF", "Text", "ImageB", "ImageC", "ImageI"]

    def object(self):
        out = PDFArray([PDFName(x) for x in self._sets])
        return PDFObject(out)


class CommonDataStructure():
    """Abstract base class for PDF common data structures."""
    def __call__(self):
        """Return a typed PDF object representing this data."""
        raise NotImplementedError()


class Rectangle(CommonDataStructure):
    """A rectangle"""
    def __init__(self, xmin, ymin, xmax, ymax):
        self._min = (xmin, ymin)
        self._max = (xmax, ymax)

    def __call__(self):
        coords = (*self._min, *self._max)
        return PDFArray([PDFNumeric(x) for x in coords])


class DateTime(CommonDataStructure):
    """A PDF datetime string.  Does not currently support time zones.
    
    :param dt: A Pyhton :class:`datetime.datetime` object, or an object with
      a similar interface.
    """
    def __init__(self, dt):
        self._dt = dt

    def __call__(self):
        fields = [("year", "{:04}"), ("month", "{:02}"), ("day", "{:02}"),
                ("hour", "{:02}"), ("minute", "{:02}"), ("second", "{:02}")
                ]
        out = b"D:"
        for field, fmt in fields:
            if hasattr(self._dt, field):
                x = int(getattr(self._dt, field))
                out += fmt.format(x).encode()
            else:
                break
        return PDFString(out)


class PDFWriter():
    """Write PDF files.  Usage:
      - Call :meth:`add_page` repeatedly to add pages
      - Call :meth:`add_pdf_object` to add any extra objects

    Then convert to `bytes` to get a fully-formed PDF file!    
    """
    def __init__(self):
        self._pages = []
        self._objs = []
        self._info = InfoObject("None")

    def add_page(self, page):
        """Add a :class:`Page` object."""
        self._pages.append(page)

    def add_pdf_object(self, obj):
        """Add a :class:`PDFObject` object, or other object to be wrapped
        as a full object.

        :param obj: :class:`PDFObject` instance, or another class to be
          make into a :class:`PDFObject` instance.

        :return: The object, made into a :class:`PDFObject` instance if
          necessary.
        """
        if not isinstance(obj, PDFObject):
            obj = PDFObject(obj)
        self._objs.append(obj)
        return obj

    def set_info_object(self, info):
        """Set the :class:`InfoObject` instance."""
        self._info = info

    def _to_full_objects(self):
        page_tree = PageTree()
        for p in self._pages:
            page_tree.add_page(p)
        page_tree_obj = page_tree.object()
        objs = [DocumentCatalog(page_tree_obj).object(), page_tree_obj]
        self._root_object = objs[0]
        for p in self._pages:
            objs.append(p.object())
        objs.extend(self._objs)
        objs.append(self._info.object())
        self._info_object = objs[-1]

        for num, obj in enumerate(objs):
            obj.number = num + 1
            obj.generation = 0
        return objs

    def _obj_marker(self, obj):
        return "{} {} obj".format(obj.number, obj.generation).encode()

    def _make_trailer(self, object_count, hash_data):
        out = b"trailer\n"
        trailer = PDFSimpleDict()
        trailer["Size"] = object_count
        trailer["Root"] = self._root_object
        trailer["Info"] = self._info_object
        h = _hashlib.md5(hash_data).digest()
        trailer["ID"] = PDFArray([PDFString(h), PDFString(h)])
        out += bytes(trailer.to_dict()) + b"\n"
        return out

    def __bytes__(self):
        out = b"%PDF-1.4\n"

        offsets = dict()
        all_objects = self._to_full_objects()
        for obj in all_objects:
            offsets[obj.number] = len(out)
            out += self._obj_marker(obj) + b"\n"
            out += bytes(obj.data) + b"\n"
            out += b"endobj\n"
        offsets = list(offsets.items())
        offsets.sort(key = lambda pr : pr[0])
        offsets = [v for k, v in offsets]

        start_xref = len(out)
        out += "xref\n0 {}\n".format(len(offsets) + 1).encode()
        out += b"0000000000 65535 f \n"
        for off in offsets:
            out += "{:010} 00000 n \n".format(off).encode()
        
        out += self._make_trailer(len(offsets) + 1, out)

        out += "startxref\n{}\n%%EOF\n".format(start_xref).encode()
        return out
