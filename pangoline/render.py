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
pangoline.render
~~~~~~~~~~~~~~~~
"""
import gi
import uuid
import cairo

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

from pathlib import Path
from itertools import count
from typing import Union, Tuple, Literal, Optional, TYPE_CHECKING

from jinja2 import Environment, PackageLoader

if TYPE_CHECKING:
    from os import PathLike

def render_text(text: str,
                output_base_path: Union[str, 'PathLike'],
                paper_size: Tuple[int, int] = (210, 297),
                margins: Tuple[int, int, int, int] = (25, 30, 20, 20),
                font: str = 'Serif Normal 10',
                language: Optional[str] = None,
                base_dir: Optional[Literal['R', 'L']] = None):
    """
    Renders (horizontal) text into a sequence of PDF files and creates parallel
    ALTO files for each page.

    PDF output will be single column, justified text without word breaking.
    Paragraphs will automatically be split once a page is full but the last
    line of the page will not be justified if the paragraph continues on the
    next page.

    ALTO file output contains baselines and bounding boxes for each line in the
    text. The unit of measurement in these files is mm.

    Args:
        output_base_path: Base path of the output files. PDF files will be
                          created at `Path.with_suffix(f'.{idx}.pdf')`, ALTO
                          files at `Path.with_suffix(f'.{idx}.xml')`.
        paper_size: `(width, height)` of the PDF output in mm.
        margins: `(top, bottom, left, right)` margins in mm.
        language: Set language to enable language-specific rendering. If none
                  is set, the system default will be used.
        base_dir: Sets the base direction of the BiDi algorithm.
    """
    output_base_path = Path(output_base_path)

    loader = PackageLoader('pangoline', 'templates')
    tmpl = Environment(loader=loader).get_template('alto.tmpl')

    _mm_point = 72 / 25.4
    width, height = paper_size[0] * _mm_point, paper_size[1] * _mm_point
    top_margin = 25 * _mm_point
    bottom_margin = 30 * _mm_point
    left_margin = 20 * _mm_point
    right_margin = 20 * _mm_point

    font_desc = Pango.font_description_from_string(font)
    pango_text_width = Pango.units_from_double(width-(left_margin+right_margin))
    if language:
        pango_lang = Pango.language_from_string(language)
    else:
        pango_lang = Pango.language_get_default()
    pango_dir = {'R': Pango.Direction.RTL,
                 'L': Pango.Direction.LTR,
                 None: None}[base_dir]


    utf8_text = text.encode('utf-8')

    text_offset = 0

    for page_idx in count():
        line_splits = []

        # draw text first on dummy surface to get number of lines that fit on
        # page.
        dummy_surface = cairo.PDFSurface(None, 1, 1)
        dummy_context = cairo.Context(dummy_surface)

        dummy_layout = PangoCairo.create_layout(dummy_context)
        dummy_layout.set_justify(True)
        dummy_layout.set_width(pango_text_width)
        dummy_layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        p_context = dummy_layout.get_context()
        p_context.set_language(pango_lang)
        if pango_dir:
            p_context.set_base_dir(pango_dir)
        dummy_layout.context_changed()

        dummy_layout.set_font_description(font_desc)

        dummy_layout.set_text(utf8_text[text_offset:].decode('utf-8'))

        line_it = dummy_layout.get_iter()
        while not line_it.at_last_line():
            line = line_it.get_line_readonly()
            baseline = line_it.get_baseline()
            if baseline > Pango.units_from_double(height-(bottom_margin+top_margin)):
                break
            s_idx, e_idx = line.start_index, line.length
            line_text = utf8_text[text_offset+s_idx:text_offset+s_idx+e_idx].decode('utf-8')
            if line_text.strip():
                _, extents = line.get_extents()
                bl = Pango.units_to_double(baseline) + top_margin
                top = bl + Pango.units_to_double(extents.y)
                bottom = top + Pango.units_to_double(extents.height)
                left = Pango.units_to_double(extents.x) + left_margin
                right = left + Pango.units_to_double(extents.width)
                line_splits.append({'id': str(uuid.uuid4()),
                                    'text': line_text.strip(),
                                    'baseline': int(bl / _mm_point),
                                    'top': int(top / _mm_point),
                                    'bottom': int(bottom / _mm_point),
                                    'left': int(left / _mm_point),
                                    'right': int(right / _mm_point)})
            line_it.next_line()

        pdf_output_path = output_base_path.with_suffix(f'.{page_idx}.pdf')
        alto_output_path = output_base_path.with_suffix(f'.{page_idx}.xml')
        # write ALTO XML file
        with open(alto_output_path, 'w') as fo:
            fo.write(tmpl.render(pdf_path=pdf_output_path.name,
                                 language=pango_lang.to_string(),
                                 base_dir={'L': 'ltr', 'R': 'rtl', None: None}[base_dir],
                                 text_block_id=str(uuid.uuid4()),
                                 page_width=paper_size[0],
                                 page_height=paper_size[1],
                                 lines=line_splits))

        # draw on actual surface
        pdf_surface = cairo.PDFSurface(pdf_output_path, width, height)
        context = cairo.Context(pdf_surface)
        context.translate(left_margin, top_margin)

        layout = PangoCairo.create_layout(context)
        p_context = layout.get_context()
        p_context.set_language(pango_lang)
        if pango_dir:
            p_context.set_base_dir(pango_dir)
        layout.context_changed()
        layout.set_justify(True)
        layout.set_width(pango_text_width)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_font_description(font_desc)

        layout.set_text(utf8_text[text_offset:text_offset+s_idx+e_idx].decode('utf-8'))

        PangoCairo.show_layout(context, layout)
        text_offset += s_idx+e_idx
        if text_offset + 1 >= len(utf8_text):
            break
        pdf_surface.finish()
