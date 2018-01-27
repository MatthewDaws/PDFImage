import pytest

import pdfimage.pdf_parser as pdf_parser
import pdfimage.pdf as pdf
import io

def test_PullBytesStream():
    # TEST `tell`
    st = pdf_parser.PullBytesStream(b"0123456789")
    assert len(st) == 10
    assert st.tell() == 0
    assert st[0] == b"0"[0]
    assert st[5] == b"5"[0]
    assert st[9] == b"9"[0]
    assert st.tell() == 0
    with pytest.raises(IndexError):
        st[10]

    assert st.read(2) == b"01"
    assert st.tell() == 2
    assert len(st) == 8
    assert st[0] == b"2"[0]

    assert st.read() == b"23456789"
    assert st.tell() == 10
    assert len(st) == 0
    with pytest.raises(IndexError):
        st[0]

    st = pdf_parser.PullBytesStream(b"0123456789")
    assert st[:5] == b"01234"
    assert st[2:3] == b"2"
    assert st[2:6:2] == b"24"

    st = pdf_parser.PullBytesStream(b"01 \t234\x00\n\r567")
    assert st.read(2) == b"01"
    st.skip_whitespace()
    assert len(st) == 9
    assert st[:3] == b"234"
    st.skip_whitespace()
    assert len(st) == 9
    assert st[:3] == b"234"
    st.read(3)
    st.skip_whitespace()
    assert len(st) == 3
    assert st[:3] == b"567"

    st = pdf_parser.PullBytesStream(b"01 \t234\x00\n\r567")
    assert pdf_parser.length_suffix_whitespace(st) == 0
    assert pdf_parser.length_suffix_whitespace(st, 2) == 2
    st.read(2)
    assert pdf_parser.length_suffix_whitespace(st) == 2

def test_at_eol_marker():
    assert pdf_parser.at_eol_marker(b"\x0a", 0) == 1
    assert pdf_parser.at_eol_marker(b"\x0d", 0) == 1
    assert pdf_parser.at_eol_marker(b"\x0d\x0a", 0) == 2
    assert pdf_parser.at_eol_marker(b"\x0a\x0d", 0) == 1

    assert pdf_parser.at_eol_marker(b"sss\x0a", 3) == 1
    assert pdf_parser.at_eol_marker(b"sss\x0d", 3) == 1
    assert pdf_parser.at_eol_marker(b"sss\x0d\x0a", 3) == 2
    assert pdf_parser.at_eol_marker(b"sss\x0a\x0d", 3) == 1

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

def test_ParseArray():
    p = pdf_parser.ParseArray()
    assert p.parse(b"ahsg") is None
    assert p.parse(b"[512 /Matt (Bob)]") == (None, 1)

def test_ArrayConsumer():
    p = pdf_parser.ParseArray()
    c = p.consumer()
    assert isinstance(c, pdf_parser.ArrayConsumer)

    c.consume(pdf.PDFName("Matt"))
    assert c.end(b"123.2") is None
    assert c.end(b"]ahsgas") == 1
    assert c.build() == pdf.PDFArray([pdf.PDFName("Matt")])

def test_ParseDictionary():
    p = pdf_parser.ParseDictionary()
    assert p.parse(b"ahsga") is None
    assert p.parse(b"<</Mat 12>>") == (None, 2)
    
def test_DictionaryConsumer():
    p = pdf_parser.ParseDictionary()
    c = p.consumer()
    assert isinstance(c, pdf_parser.DictionaryConsumer)

    assert c.end(b"ajsdga") is None
    assert c.end(b">>ahsga") == 2

    c.consume(pdf.PDFName("Mat"))
    c.consume(pdf.PDFObjectId(12, 0))
    d = c.build()
    assert bytes(d[pdf.PDFName("Mat")]) == b"12 0 R"

def test_StreamParser():
    p = pdf_parser.StreamParser(5)
    assert p.parse(b"ahjsga") is None
    assert p.parse(b"stream\n8gsd5\nendstream<<") == (pdf.PDFRawStream(b"8gsd5"), 22)
    assert p.parse(b"stream\r\n8gsd5endstream<<") == (pdf.PDFRawStream(b"8gsd5"), 22)
    assert p.parse(b"stream\r8gsd5endstream<<") is None

    with pytest.raises(pdf_parser.ParseError):
        p.parse(b"stream\n8gsd55\nendstream<<")
    with pytest.raises(pdf_parser.ParseError):
        p.parse(b"stream\n8gsdendstream<<")

def test_PDFParser_1():
    f = io.BytesIO(b"\n<</Linearized 1/L 10171355/O 1489/E 14578/N 480/T 10169091/H [ 470 1215]>>\n")
    p = pdf_parser.PDFParser(f)
    got = list(p)
    assert len(got) == 1
    got = got[0]
    assert got[pdf.PDFName("Linearized")] == pdf.PDFNumeric(1)
    assert got[pdf.PDFName("L")] == pdf.PDFNumeric(10171355)
    assert got[pdf.PDFName("O")] == pdf.PDFNumeric(1489)
    assert got[pdf.PDFName("E")] == pdf.PDFNumeric(14578)
    assert got[pdf.PDFName("N")] == pdf.PDFNumeric(480)
    assert got[pdf.PDFName("T")] == pdf.PDFNumeric(10169091)
    assert got[pdf.PDFName("H")] == pdf.PDFArray([pdf.PDFNumeric(470), pdf.PDFNumeric(1215)])

    keys = []
    for x in got:
        assert isinstance(x, pdf.PDFName)
        keys.append(x.name)
    assert set(keys) == {b"Linearized", b"L", b"O", b"E", b"N", b"T", b"H"}
    
def test_PDFParser_2():
    f = io.BytesIO(b"<<\n>>\n")
    p = pdf_parser.PDFParser(f)
    got = list(p)
    assert len(got) == 1
    got = got[0]
    print(got)
