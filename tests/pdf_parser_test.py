import pytest

import pdfimage.pdf_parser as pdf_parser
import pdfimage.pdf as pdf

def test_PullBytesStream():
    st = pdf_parser.PullBytesStream(b"0123456789")
    assert len(st) == 10
    assert st[0] == b"0"[0]
    assert st[5] == b"5"[0]
    assert st[9] == b"9"[0]
    with pytest.raises(IndexError):
        st[10]

    assert st.read(2) == b"01"
    assert len(st) == 8
    assert st[0] == b"2"[0]

    assert st.read() == b"23456789"
    assert len(st) == 0
    with pytest.raises(IndexError):
        st[0]

    st = pdf_parser.PullBytesStream(b"0123456789")
    assert st[:5] == b"01234"
    assert st[2:3] == b"2"
    assert st[2:6:2] == b"24"

def test_BooleanParser():
    p = pdf_parser.BooleanParser()
    assert p.parse(b"basga") is None
    assert p.parse(b"true aljsdhga") == (pdf.PDFBoolean(True), 4)
    assert p.parse(b"false/A true") == (pdf.PDFBoolean(False), 5)

def test_NumericParser():
    p = pdf_parser.NumericParser()
    assert p.parse(b"Bob") is None
    assert p.parse(b"1521/T asa") == (pdf.PDFNumeric(1521), 4)
    assert p.parse(b"-.002/T asa") == (pdf.PDFNumeric(-0.002), 5)
    with pytest.raises(pdf_parser.ParseError):
        p.parse(b"+121.261.1622 ahsga")
    with pytest.raises(pdf_parser.ParseError):
        p.parse(b"1521a")

def test_StringParser():
    p = pdf_parser.StringParser()
    assert p.parse("5ada") is None
    assert p.parse(b"(Matt)asa") == (pdf.PDFString("Matt"), 6)
    assert p.parse(b"(Matt)") == (pdf.PDFString("Matt"), 6)
    assert p.parse(b"()asa") == (pdf.PDFString(""), 2)
    with pytest.raises(pdf_parser.ParseError):
        p.parse(b"(Matt")
    assert p.parse(b"(Matt \\\nnew line\\\none)asa") == (pdf.PDFString("Matt new lineone"), 22)
    assert p.parse(b"(Matt \\\x0anew line\\\x0d\x0aone)asa")[0] == pdf.PDFString("Matt new lineone")
    assert p.parse(b"(Matt\x0dOne\x0aTwo\x0d\x0aThree)")[0] == pdf.PDFString("Matt\nOne\nTwo\nThree")
    assert p.parse(b"(ahsdag##?)") == (pdf.PDFString("ahsdag##?"), 11)
    assert p.parse(b"(M\\nn)")[0] == pdf.PDFString(b"M\nn")
    assert p.parse(b"(M\\rn)")[0] == pdf.PDFString(b"M\rn")
    assert p.parse(b"(M\\tn)")[0] == pdf.PDFString(b"M\tn")
    assert p.parse(b"(M\\bn)")[0] == pdf.PDFString(b"M\bn")
    assert p.parse(b"(M\\fn)")[0] == pdf.PDFString(b"M\fn")
    assert p.parse(b"(M\\(??\\)n)")[0] == pdf.PDFString(b"M(??)n")
    assert p.parse(b"(M\\\\n)")[0] == pdf.PDFString(b"M\\n")
    assert p.parse(b"(Mat\\164)")[0] == pdf.PDFString(b"Matt")
    assert p.parse(b"(Mat\\0536)")[0] == pdf.PDFString(b"Mat+6")
    assert p.parse(b"(Mat\\53as)")[0] == pdf.PDFString(b"Mat+as")

def test_HexStringParser():
    p = pdf_parser.HexStringParser()
    assert p.parse(b"ahsha") is None
    assert p.parse(b"<4E>") == (pdf.PDFString(b"\x4e"), 4)
    assert p.parse(b"<4e>asa") == (pdf.PDFString(b"\x4e"), 4)
    assert p.parse(b"< 4e  >asa") == (pdf.PDFString(b"\x4e"), 7)
    assert p.parse(b"<4e5d4fEE>asa") == (pdf.PDFString(b"\x4e\x5d\x4f\xee"), 10)
    with pytest.raises(pdf_parser.ParseError):
        p.parse(b"<4a")
    assert p.parse(b"<4a5>asa") == (pdf.PDFString(b"\x4a\x50"), 5)
    with pytest.raises(pdf_parser.ParseError):
        p.parse(b"<4at0>")

def test_ParseName():
    p = pdf_parser.ParseName()
    assert p.parse(b"asa") is None
    assert p.parse(b"/Matt asa") == (pdf.PDFName("Matt"), 5)
    assert p.parse(b"/Matt") == (pdf.PDFName("Matt"), 5)
    assert p.parse(b"/Matt#20 asa") == (pdf.PDFName("Matt "), 8)
    assert p.parse(b"/Matt/Bob") == (pdf.PDFName("Matt"), 5)
    
def test_ParseNull():
    p = pdf_parser.ParseNull()
    assert p.parse(b"nul") is None
    assert p.parse(b"nulll") is None
    assert p.parse(b"null ") == (pdf.PDFNull(), 4)
    assert p.parse(b"null/Ma") == (pdf.PDFNull(), 4)

def test_ParseObjectId():
    p = pdf_parser.ParseObjectId()
    assert p.parse(b"ahjkdga") is None
    assert p.parse(b"521") is None
    assert p.parse(b"512 ada") is None
    assert p.parse(b"512[12 R]") is None
    assert p.parse(b"512 12 ") is None
    assert p.parse(b"512 12 basa") is None
    assert p.parse(b"512 12 RR") is None
    assert p.parse(b"512 12 R<") == (pdf.PDFObjectId(512, 12), 8)
    assert p.parse(b"512 12 R ahdsga") == (pdf.PDFObjectId(512, 12), 8)
