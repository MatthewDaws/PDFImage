from setuptools import setup, find_packages

def find_version():
    import os
    with open(os.path.join("pdfimage", "__init__.py")) as file:
        for line in file:
            if line.startswith("__version__"):
                start = line.index('"')
                end = line[start+1:].index('"')
                return line[start+1:][:end]
            
long_description = ""

setup(
    name = 'pdfimage',
    packages = find_packages(include=["pdfimage*"]),
    version = find_version(),
    install_requires = [], # TODO
    python_requires = '>=3.5',
    description = 'Generate PDF files from images, in pure Python',
    long_description = long_description,
    author = 'Matthew Daws',
    author_email = 'matthew.daws@gogglemail.com',
    url = 'https://github.com/MatthewDaws/PDFImage',
    license = 'MIT',
    keywords = [],
    classifiers = [
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion"
    ]
)