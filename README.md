# PangoLine

PangoLine is a basic tool to render raw (horizontal) text into PDF documents
and create parallel ALTO files for each page containing baseline and bounding
box information. 

It is intended to support the rendering of most of the world's writing systems
in order to create synthetic page-level training data for automatic text
recognition systems. Functionality is fairly basic for now. PDF output is
single column, justified text without word breaking. Paragraphs are split
automatically once a page is full.

## Installation

You'll need PyGObject and the Pango/Cairo libraries on your system. As
PyGObject is only shipped in source form this also requires a C compiler and
the usual build environment dependencies installed. An easier way is to use conda:

    ~> conda create --name pangoline-py3.11 -c conda-forge python=3.11
    ~> conda activate pangoline-py3.11
    ~> conda install -c conda-forge pygobject pango Cairo click jinja2 rich pypdfium2 lxml pillow

Afterwards either install from pypi:

    ~> pip install pangoline-tool

or directly from the checked out git repository:

    ~> pip install --no-deps .

## Usage

### Rendering

PangoLine renders text first into vector PDFs and ALTO facsimiles using some
configurable "physical" dimensions.

    ~> pangoline render doc.txt
    Rendering ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00

Various options to direct rendering such as page size, margins, language, and
base direction can be manually set, for example:

    ~> pangoline render -p 216 279 -l en-us -f "Noto Sans 24" doc.txt

Text can also be styled with [Pango
Markup](https://docs.gtk.org/Pango/pango_markup.html). Parsing is disabled per
default but can be enabled with a switch:

    ~> pangoline render --markup doc.txt

It is possible to randomly insert stylization of Unicode [word
segments](https://unicode.org/reports/tr29/#Word_Boundaries) in the text. One
or more styles will be randomly selected from a configurable list of styles:

    ~> pangoline render --random-markup-probability 0.01 doc.txt

The probability is the probability of at least one style being applied to any
particular segment. A subset of the total available number of styles is enabled
by default when a probability greater than 0 is given. To change the list of
possible styles:

    ~> pangoline render --random-markup-probability 0.01 --random-markup style_italic --random-markup variant_smallcaps doc.txt

The semantics of each value can be found in the [pango documentation](https://docs.gtk.org/Pango/pango_markup.html).

Styling with color is treated slightly differently than other styles. In
general, colors are selected with the `foreground_*` style. As a large number
of colors are known to Pango, the `foreground_random` alias exists that enables
all possible colors:

    ~> pangoline render  --random-markup-probability 0.01 --random-markup foreground_random doc.txt

### Rasterization

In a second step those vector files can be rasterized into PNGs and the
coordinates in the ALTO files scaled to the selected resolution (per default
300dpi):

    ~> pangoline rasterize doc.0.xml doc.1.xml ...
    Rasterizing ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00

Rasterized files and their ALTOs can be used as is as ATR training data.

To obtain slightly more realistic input images it is possible to overlay the
rasterized text into images of writing surfaces.

    ~> pangoline rasterize -w ~/background_1.jpg doc.0.xml doc.1.xml ...

Rasterization can be invoked with multiple background images in which case they
will be sampled randomly for each output page. A tarball with 70 empty paper
backgrounds of different origins, digitization qualities, and states of
preservation can be found [here](http://l.unchti.me/paper.tar).

For larger collections of texts it is advisable to parallelize processing,
especially for rasterization with overlays:

    ~> pangoline --workers 8 render *.txt
    ~> pangoline --workers 8 rasterize *.xml

## Limitations

In order to achieve proper typesetting quality, Pango requires placing the
whole text into a single layout before splitting it into individual pages by
translating each line of the layout onto a page surface. This approach limits to
maximum print space of a single text to 739.8 meters, roughly 3000 pages
depending on paper size and margins, before an overflow of the 32 bit integer
baseline position y-offset will occur.

## Funding

<table border="0">
 <tr>
    <td> <img src="https://raw.githubusercontent.com/mittagessen/kraken/main/docs/_static/normal-reproduction-low-resolution.jpg" alt="Co-financed by the European Union" width="100"/></td>
    <td>This project was funded in part by the European Union. (ERC, MiDRASH,project number 101071829).</td>
 </tr>
</table>
