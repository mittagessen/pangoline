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
import re
import pypdfium2 as pdfium

from PIL import Image
from lxml import etree
from pathlib import Path
from typing import Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from os import PathLike


@staticmethod
def _parse_alto_pointstype(coords: str) -> list[tuple[float, float]]:
    """
    ALTO's PointsType is underspecified so a variety of serializations are valid:

        x0, y0 x1, y1 ...
        x0 y0 x1 y1 ...
        (x0, y0) (x1, y1) ...
        (x0 y0) (x1 y1) ...

    Returns:
        A list of tuples [(x0, y0), (x1, y1), ...]
    """
    float_re = re.compile(r'[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?')
    points = [float(point.group()) for point in float_re.finditer(coords)]
    if len(points) % 2:
        raise ValueError(f'Odd number of points in points sequence: {points}')
    return points


def rasterize_document(doc: Union[str, 'PathLike'],
                       output_base_path: Union[str, 'PathLike'],
                       writing_surface: Optional[Union[str, 'PathLike']] = None,
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
        writing_surfaces: Path to image file used as a background writing
                          surface on which the rasterized text is pasted on.
                          The image will be resized to the selected PDF
                          resolution.
        dpi: DPI to render the PDF

    """
    output_base_path = Path(output_base_path)
    doc = Path(doc)

    if writing_surface:
        writing_surface = Image.open(writing_surface).convert('RGBA')

    coord_scale = dpi / 25.4
    _dpi_point = 1 / 72

    tree = etree.parse(doc)
    tree.find('.//{*}MeasurementUnit').text = 'pixel'
    fileName = tree.find('.//{*}fileName')
    pdf_file = doc.parent / fileName.text
    # rasterize and save as png
    pdf_page = pdfium.PdfDocument(pdf_file).get_page(0)
    transparency = 0 if writing_surface else 255
    im = pdf_page.render(scale=dpi*_dpi_point, fill_color=(255, 255, 255, transparency)).to_pil()
    if writing_surface:
        writing_surface = writing_surface.resize(im.size)
        writing_surface.alpha_composite(im)
        im = writing_surface

    fileName.text = doc.with_suffix('.png').name

    im.save(output_base_path / fileName.text, format='png', optimize=True)

    # rewrite coordinates
    page = tree.find('.//{*}Page')
    printspace = page.find('./{*}PrintSpace')
    page.set('WIDTH', str(im.width))
    page.set('HEIGHT', str(im.height))
    printspace.set('WIDTH', str(im.width))
    printspace.set('HEIGHT', str(im.height))

    for line in tree.findall('.//{*}TextLine'):
        hpos = int(float(line.get('HPOS')) * coord_scale)
        vpos = int(float(line.get('VPOS')) * coord_scale)
        width = int(float(line.get('WIDTH')) * coord_scale)
        height = int(float(line.get('HEIGHT')) * coord_scale)
        line.set('HPOS', str(hpos))
        line.set('VPOS', str(vpos))
        line.set('WIDTH', str(width))
        line.set('HEIGHT', str(height))
        bl_x0, bl_y0, bl_x1, bl_y1 = _parse_alto_pointstype(line.get('BASELINE'))
        line.set('BASELINE', f'{int(bl_x0 * coord_scale)},{int(bl_y0 * coord_scale)} {int(bl_x1 * coord_scale)},{int(bl_y1 * coord_scale)}')
        pol = line.find('.//{*}Polygon')
        pol.set('POINTS', f'{hpos},{vpos} {hpos+width},{vpos} {hpos+width},{vpos+height} {hpos},{vpos+height}')
    tree.write(output_base_path / doc.name, encoding='utf-8')
