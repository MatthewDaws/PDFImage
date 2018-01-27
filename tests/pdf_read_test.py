import pytest

import pdfimage.pdf_read as pdf_read
import pdfimage.pdf as pdf
import os, io

@pytest.fixture
def lines1():
    x = b"Matt\nDaws\r\nStuff\n\rBob"
    return io.BytesIO(x)

def test_PDFLineReader(lines1):
    lines1.seek(0)
    lr = pdf_read.PDFLineReader(lines1)
    assert lr.read(4) == b"Matt"
    lines1.seek(0)
    assert lr.readline() == b"Matt\n"
    assert lines1.tell() == 5
    assert lr.readline() == b"Daws\r\n"
    assert lr.readline() == b"Stuff\n"
    assert lr.readline() == b"\r"
    assert lr.readline() == b"Bob"

def test_PDFLineReader_bytes():
    lr = pdf_read.PDFLineReader(b"Matt")
    assert lr.readline() == b"Matt"

def test_PDFLineReaderComments():
    lr = pdf_read.PDFLineReaderComments(b"Matt%Daws% Sutuff\nBob")
    assert lr.readline() == b"Matt"
    assert lr.readline() == b"Bob"

@pytest.fixture
def pdf1():
    return os.path.join("tests", "data", "eg.pdf")

def test_version(pdf1):
    pdf = pdf_read.PDF(pdf1)
    assert pdf.version == "%PDF-1.3"

def test_find_last_occurance():
    data = b"%%EOF\nsdgfhjga adhjg %%EOF\n"
    x = pdf_read.PDF.find_last_occurance(data, b"%%EOF")
    assert x > 0
    assert data[x:] == b"%%EOF\n"

    data = b"%%EOF\nsdgfhjga adhjg %%EOF"
    x = pdf_read.PDF.find_last_occurance(data, b"%%EOF")
    assert x == 0

    data = b"%%EOFsdgfhjga adhjg %%EOF"
    x = pdf_read.PDF.find_last_occurance(data, b"%%EOF")
    assert x == -1

def test_trailer(pdf1):
    p = pdf_read.PDF(pdf1)
    assert p.trailer[pdf.PDFName("Size")] == pdf.PDFNumeric(18)
    assert pdf.PDFName("Info") in p.trailer
    assert pdf.PDFName("Root") in p.trailer

def test_object_lookup(pdf1):
    pdf = pdf_read.PDF(pdf1)
    assert pdf.object_lookup[pdf_read.PDFObjectId(1, 0)] == 10
    assert pdf.object_lookup[pdf_read.PDFObjectId(10, 0)] == 309482

def test_split_by_whitespace():
    assert pdf_read.split_by_whitespace(b"Matt") == [b"Matt"]
    assert pdf_read.split_by_whitespace(b"Matt D") == [b"Matt", b"D"]
    assert pdf_read.split_by_whitespace(b"Matt D\x00") == [b"Matt", b"D"]
    assert pdf_read.split_by_whitespace(b" Matt \n\tD\x00\t") == [b"Matt", b"D"]
    
def test_read_object_1(pdf1):
    p = pdf_read.PDF(pdf1)
    objs = p.object_at(10)
    assert len(objs) == 1
    assert objs[0][pdf.PDFName("Pages")] == pdf.PDFObjectId(2, 0)
    assert objs[0][pdf.PDFName("Type")] == pdf.PDFName("Catalog")

def test_read_stream(pdf1):
    pdf = pdf_read.PDF(pdf1)
    loc = pdf.object_lookup[pdf_read.PDFObjectId(4, 0)]
    objs = pdf.object_at(loc)
    assert isinstance(objs[1], pdf_read.PDFStreamIndicator)
    loc = objs[1].location
    obj = pdf.read_stream(loc, 33)
    assert obj.contents.startswith(b"q\n1637")
    assert len(obj.contents) == 33

def test_read_full_object(pdf1):
    p = pdf_read.PDF(pdf1)
    loc = p.object_lookup[pdf_read.PDFObjectId(5, 0)]
    obj = p.full_object_at(loc)
    assert repr(obj) == "PDFNumeric(33)"

    loc = p.object_lookup[pdf_read.PDFObjectId(4, 0)]
    obj = p.full_object_at(loc)
    assert obj[pdf.PDFName("Length")] == pdf.PDFNumeric(33)
    assert obj.stream_contents.startswith(b"q\n1637")

def test_read_object_all(pdf1):
    pdf = pdf_read.PDF(pdf1)
    for key, location in pdf.object_lookup.items():
        # Sort of cheeky test...
        print(key, location, pdf.object_at(location))

@pytest.fixture
def pdf2():
    return os.path.join("tests", "data", "eg1.pdf")

def test_read_object_all1(pdf2):
    pdf = pdf_read.PDF(pdf2)
    for key, location in pdf.object_lookup.items():
        # Sort of cheeky test...
        print(key, location, pdf.object_at(location))
