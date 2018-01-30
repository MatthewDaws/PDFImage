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

def test_UncompressedImage_combine(grey_image, palette_image, blackwhite_image, test_output_dir):
    writer = pdf_write.PDFWriter()

    parts = pdf_image.UncompressedImage(palette_image)()
    parts.add_to_pdf_writer(writer)
    parts = pdf_image.UncompressedImage(grey_image)()
    parts.add_to_pdf_writer(writer)
    parts = pdf_image.UncompressedImage(blackwhite_image)()
    parts.add_to_pdf_writer(writer)

    with open(os.path.join(test_output_dir, "uncompressed_three_up.pdf"), "wb") as f:
        f.write(bytes(writer))

@pytest.fixture
def rgb_image():
    filename = os.path.join("tests", "data", "22.jpg")
    return PIL.Image.open(filename)

def test_UncompressedImage_rgb(rgb_image, test_output_dir):
    image = pdf_image.UncompressedImage(rgb_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "uncompressed_image_rgb.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_FlateImage_rgb(rgb_image, test_output_dir):
    image = pdf_image.FlateImage(rgb_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "flate_image_rgb.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_FlateImage(grey_image, test_output_dir):
    image = pdf_image.FlateImage(grey_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "flate_image_grey.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_PNGImage(grey_image, test_output_dir):
    image = pdf_image.PNGImage(grey_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "png_image_grey.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_PNGImage_RGB(rgb_image, test_output_dir):
    image = pdf_image.PNGImage(rgb_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "png_image_rgb.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_TIFFImage(grey_image, test_output_dir):
    image = pdf_image.TIFFImage(grey_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "tiff_image_grey.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_TIFFImage_RGB(rgb_image, test_output_dir):
    image = pdf_image.TIFFImage(rgb_image)
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "tiff_image_rgb.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_Flate_Multiple_Image1(test_output_dir, rgb_image, blackwhite_image):
    image = pdf_image.FlateMultiImage(blackwhite_image)
    image.add_top_image(rgb_image, (10, 20), (50, 50))
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "multi_flate_1.pdf"), "wb") as f:
        f.write(bytes(writer))
    
def test_Flate_Multiple_Image2(test_output_dir, rgb_image, blackwhite_image):
    image = pdf_image.FlateMultiImage(rgb_image)
    image.add_top_image(blackwhite_image, (10, 20), (80, 150))
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "multi_flate_2.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_Flate_Multiple_Image3(test_output_dir, rgb_image, blackwhite_image):
    image = pdf_image.FlateMultiImage(rgb_image)
    image.add_top_image(blackwhite_image, (10, 20), (80, 150), (1, 1))
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "multi_flate_3.pdf"), "wb") as f:
        f.write(bytes(writer))

def test_Flate_Multiple_Image4(test_output_dir, rgb_image, grey_image):
    image = pdf_image.FlateMultiImage(rgb_image)
    image.add_top_image(grey_image, (10, 20), (80, 150), (200, 255))
    parts = image()

    writer = pdf_write.PDFWriter()
    parts.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "multi_flate_4.pdf"), "wb") as f:
        f.write(bytes(writer))
