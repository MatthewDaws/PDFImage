import pytest
import unittest.mock as mock

import pdfimage.pdf_image as pdf_image
import pdfimage.pdf_write as pdf_write
import os
import PIL.Image

def test_PDFImageParts():
    page = mock.Mock()
    objects = [mock.Mock()]
    parts = pdf_image.PDFImageParts(page, objects)

    assert parts.page is page
    assert parts.objects == objects

    pdf_writer = mock.Mock()
    parts.add_to_pdf_writer(pdf_writer)
    pdf_writer.add_page.assert_called_with(page)
    pdf_writer.add_pdf_object.assert_called_with(objects[0])

@pytest.fixture
def test_output_dir():
    try:
        os.mkdir("test_outputs")
    except:
        pass
    return "test_outputs"

@pytest.fixture
def grey_image():
    filename = os.path.join("tests", "data", "11.png")
    return PIL.Image.open(filename)

def test_UncompressedImage(grey_image, test_output_dir):
    image = pdf_image.UncompressedImage(grey_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "uncompressed_image_grey.pdf"), "wb") as f:
        f.write(bytes(writer))

@pytest.fixture
def palette_image():
    filename = os.path.join("tests", "data", "palette.png")
    return PIL.Image.open(filename)

def test_UncompressedImage_palette(palette_image, test_output_dir):
    image = pdf_image.UncompressedImage(palette_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "uncompressed_image_palette.pdf"), "wb") as f:
        f.write(bytes(writer))

@pytest.fixture
def blackwhite_image():
    filename = os.path.join("tests", "data", "bw.png")
    return PIL.Image.open(filename)

def test_UncompressedImage_bw(blackwhite_image, test_output_dir):
    image = pdf_image.UncompressedImage(blackwhite_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "uncompressed_image_bw.pdf"), "wb") as f:
        f.write(bytes(writer))
