import pytest

import pdfimage.pdf_write as pdf_write
import pdfimage.pdf as pdf
import datetime, hashlib, os

def test_DocumentCatalog():
    pages = pdf.PDFObjectId(5, 2)
    root = pdf_write.DocumentCatalog(pages)
    
    dic = root.object().data
    assert set(bytes(x) for x in dic) == {b"/Type", b"/Pages"}
    assert dic[pdf.PDFName("Type")] == pdf.PDFName("Catalog")
    assert bytes(dic[pdf.PDFName("Pages")]) == b"5 2 R"

def test_Rectangle():
    rect = pdf_write.Rectangle(5, 7, 50, 70)
    assert rect() == pdf.PDFArray([pdf.PDFNumeric(x) for x in [5, 7, 50, 70]])
    rect = pdf_write.Rectangle(xmin=5, ymin=7, xmax=50, ymax=70)
    assert rect() == pdf.PDFArray([pdf.PDFNumeric(x) for x in [5, 7, 50, 70]])

@pytest.fixture
def page1():
    mediabox = pdf_write.Rectangle(0, 1, 20, 50)
    resources = pdf.PDFDictionary([(pdf.PDFName("Matt"), pdf.PDFNumeric(7))])
    contents = pdf.PDFObjectId(3, 2)
    return pdf_write.Page(mediabox, resources, contents)

def test_Page(page1):
    page = page1
    page.parent = pdf.PDFObjectId(2, 5)

    dic = page.object().data
    assert set(bytes(x) for x in dic) == {b"/Type", b"/Parent", b"/Resources", b"/MediaBox", b"/Contents"}
    assert dic[pdf.PDFName("Type")] == pdf.PDFName("Page")
    assert bytes(dic[pdf.PDFName("Parent")]) == b"2 5 R"
    assert bytes(dic[pdf.PDFName("Resources")]) == b"<</Matt 7>>"
    assert bytes(dic[pdf.PDFName("MediaBox")]) == b"[0 1 20 50]"
    assert bytes(dic[pdf.PDFName("Contents")]) == b"3 2 R"

def test_PageTree(page1):
    pt = pdf_write.PageTree()
    pt.add_page(page1)

    pt_obj = pt.object()
    dic = pt_obj.data
    assert set(bytes(x) for x in dic) == {b"/Type", b"/Kids", b"/Count"}
    assert dic[pdf.PDFName("Type")] == pdf.PDFName("Pages")
    assert dic[pdf.PDFName("Kids")][0].number == None
    assert dic[pdf.PDFName("Count")] == pdf.PDFNumeric(1)

    assert page1.parent is pt_obj
    page1.object().number = 5
    assert dic[pdf.PDFName("Kids")][0].number == 5

def test_ColourSpaceRGB():
    assert bytes(pdf_write.ColourSpaceRGB()()) == b"/DeviceRGB"

def test_ColourSpaceGrey():
    assert bytes(pdf_write.ColourSpaceGrey()()) == b"/DeviceGray"

def test_ColourSpaceIndexed():
    import random
    pal = [tuple(random.randrange(0, 256) for _ in range(3)) for _ in range(256)]
    csi = pdf_write.ColourSpaceIndexed(pal)
    expected = b"[/Indexed /DeviceRGB 255 "
    expected += bytes(pdf.PDFString([x for y in pal for x in y]))
    expected += b"]"
    assert bytes(csi()) == expected

def test_DateTime():
    d = pdf_write.DateTime(datetime.datetime(2017, 1, 1, 12, 32, 45))
    assert bytes(d()) == b"(D:20170101123245)"

def test_InfoObject():
    io = pdf_write.InfoObject("My Title")
    dic = io.object().data
    assert set(bytes(x) for x in dic) == {b"/Title", b"/CreationDate"}
    assert dic[pdf.PDFName("Title")] == pdf.PDFString("My Title")

def test_ProcedureSet():
    ps = pdf_write.ProcedureSet()
    assert bytes(ps.object().data) == b"[/PDF /Text /ImageB /ImageC /ImageI]"

def test_ImageDictionary():
    im = pdf_write.ImageDictionary(width=1024, height=768,
        colour_space=pdf_write.ColourSpaceRGB(), bits=8)
    im.add_filtered_data("FlateDecode", b"1234", {"Predictor": 5})
    
    obj = im.object()
    dic = obj.data
    assert set(bytes(x) for x in dic) == {b"/Subtype", b"/Filter", b"/Width",
        b"/Height", b"/ColorSpace", b"/BitsPerComponent", b"/Length",
        b"/Interpolate", b"/DecodeParms"}
    assert dic[pdf.PDFName("Subtype")] == pdf.PDFName("Image")
    assert dic[pdf.PDFName("Filter")] == pdf.PDFName("FlateDecode")
    assert dic[pdf.PDFName("Width")] == pdf.PDFNumeric(1024)
    assert dic[pdf.PDFName("Height")] == pdf.PDFNumeric(768)
    assert dic[pdf.PDFName("ColorSpace")] == pdf.PDFName("DeviceRGB")
    assert dic[pdf.PDFName("BitsPerComponent")] == pdf.PDFNumeric(8)
    assert dic[pdf.PDFName("Length")] == pdf.PDFNumeric(4)
    assert dic[pdf.PDFName("Interpolate")] == pdf.PDFBoolean(True)
    #assert dic[pdf.PDFName("Predictor")] == pdf.PDFNumeric(5)
    assert bytes(dic[pdf.PDFName("DecodeParms")]) == b"<</Predictor 5>>"

    assert obj.data.stream_contents == b"1234"

def test_ImageScale():
    ims = pdf_write.ImageScale(2.5, 10)
    assert ims() == "2.5 0 0 10 0 0 cm"

def test_ImageDrawer():
    idd = pdf_write.ImageDrawer([pdf_write.ImageScale(2.5, 10)], "Im0")
    assert bytes(idd.object().data) == b"<</Length 29>>\nstream\nq\n2.5 0 0 10 0 0 cm\n/Im0 Do\nQ\nendstream"

@pytest.fixture
def test_output_dir():
    try:
        os.mkdir("test_outputs")
    except:
        pass
    return "test_outputs"

def test_PDFWriter(test_output_dir):
    pw = pdf_write.PDFWriter()
    
    font = pdf.PDFSimpleDict()
    font["Type"] = "Font"
    font["Subtype"] = "Type1"
    font["Name"] = "F1"
    font["BaseFont"] = "Helvetica"
    font["Encoding"] = "MaxRomanEncoding"
    font = pw.add_pdf_object(font.to_dict())
    resources = pdf.PDFSimpleDict()
    proc_set = pw.add_pdf_object(pdf_write.ProcedureSet().object())
    resources["ProcSet"] = proc_set
    resources["Font"] = pdf.PDFDictionary([(pdf.PDFName("F1"), font)])
    resources = resources.to_dict()
    data = b"BT\n/F1 24 Tf\n100 100 Td\n(Hello World) Tj\nET"
    contents = pdf.PDFStream([(pdf.PDFName("Length"), pdf.PDFNumeric(len(data)))], data)
    contents = pw.add_pdf_object(contents)
    page = pdf_write.Page(pdf_write.Rectangle(0, 0, 612, 792), resources, contents)

    pw.add_page(page)

    with open(os.path.join(test_output_dir, "text.pdf"), "wb") as f:
        f.write(bytes(pw))
