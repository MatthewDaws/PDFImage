import pytest
import unittest.mock as mock

import pdfimage.jb2 as jb2
import pdfimage.pdf_write as pdf_write
import subprocess, os

@mock.patch("subprocess.run")
def test_JBIG2Compressor(mock_runner):
    compressor = jb2.JBIG2Compressor()
    mock_runner.return_value.returncode = 0
    result = compressor.encode(["file1.png", "file2.jpg"])

    assert result is mock_runner.return_value
    expected_args = [jb2._default_jbig2_exe, "-s", "-p", "-v", "-2", "file1.png", "file2.jpg"]
    mock_runner.assert_called_once_with(expected_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    mock_runner.return_value.returncode = 1
    with pytest.raises(AssertionError):
        result = compressor.encode([])

@mock.patch("subprocess.run")
def test_JBIG2Compressor_with_path(mock_runner):
    compressor = jb2.JBIG2Compressor("test.exe")
    mock_runner.return_value.returncode = 0
    result = compressor.encode(["file1.png", "file2.jpg"])

    expected_args = ["test.exe", "-s", "-p", "-v", "-2", "file1.png", "file2.jpg"]
    mock_runner.assert_called_once_with(expected_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

@pytest.fixture
def test_output_dir():
    try:
        os.mkdir("test_outputs")
    except:
        pass
    return "test_outputs"

@pytest.fixture
def jb2zip():
    return os.path.join("tests", "data", "jbig2.zip")

def test_JBIG2Images(test_output_dir, jb2zip):
    result = jb2.JBIG2Images(jb2zip).parts

    writer = pdf_write.PDFWriter()
    result.add_to_pdf_writer(writer)
    with open(os.path.join(test_output_dir, "jb2_test.pdf"), "wb") as f:
        f.write(bytes(writer))
