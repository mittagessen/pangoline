# PangoLine

PangoLine is a basic tool to render raw (horizontal) text into PDF documents
and create parallel ALTO files for each page containing baseline and bounding
box information. 

It is intended to support the rendering of most of the world's writing systems
in order to create synthetic page-level training data for automatic text
recognition systems. Functionality is fairly basic for now. PDF output is
single column, justified text without word breaking. Paragraphs automatically
be split once a page is full but the last line of the page will not be
justified if the paragraph continues on the next page.

## Installation

You'll need PyGObject and the Pango/Cairo libraries on your system. As
PyGObject is only shipped in source form this also requires a C compiler and
the usual build environment dependencies installed. An easier way is to use conda:

    ~> conda install -c conda-forge pygobject pango Cairo click jinja2 rich
    ~> pip install --no-deps .

## Usage

    ~> pangoline render doc.txt

Various options to direct rendering such as page size, margins, language, and
base direction can be manually set.
