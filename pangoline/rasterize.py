#
# Copyright 2025 Benjamin Kiessling
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing
# permissions and limitations under the License.
"""
pangoline.rasterize
~~~~~~~~~~~~~~~~~~~
"""
import pypdfium2 as pdfium

from lxml import etree
from pathlib import Path
from itertools import count
from typing import Union, Tuple, Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from os import PathLike


def rasterize_document(doc: Union[str, 'PathLike'],
                       output_base_path: Union[str, 'PathLike'],
                       dpi: int = 300):
    """
    Takes an ALTO XML file, rasterizes the associated PDF document with the
    given resolution and rewrites the ALTO, translating the physical dimension
    to pixel positions.

    The output image and XML files will be at `output_base_path/doc`.

    Args:
        doc: Input ALTO file
        output_base_path: Directory to write output image file and rewritten
                          ALTO into.
        dpi: DPI to render the PDF

    """
    output_base_path = Path(output_base_path)
    doc = Path(doc)

    coord_scale = dpi / 25.4
    _dpi_point = 1 / 72

    tree = etree.parse(doc)
    mmu = tree.find('.//{*}MeasurementUnit').text = 'pixel'
    fileName = tree.find('.//{*}fileName')
    pdf_file = fileName.text
    # rasterize and save as png
    pdf_page =  pdfium.PdfDocument(pdf_file).get_page(0)
    im = pdf_page.render(scale=dpi*_dpi_point).to_pil()
    fileName.text = str(output_base_path / doc.with_suffix('.png').name)
    im.save(fileName.text, format='png', optimize=True)

    # rewrite coordinates
    page = tree.find('.//{*}Page')
    printspace = page.find('./{*}PrintSpace')
    page.set('WIDTH', str(im.width))
    page.set('HEIGHT', str(im.height))
    printspace.set('WIDTH', str(im.width))
    printspace.set('HEIGHT', str(im.height))

    for line in tree.findall('.//{*}TextLine'):
        hpos = int(int(line.get('HPOS')) * coord_scale)
        vpos = int(int(line.get('VPOS')) * coord_scale)
        width = int(int(line.get('WIDTH')) * coord_scale)
        height = int(int(line.get('HEIGHT')) * coord_scale)
        line.set('HPOS', str(hpos))
        line.set('VPOS', str(vpos))
        line.set('WIDTH', str(width))
        line.set('HEIGHT', str(height))
        line.set('BASELINE', f'{hpos},{vpos} {hpos+width},{vpos+height}')
        pol = line.find('.//{*}Polygon')
        pol.set('POINTS', f'{hpos},{vpos} {hpos+width},{vpos} {hpos+width},{vpos+height} {hpos},{vpos+height}')
    tree.write(output_base_path / doc, encoding='utf-8')
