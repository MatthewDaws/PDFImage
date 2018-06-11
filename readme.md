[![Build Status](https://travis-ci.org/MatthewDaws/PDFImage.svg?branch=master)](https://travis-ci.org/MatthewDaws/PDFImage)

# PDFImage

A simple, pure python library, for reading the raw contents of PDF files and writing PDF files composed of images, e.g. from scanned images.

- Native support for PNG compressed images.
- With the help of an [external compressor](https://github.com/agl/jbig2enc) support for JBIG2 compressed images (excellent compression of black and white text, for example).

## Requirements

Pure python, with:

- [PIL the pillow fork](https://pillow.readthedocs.io/en/latest/installation.html) for image manipulation
- [Numpy](http://www.numpy.org/) for fast PNG compression
- Optional use of JBIG2 requires a compiled version of [jbig2enc](https://github.com/agl/jbig2enc).  For windows, [download here](https://github.com/agl/jbig2enc/wiki/agl%27s-jbig2enc-windows-compiled-version)

## Install

Build from source:

    python setup.py install

or directly from GitHub:

    pip install https://github.com/MatthewDaws/PDFImage/zipball/master

## Usage

See the [Jupyter notebooks](notebooks/) for some examples.
