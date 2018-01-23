import pytest

import pdfimage.pdf_old as pdf
import io, os

def test_OBJ():
    x = pdf.OBJ(5, 7, "Bob")
    assert x.n == 5
    assert x.m == 7
    assert x.contents == "Bob"

def test_XREF():
    x = pdf.XREF(5, 1, True)
    assert x.offset == 5
    assert x.generation == 1
    assert x.inuse == True

def test_LineReader():
    file = io.BytesIO(b"One\nTwo\rThree\r\n")
    lr = pdf.LineReader(file)
    assert lr.readline() == b"One\n"
    assert lr.readline() == b"Two\r"
    assert lr.readline() == b"Three\r\n"
    assert lr.readline() == b""

    file = io.BytesIO(b"One\nTwo\rThree\r\n")
    lr = pdf.LineReader(file, {"\n"})
    assert lr.readline() == b"One\n"
    assert lr.readline() == b"Two\rThree\r\n"
    assert lr.readline() == b""

    file = io.BytesIO(b"One\nTwo\r")
    lr = pdf.LineReader(file, {"\n"})
    assert lr.readline() == b"One\n"
    lr.pushback(b"The")
    assert lr.readline() == b"The"
    assert lr.readline() == b"Two\r"
    assert lr.readline() == b""

@pytest.fixture
def obj1():
    return io.BytesIO(b"1 0 obj\n<<\n/Pages 2 0 R\n/Type /Catalog\n>>\nendobj\n")

def test_ObjReader1(obj1):
    lr = pdf.LineReader(obj1)
    data = lr.readline()
    obj = pdf.ObjReader(data, lr).obj
    assert obj.n == 1
    assert obj.m == 0
    assert obj.contents == [b"<<\n", b"/Pages 2 0 R\n", b"/Type /Catalog\n", b">>\n"]

@pytest.fixture
def obj2():
    return io.BytesIO(b"1 0 obj <<\n/Pages 2 0 R\n/Type /Catalog\n>> endobj\n")

def test_ObjReader2(obj2):
    lr = pdf.LineReader(obj2)
    data = lr.readline()
    obj = pdf.ObjReader(data, lr).obj
    assert obj.n == 1
    assert obj.m == 0
    assert obj.contents == [b"<<\n", b"/Pages 2 0 R\n", b"/Type /Catalog\n", b">> "]

@pytest.fixture
def example_filename():
    return os.path.join("tests", "eg.pdf")

def test_load_example(example_filename):
    with open(example_filename, "rb") as file:
        pdf.PDF(file)

@pytest.fixture
def pdflatex_filename():
    return os.path.join("tests", "out.pdf")

def FAILING_test_load_example(pdflatex_filename):
    with open(pdflatex_filename, "rb") as file:
        pdf.PDF(file)
