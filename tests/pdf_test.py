import pytest

import pdfimage.pdf as pdf
    
def test_PDFObjectId():
    obj = pdf.PDFObjectId(2, 0)
    assert obj.number == 2
    assert obj.generation == 0
    assert repr(obj) == "PDFObjectId(2, 0)"
    assert bytes(obj) == b"2 0 R"

def test_PDFObjectId_eq():
    a = pdf.PDFObjectId(1, 2)
    b = pdf.PDFObjectId(1, 3)
    c = pdf.PDFObjectId(1, 2)
    assert a != b
    assert a == c
    assert c != b
    assert hash(a) == hash(c)

def test_PDFObject():
    obj = pdf.PDFObject(pdf.PDFNumeric(12.3), 1, 5)
    assert obj.number == 1
    assert obj.generation == 5
    assert obj.data == pdf.PDFNumeric(12.3)
    assert repr(obj) == "PDFObject(1, 5)"
    assert bytes(obj) == b"1 5 R"

    obj = pdf.PDFObject(None, None, 5)
    with pytest.raises(ValueError):
        bytes(obj)
    obj.number = 1
    assert bytes(obj) == b"1 5 R"
    obj = pdf.PDFObject(None, 1, None)
    with pytest.raises(ValueError):
        bytes(obj)
    obj.generation = 5
    assert bytes(obj) == b"1 5 R"

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

    assert len({pdf.PDFBoolean(True), pdf.PDFBoolean(True)}) == 1

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

    assert len({pdf.PDFNumeric(12), pdf.PDFNumeric(12)}) == 1
    
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

    assert len({pdf.PDFString("Ma"), pdf.PDFString("Ma")}) == 1

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
    
    assert len({pdf.PDFName("Masa"), pdf.PDFName("Masa")})

def test_PDFNull():
    x = pdf.PDFNull()
    assert repr(x) == "PDFNull()"
    assert bytes(x) == b"null"
    assert x == pdf.PDFNull()

def test_PDFArray():
    x = pdf.PDFArray()
    with pytest.raises(IndexError):
        x[0]
    assert repr(x) == "PDFArray([])"
    assert bytes(x) == b"[]"
    assert x == pdf.PDFArray()

    x = pdf.PDFArray([pdf.PDFName("Matt"), pdf.PDFNumeric(12.2)])
    assert repr(x) == "PDFArray([PDFName(b'Matt'), PDFNumeric(12.2)])"
    assert bytes(x) == b"[/Matt 12.2]"
    assert x == pdf.PDFArray([pdf.PDFName("Matt"), pdf.PDFNumeric(12.2)])
    
def test_PDFDictionary():
    x = pdf.PDFDictionary()
    with pytest.raises(KeyError):
        x[pdf.PDFName("Mat")]
    assert repr(x) == "PDFDictionary({})"
    assert bytes(x) == b"<<>>"

    x = pdf.PDFDictionary([(pdf.PDFName("Bob"), pdf.PDFNumeric(12))])
    assert x[pdf.PDFName("Bob")] == pdf.PDFNumeric(12)
    assert repr(x) == "PDFDictionary({PDFName(b'Bob'): PDFNumeric(12)})"
    assert bytes(x) == b"<</Bob 12>>"
    x[pdf.PDFName("Bob")] = pdf.PDFNumeric(1)
    assert bytes(x) == b"<</Bob 1>>"

def test_PDFRawStream():
    x = pdf.PDFRawStream(b"agsgaha")
    assert x.contents == b"agsgaha"
    assert repr(x) == "PDFRawStream(length=7)"
    assert bytes(x) == b"stream\nagsgaha\nendstream"
    assert x == pdf.PDFRawStream(b"agsgaha")
    assert len({pdf.PDFRawStream(b"agsgaha"), pdf.PDFRawStream(b"agsga")}) == 2

def test_PDFStream():
    x = pdf.PDFStream([(pdf.PDFName("Length"), pdf.PDFNumeric(10))], b"abcdfgiqsp")
    assert x.stream_contents == b"abcdfgiqsp"
    assert repr(x) == "PDFDictionary({PDFName(b'Length'): PDFNumeric(10)}, stream length=10)"
    assert bytes(x) == b"<</Length 10>>\nstream\nabcdfgiqsp\nendstream"

    y = pdf.PDFStream([(pdf.PDFName("Length"), pdf.PDFNumeric(10))], b"abcdfgiqsp")
    assert x == y

def test_PDFSimpleDict():
    d = pdf.PDFSimpleDict()
    d["Filter"] = "FlateDecode"
    d["BitsPerComponent"] = 8
    d["Interpolate"] = True
    d["matt"] = 1.23

    dd = d.to_dict()
    assert dd[pdf.PDFName("Filter")] == pdf.PDFName("FlateDecode")
    assert dd[pdf.PDFName("BitsPerComponent")] == pdf.PDFNumeric(8)
    assert dd[pdf.PDFName("Interpolate")] == pdf.PDFBoolean(True)
    assert dd[pdf.PDFName("matt")] == pdf.PDFNumeric(1.23)
