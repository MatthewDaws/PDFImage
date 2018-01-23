"""
image.py
~~~~~~~~

Simple image manipulation, built on top of `PIL`.  Mainly to help with
"stitching" images together.
"""

import numpy as _np

class ImageRow():
    """Stores a single row of a data, in an abstract format.

    """
    def __init__(self, width, data):
        self._width = width
        self._data = _np.asarray(data)

    @property
    def width(self):
        """The width of the row."""
        return self._width

    @property
    def bytes(self):
        """Array of bytes which form the row"""
        return self._data

    def l2_error_to(self, other_row):
        """Return the sum of squared error to the `other_row`."""
        if self._width != other_row._width:
            raise ValueError("Rows not of same size")
        if self._data.shape != other_row._data.shape:
            raise ValueError("Rows not of same pixel depth")
        return _np.sum((self.bytes - other_row.bytes)**2)


class Image():
    """Wraps a `PIL.Image` and allows comparing rows.

    :param image: The `PIL.Image` to wrap.
    """
    def __init__(self, image):
        self._image = image

    @property
    def image(self):
        """The `PIL.Image` object"""
        return self._image

    def to_array(self):
        """Convert the image data to a numpy array of shape `(x,y,b)` where
        the image is of width `x`, height `y` and each pixel uses `b` bytes.
        """
        if not hasattr(self, "_array_cache"):
            out = _np.asarray(self._image.getdata())
            if len(out.shape) == 1:
                out = out[:,None]
            b = out.shape[-1]
            out = out.reshape((self._image.height, self._image.width, b)).astype(_np.int64)
            self._array_cache = out.transpose((1,0,2))
        return self._array_cache

    def row(self, row):
        """Obtain a :class:`ImageRow` instance representing this row of the
        image."""
        data = self.to_array()[:,row,:]
        return ImageRow(self._image.width, data)

    def find_maximum_solid_rectangle(self, x, y, tolerance=0):
        """Find the largest rectangle with the same colour as pixel `(x,y)`.
        Uses a simple greedy algorithm, so won't deal with complicated shapes.

        :param x:
        :param y: Location to start at
        :param tolerance: Max squared error per pixel, defaults to 0, so
          requiring an exact match.

        :return: `(xmin, ymin, xmax, ymax)` inclusive.
        """
        data = self.to_array()
        pixel = data[x, y, :]
        def mean_sqdiff(xmin, ymin, xmax, ymax):
            return _np.mean((data[xmin:xmax+1, ymin:ymax+1, :] - pixel)**2)
        
        x1, x2, y1, y2 = x, x, y, y
        while x1 >= 0 and mean_sqdiff(x1, y1, x2, y2) <= tolerance:
            x1 -= 1
        x1 += 1
        while x2 < self._image.size[0] and mean_sqdiff(x1, y1, x2, y2) <= tolerance:
            x2 += 1
        x2 -= 1
        while y1 >= 0 and mean_sqdiff(x1, y1, x2, y2) <= tolerance:
            y1 -= 1
        y1 += 1
        while y2 < self._image.size[1] and mean_sqdiff(x1, y1, x2, y2) <= tolerance:
            y2 += 1
        y2 -= 1
    
        return x1, y1, x2, y2


def find_vertical_overlap(one, two, minimum_overlap=5, maximum_difference=100):
    """Assumes that image `two` can be pasted over the bottom of `one` to form
    a consistent image.

    :param one: Top image
    :param two: Bottom image
    :param minimum_overlap: The minimum number of rows we want to overlap

    :return: The row of `one` to paste `two` against.

    :raises: `Exception` if no overlap detected.
    """
    try:
        a = one.to_array()
    except AttributeError:
        one = Image(one)
        a = one.to_array()
    try:
        b = two.to_array()
    except AttributeError:
        two = Image(two)
        b = two.to_array()
    if a.shape[0] != b.shape[0]:
        raise ValueError("Images not the same width")
    if a.shape[2] != b.shape[2]:
        raise ValueError("Images not of the same pixel depth")
    
    avg_diffs = []
    for y in range(one.image.height - minimum_overlap):
        yr = min(one.image.height - y, two.image.height)
        diff = _np.sum((a[:,y:y+yr,:] - b[:,0:yr,:])**2)
        avg_diffs.append(_np.sqrt(diff / yr))
    avg_diffs = _np.asarray(avg_diffs)

    mask = avg_diffs == 0
    if _np.any(mask):
        return _np.min(_np.where(mask))

    if _np.min(avg_diffs) > maximum_difference:
        raise Exception("No approximate match")
    return _np.argmin(avg_diffs)


class SplitByRows():
    """Split an image by finding rows of a fixed type.

    :param image: The :class:`PIL.Image` or :class:`Image` to split
    :param row: The :class:`ImageRow`, one or more on top of each other signals
      a split.
    """
    def __init__(self, image, row):
        try:
            self._image = Image(image.image)
        except AttributeError:
            self._image = Image(image)
        self._row = row

    def to_parts(self):
        """Iterable of tuples `(y1, y2)` where rows `y` with `y1 <= y <= y2`
        being the part of the image to keep."""
        rows_equal_row = [
            self._row.l2_error_to(self._image.row(y)) == 0
            for y in range(self._image.image.height) ]
        return self._find_false_segments(rows_equal_row)

    def to_sub_images(self):
        """Iterable of images, cropped according to :meth:`to_parts`."""
        width = self._image.image.width
        for y1, y2 in self.to_parts():
            yield self._image.image.crop((0, y1, width, y2+1))

    def _find_false_segments(self, segs):
        out = []
        start = 0
        while True:
            while start < len(segs) and segs[start]:
                start += 1
            if start >= len(segs):
                break
            end = start + 1
            while end < len(segs) and not segs[end]:
                end += 1
            out.append((start, end-1))
            start = end + 1
            if start >= len(segs):
                break
        return out