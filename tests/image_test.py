import pytest

import pdfimage.image as image
import PIL.Image
import os
import numpy as np

@pytest.fixture
def image_11():
    filename = os.path.join("tests", "data", "11.png")
    return PIL.Image.open(filename)

@pytest.fixture
def image_12():
    filename = os.path.join("tests", "data", "12.png")
    return PIL.Image.open(filename)

@pytest.fixture
def image_21():
    filename = os.path.join("tests", "data", "21.jpg")
    return PIL.Image.open(filename)

@pytest.fixture
def image_22():
    filename = os.path.join("tests", "data", "22.jpg")
    return PIL.Image.open(filename)

def test_Image_image(image_11):
    im = image.Image(image_11)
    assert im.image is image_11

def test_Image_to_array_8bit(image_11):
    im = image.Image(image_11)
    x = im.to_array()
    assert x.shape == (300, 310, 1)
    assert all(a==255 for a in x[:,0,0])

def test_Image_row(image_11):
    im = image.Image(image_11)
    row = im.row(0)
    assert row.width == 300
    expected = np.asarray([255]*300)[:,None]
    np.testing.assert_allclose(row.bytes, expected)

def test_Image_to_array_24bit(image_21):
    im = image.Image(image_21)
    x = im.to_array()
    assert x.shape == (100, 200, 3)

def test_Image_row_24bit(image_21):
    im = image.Image(image_21)
    row = im.row(0)
    assert row.width == 100
    assert row.bytes.shape == (100, 3)

def test_Image_find_maximum_solid_rectangle(image_11):
    im = image.Image(image_11)
    assert im.find_maximum_solid_rectangle(1, 1) == (0, 0, 299, 79)

def test_find_vertical_overlap1(image_11, image_12):
    y = image.find_vertical_overlap(image.Image(image_11), image.Image(image_12), 5)
    assert y == 250

def test_find_vertical_overlap1a(image_11, image_12):
    y = image.find_vertical_overlap(image_11, image_12, 5)
    assert y == 250

def test_find_vertical_overlap2(image_21, image_22):
    y = image.find_vertical_overlap(image.Image(image_21), image.Image(image_22), 5, maximum_difference=1000)
    assert y == 102
    with pytest.raises(Exception):
        image.find_vertical_overlap(image.Image(image_21), image.Image(image_22), 5, maximum_difference=100)

def test_SplitByRows():
    d = np.random.randint(0, 256, 100*200)
    d[0:100] = 128
    d[100:200] = 128
    d[200:300] = 145
    d[1000:1500] = 128
    im = PIL.Image.frombytes("L", (100,200), bytes(list(d)))
    row = image.Image(im).row(0)
    sbr = image.SplitByRows(im, row)
    assert list(sbr.to_parts()) == [(2,9), (15,199)]

    a, b = list(sbr.to_sub_images())
    assert a.size == (100, 8)
    assert b.size == (100, 185)
