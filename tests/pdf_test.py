import pytest

import pdfimage.pdf as pdf
    
def test_PDFObjectId():
    obj = pdf.PDFObjectId(2, 0)
    assert obj.number == 2
    assert obj.generation == 0
    assert repr(obj) == "PDFObjectId(2, 0)"
    assert bytes(obj) == b"2, 0"
    with pytest.raises(ValueError):
        pdf.PDFObjectId(0, 1)
    with pytest.raises(ValueError):
        pdf.PDFObjectId(1, -1)

def test_PDFObjectId_eq():
    a = pdf.PDFObjectId(1, 2)
    b = pdf.PDFObjectId(1, 3)
    c = pdf.PDFObjectId(1, 2)
    assert a != b
    assert a == c
    assert c != b
    assert hash(a) == hash(c)

def test_PDFObject():
    obj = pdf.PDFObject(1,5,b"agsa")
    assert obj.number == 1
    assert obj.generation == 5
    assert obj.data == b"agsa"
    assert repr(obj) == "PDFObject(1, 5)"

def test_PDFBoolean():
    x = pdf.PDFBoolean(True)
    assert x.value
    assert bool(x)
    assert x
    assert repr(x) == "PDFBoolean(True)"
    assert bytes(x) == b"true"
    assert x == pdf.PDFBoolean(True)
    assert x != pdf.PDFBoolean(False)

    x = pdf.PDFBoolean(False)
    assert not x.value
    assert not bool(x)
    assert not x
    assert repr(x) == "PDFBoolean(False)"
    assert bytes(x) == b"false"
    assert x != pdf.PDFBoolean(True)
    assert x == pdf.PDFBoolean(False)

def test_PDFNumeric():
    x = pdf.PDFNumeric(5)
    assert x.value == 5
    assert int(x) == 5
    assert float(x) == 5.0
    assert repr(x) == "PDFNumeric(5)"
    assert bytes(x) == b"5"
    assert x == pdf.PDFNumeric("5")

    x = pdf.PDFNumeric(5.2)
    assert x.value == pytest.approx(5.2)
    assert int(x) == 5
    assert float(x) == pytest.approx(5.2)
    assert repr(x) == "PDFNumeric(5.2)"
    assert bytes(x) == b"5.2"
    assert x == pdf.PDFNumeric("5.2")

    x = pdf.PDFNumeric("+7")
    assert x.value == 7
    assert isinstance(x.value, int)

    x = pdf.PDFNumeric("-7")
    assert x.value == -7
    assert isinstance(x.value, int)

    x = pdf.PDFNumeric("+7.523")
    assert x.value == pytest.approx(7.523)
    assert x == pdf.PDFNumeric(7.523)

    with pytest.raises(ValueError):
        pdf.PDFNumeric("a6sa")
    
def test_PDFString():
    x = pdf.PDFString(b"ahsga\xde")
    assert x.value == b"ahsga\xde"
    assert repr(x) == "PDFString(b'ahsga\\xde')"
    assert bytes(x) == b"(ahsga\xde)"
    assert x == pdf.PDFString(b"ahsga\xde")

    x = pdf.PDFString("Matt")
    assert bytes(x) == b"(Matt)"

    assert bytes(pdf.PDFString("Mat\nt")) == b"(Mat\\nt)"
    assert bytes(pdf.PDFString("Mat())\\a")) == b"(Mat\\(\\)\\)\\\\a)"

def test_PDFName():
    x = pdf.PDFName(b"Bob")
    assert x.name == b"Bob"
    assert repr(x) == "PDFName(b'Bob')"
    assert x == pdf.PDFName(b"Bob")
    assert x == pdf.PDFName("Bob")
    assert bytes(x) == b"/Bob"
    
    with pytest.raises(ValueError):
        x = pdf.PDFName("ahdga\x00")
        bytes(x)

    x = pdf.PDFName(b"Bob\n T\xee")
    assert bytes(x) == b"/Bob#0A#20T#EE"
    
def test_PDFNull():
    x = pdf.PDFNull()
    assert repr(x) == "PDFNull()"
    assert bytes(x) == b"null"
    assert x == pdf.PDFNull()
