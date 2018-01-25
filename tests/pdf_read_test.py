import pytest

import pdfimage.pdf_read as pdf_read
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

def test_object_lookup(pdf1):
    pdf = pdf_read.PDF(pdf1)
    assert pdf.object_lookup[pdf_read.PDFObjectId(1, 0)] == 10
    assert pdf.object_lookup[pdf_read.PDFObjectId(10, 0)] == 309482

def test_split_by_whitespace():
    assert pdf_read.split_by_whitespace(b"Matt") == [b"Matt"]
    assert pdf_read.split_by_whitespace(b"Matt D") == [b"Matt", b"D"]
    assert pdf_read.split_by_whitespace(b"Matt D\x00") == [b"Matt", b"D"]
    assert pdf_read.split_by_whitespace(b" Matt \n\tD\x00\t") == [b"Matt", b"D"]
    