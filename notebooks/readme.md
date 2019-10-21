# Notebooks

Example of how to use the library.

- [Low level parsing example](Low%20level%20parsing%20example.ipynb) : Quick example of how to parse a PDF file and examine the individual PDF objects.
- [JBIG2 demo](JBIG2%20demo.ipynb) : Shows how to use the external JBIG2 compressor with the library to easily produce a PDF file composed of JB2 compressed black and white images.
- [PNG Demo](PNG%20Demo.ipynb) : Same as `JBIG2 demo` but uses the libraries internal PNG compression.  This is a little slow, but it's nice not to be dependant on an external programme.
- [JBIG2 and PNG demo](JBIG2%20and%20PNG%20demo.ipynb) : Shows how to use the external JBIG2 compressor to automatically detect "pictures" within text, to separate these, compress the text with JB2 and the picture with PNG, and then to combine the result in a PDF file.  As a demo of the library, I like this, but the end result is not always that impressive.
- [JBIG2 with manual PNG](JBIG2%20with%20manual%20PNG.ipynb) : Manual version of the previous, where now PNG segments are selected by the user.
