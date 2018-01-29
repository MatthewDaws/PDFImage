"""
png.py
~~~~~~

Load and save PNG files in PDF.
"""

import PIL.Image
import zlib, enum, array
import numpy as np

class PNGPredictor(enum.Enum):
    """The different PNG "predictors" or "filters".  See for example:
      - https://en.wikipedia.org/wiki/Portable_Network_Graphics#Filtering
      - https://www.w3.org/TR/PNG-Filters.html
    """
    none = 0
    sub = 1
    up = 2
    average = 3
    paeth = 4
    heuristic = 1000


class PNG():
    """Encode image files using different PNG "predictors".

    :param image: A :class:`PIL.Image` object
    """
    def __init__(self, image):
        self.width = image.width
        self.height = image.height
        self.bpp = self._bpp(image)
        self.bytes = array.array("B", image.tobytes())
    
    def _bpp(self, image):
        if image.mode == "RGB":
            return 3
        elif image.mode == "1" or image.mode == "L":
            return 1
        else:
            raise ValueError("Unsupported image mode")

    def png_sub(self, row):
        """Encode the row using the sub method."""
        out = array.array("B")
        if self.bpp == 1:
            past = 0
            for i in range(self.width):
                pixel, past = row[i] - past, row[i]
                if pixel < 0:
                    pixel += 256
                out.append(pixel)
        elif self.bpp == 3:
            index = 0
            past = [0, 0, 0]
            for _ in range(self.width):
                for i in range(3):
                    pixel = row[index + i]
                    pixel, past[i] = pixel - past[i], pixel
                    if pixel < 0:
                        pixel += 256
                    out.append(pixel)
                index += 3
        else:
            raise ValueError()
        return out

    def png_up(self, row, rowup):
        """Encode the row using the up method."""
        out = array.array("B")
        for x, y in zip(row, rowup):
            d = x - y
            if d < 0:
                d += 256
            out.append(d)
        return out

    def png_avg(self, row, rowup):
        """Encode the row using the average method."""
        out = array.array("B")
        for i, (x, y) in enumerate(zip(row, rowup)):
            if i < self.bpp:
                old = 0
            else:
                old = row[i - self.bpp]
            pred = x - (old + y) // 2
            if pred < 0:
                pred += 256
            out.append(pred)
        return out

    def png_paeth(self, row, rowup):
        """Encode the row using the "paeth" method."""
        out = array.array("B")
        for i in range(len(row)):
            if i < self.bpp:
                a = 0
                c = 0
            else:
                a = row[i - self.bpp]
                c = rowup[i - self.bpp]
            b = rowup[i]
            diff = row[i] - self.paeth(a, b, c)
            if diff < 0:
                diff += 256
            out.append(diff)
        return out

    @staticmethod
    def paeth(a, b, c):
        """Implements the "paeth" transform"""
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    def _row_up(self, row_number, w):
        if row_number == 0:
            return array.array("B", [0]) * w
        return self.bytes[(row_number - 1) * w : row_number * w]

    def heuristic(self, row, rowup):
        raise NotImplementedError("Use `PNGFast`")

    def png_predict(self, row_number, predict_type):
        """Encode a row of the image using a predictor.
        
        :param row_number: Which row to encode
        :param predict_type: Which :class:`PNGPredictor` to use.

        :return: Encodes row of bytes, as an `array`.
        """
        w = self.width * self.bpp
        row = self.bytes[row_number * w : (row_number + 1) * w]
        
        if predict_type == PNGPredictor.none:
            return row
        if predict_type == PNGPredictor.sub:
            return self.png_sub(row)
        if predict_type == PNGPredictor.up:
            return self.png_up(row, self._row_up(row_number, w))
        if predict_type == PNGPredictor.average:
            return self.png_avg(row, self._row_up(row_number, w))
        if predict_type == PNGPredictor.paeth:
            return self.png_paeth(row, self._row_up(row_number, w))
        if predict_type == PNGPredictor.heuristic:
            return self.heuristic(row, self._row_up(row_number, w))
        raise ValueError()


class PNGFast(PNG):
    """Subclass of :class:`PNG` which is `numpy` accelerated, and implements
    the "heuristic" method.

    :param image: A :class:`PIL.Image` object
    """
    def __init__(self, image):
        super().__init__(image)

    def signed_filter(self, row, rowup):
        """Returns the resulting of the "filtering"/"predicting" step for
        "none", "sub", "up", "average", "paeth" but as signed numpy arrays.
        """
        out = []
        data = array.array("B", [0] * self.bpp)
        data.extend(row)
        rowoffset = np.asarray(data, dtype=np.int)[:-self.bpp]
        data = array.array("B", [0] * self.bpp)
        data.extend(rowup)
        rowupoffset = np.asarray(data, dtype=np.int)[:-self.bpp]
        row = np.asarray(row, dtype=np.int)
        rowup = np.asarray(rowup, dtype=np.int)
        out.append(row)
        out.append(row - rowoffset)
        out.append(row - rowup)
        average = (rowoffset + rowup) // 2
        out.append(row - average)
        out.append(row - self.paeth_parallel(rowoffset, rowup, rowupoffset))
        return out

    def heuristic(self, row, rowup):
        signed = self.signed_filter(row, rowup)
        score = [np.sum(np.abs(x)) for x in signed]
        index = score.index(min(score))
        return index, signed[index].astype(np.uint8)

    def png_sub(self, row):
        data = array.array("B", [0] * self.bpp)
        data.extend(row)
        row = np.asarray(data)
        diffs = row[self.bpp:] - row[:-self.bpp]
        return diffs

    def png_up(self, row, rowup):
        diffs = np.asarray(row) - np.asarray(rowup)
        return diffs

    def png_avg(self, row, rowup):
        row = np.asarray(row)
        old = np.empty_like(row)
        for i in range(self.bpp):
            old[i] = 0
        old[self.bpp:] = row[:-self.bpp]
        diffs = row - (old.astype(np.int) + np.asarray(rowup)) // 2
        diffs[diffs < 0] += 256
        return diffs

    def png_paeth(self, row, rowup):
        data = array.array("B", [0] * self.bpp)
        data.extend(row)
        rowoffset = np.asarray(data, dtype=np.int)[:-self.bpp]
        data = array.array("B", [0] * self.bpp)
        data.extend(rowup)
        rowupoffset = np.asarray(data, dtype=np.int)[:-self.bpp]
        p = self.paeth_parallel(rowoffset, rowup, rowupoffset).astype(np.uint8)
        return np.asarray(row) - p

    @staticmethod
    def paeth_parallel(a, b, c):
        a = np.asarray(a, dtype=np.int)
        b = np.asarray(b, dtype=np.int)
        c = np.asarray(c, dtype=np.int)
        pa, pb = b - c, a - c
        pc = np.abs(pa + pb)
        pa, pb = np.abs(pa), np.abs(pb)
        amask = (pa <= pb) & (pa <= pc)
        bmask = (~amask) & (pb <= pc)
        cmask = (~amask) & (~bmask)
        return a * amask + b * bmask + c * cmask

def png_heuristic_predictor(image):
    out = array.array("B")
    png = PNGFast(image)
    for row in range(image.height):
        filter_num, data = png.png_predict(row, PNGPredictor.heuristic)
        out.append( filter_num )
        out.extend( data )
    return bytes(out)

def tiff_predictor(image):
    out = array.array("B")
    png = PNGFast(image)
    for row in range(image.height):
        out.extend( png.png_predict(row, PNGPredictor.sub) )
    return bytes(out)
