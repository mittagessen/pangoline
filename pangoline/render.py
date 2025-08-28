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
import html
import math
import uuid
import cairo
import regex
import logging
import numpy as np

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

from pathlib import Path
from itertools import count
from typing import Union, Literal, Optional, TYPE_CHECKING, Sequence

from jinja2 import Environment, PackageLoader

if TYPE_CHECKING:
    from os import PathLike

logger = logging.getLogger(__name__)

_markup_mapping = {'style': 'style',
                   'weight': 'weight',
                   'variant': 'variant',
                   'underline': 'underline',
                   'overline': 'overline',
                   'shift': 'baseline_shift',
                   'strikethrough': 'strikethrough',
                   'foreground': 'foreground'}

_markup_colors = ['aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure',
                  'beige', 'bisque', 'blanchedalmond', 'blue',
                  'blueviolet', 'brown', 'burlywood', 'cadetblue',
                  'chartreuse', 'chocolate', 'coral', 'cornflowerblue',
                  'cornsilk', 'crimson', 'cyan', 'darkblue', 'darkcyan',
                  'darkgoldenrod', 'darkgray', 'darkgrey', 'darkgreen',
                  'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange',
                  'darkorchid', 'darkred', 'darksalmon', 'darkseagreen',
                  'darkslateblue', 'darkslategray', 'darkslategrey',
                  'darkturquoise', 'darkviolet', 'deeppink', 'deepskyblue',
                  'dimgray', 'dimgrey', 'dodgerblue', 'firebrick',
                  'floralwhite', 'forestgreen', 'fuchsia', 'gainsboro',
                  'ghostwhite', 'gold', 'goldenrod', 'gray', 'grey', 'green',
                  'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo',
                  'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen',
                  'lemonchiffon', 'lightblue', 'lightcoral', 'lightcyan',
                  'lightgoldenrodyellow', 'lightgray', 'lightgrey',
                  'lightgreen', 'lightpink', 'lightsalmon', 'lightseagreen',
                  'lightskyblue', 'lightslategray', 'lightslategrey',
                  'lightsteelblue', 'lightyellow', 'lime', 'limegreen',
                  'linen', 'magenta', 'maroon', 'mediumaquamarine',
                  'mediumblue', 'mediumorchid', 'mediumpurple',
                  'mediumseagreen', 'mediumslateblue', 'mediumspringgreen',
                  'mediumturquoise', 'mediumvioletred', 'midnightblue',
                  'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 'navy',
                  'oldlace', 'olive', 'olivedrab', 'orange', 'orangered',
                  'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise',
                  'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink',
                  'plum', 'powderblue', 'purple', 'red', 'rosybrown',
                  'royalblue', 'rebeccapurple', 'saddlebrown', 'salmon',
                  'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
                  'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow',
                  'springgreen', 'steelblue', 'tan', 'teal', 'thistle',
                  'tomato', 'turquoise', 'violet', 'wheat', 'whitesmoke',
                  'yellow', 'yellowgreen']


def render_text(text: str,
                output_base_path: Union[str, 'PathLike'],
                paper_size: tuple[int, int] = (210, 297),
                margins: tuple[int, int, int, int] = (25, 30, 25, 25),
                font: str = 'Serif Normal 10',
                language: Optional[str] = None,
                base_dir: Optional[Literal['R', 'L']] = None,
                enable_markup: bool = False,
                random_markup: Optional[Sequence[Literal['style_oblique',
                                                     'style_italic',
                                                     'weight_ultralight',
                                                     'weight_bold',
                                                     'weight_ultrabold',
                                                     'weight_heavy',
                                                     'variant_smallcaps',
                                                     'underline_single',
                                                     'underline_double',
                                                     'underline_low',
                                                     'underline_error',
                                                     'overline_single',
                                                     'shift_subscript',
                                                     'shift_superscript',
                                                     'strikethrough_true',
                                                     'foreground_random']]] =
                ('style_italic', 'weight_bold', 'underline_single',
                 'underline_double', 'overline_single', 'shift_subscript',
                 'shift_superscript', 'strikethrough_true'),
                random_markup_probability: float = 0.0,
                raise_unrenderable: bool = False):
    """
    Renders (horizontal) text into a sequence of PDF files and creates parallel
    ALTO files for each page.

    PDF output will be single column, justified text without word breaking.
    Paragraphs will automatically be split once a page is full.

    ALTO file output contains baselines and bounding boxes for each line in the
    text. The unit of measurement in these files is mm.

    Args:
        output_base_path: Base path of the output files. PDF files will be
                          created at `Path.with_suffix(f'.{idx}.pdf')`, ALTO
                          files at `Path.with_suffix(f'.{idx}.xml')`.
        paper_size: `(width, height)` of the PDF output in mm.
        margins: `(top, bottom, left, right)` margins in mm.
        language: Set language to enable language-specific rendering. If none
                  is set, the system default will be used. It also sets the
                  language metadata field in the ALTO output.
        base_dir: Sets the base direction of the BiDi algorithm.
        enable_markup: Enables/disables Pango markup parsing
        random_markup: Set of text attributes to randomly apply to input text
                       segments.
        random_markup_probability: Probability with which to apply random markup to
                                 input text segments. Set to 0.0 to disable.
                                 Will automatically be disabled if
                                 `enable_markup`is set to true.
        raise_unrenderable: raises an exception if the supplied text contains
                            glyphs that are not contained in the selected
                            typeface.

    Raises:
        ValueError if the text contains unrenderable glyphs and
        raise_unrenderable is set to True.
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
    font_desc.set_features('liga=1, clig=1, dlig=1, hlig=1')
    pango_text_width = Pango.units_from_double(width-(left_margin+right_margin))
    if language:
        pango_lang = Pango.language_from_string(language)
    else:
        pango_lang = Pango.language_get_default()
    pango_dir = {'R': Pango.Direction.RTL,
                 'L': Pango.Direction.LTR,
                 None: None}[base_dir]

    dummy_surface = cairo.PDFSurface(None, 1, 1)
    dummy_context = cairo.Context(dummy_surface)

    # as it is difficult to truncate a text containing RTL runs to split it
    # into pages we render the whole text into a single PangoLayout and then
    # manually place each line on the correct position of a cairo context for
    # each page, translating the vertical coordinates by a print space offset.

    layout = PangoCairo.create_layout(dummy_context)
    layout.set_justify(True)
    layout.set_width(pango_text_width)
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    p_context = layout.get_context()
    p_context.set_language(pango_lang)
    if pango_dir:
        p_context.set_base_dir(pango_dir)
    layout.context_changed()

    layout.set_font_description(font_desc)

    if enable_markup:
        if random_markup_probability> 0.0:
            logger.warning('Input markup parsing and random markup are both enabled. Disabling random markup.')
        _, attr, text, _ = Pango.parse_markup(text, -1, u'\x00')
        layout.set_text(text)
        layout.set_attributes(attr)
    elif random_markup_probability > 0.0:
        rng = np.random.default_rng()
        random_markup = np.array(random_markup)
        marked_text = ''
        for s in regex.splititer(r'(\m\w+\M)', text):
            s = html.escape(s, quote=False)
            # only mark up words, not punctuation, whitespace ...
            if regex.match(r'\w+', s):
                ts = random_markup[rng.random(len(random_markup)) > (1 - random_markup_probability) ** (1./len(random_markup))].tolist()
                ts = {_markup_mapping[t.split('_', 1)[0]]: t.split('_', 1)[1] for t in ts}
                if (color := ts.get('foreground')) and color == 'random':
                    ts['foreground'] = rng.choice(_markup_colors)
                if ts:
                    s = '<span ' + ' '.join(f'{k}="{v}"' for k, v in ts.items()) + f'>{s}</span>'
            marked_text += s
        _, attr, text, _ = Pango.parse_markup(marked_text, -1, u'\x00')
        layout.set_text(text)
        layout.set_attributes(attr)
    else:
        layout.set_text(text)

    if unk_glyphs := layout.get_unknown_glyphs_count():
        msg = f'{unk_glyphs} unknown glyphs in text with output {output_base_path}'
        if raise_unrenderable:
            raise ValueError(msg)
        logger.warning(msg)

    utf8_text = text.encode('utf-8')

    line_it = layout.get_iter()

    page_print_space = Pango.units_from_double(height-(bottom_margin+top_margin))

    for page_idx in count():
        print_space_offset = page_idx * page_print_space

        pdf_output_path = output_base_path.with_suffix(f'.{page_idx}.pdf')
        alto_output_path = output_base_path.with_suffix(f'.{page_idx}.xml')

        logger.info(f'Rendering {page_idx} to {pdf_output_path}')

        line_splits = []

        pdf_surface = cairo.PDFSurface(pdf_output_path, width, height)
        context = cairo.Context(pdf_surface)
        context.translate(left_margin, top_margin)

        while not line_it.at_last_line():
            line = line_it.get_line_readonly()
            baseline = line_it.get_baseline()
            # integer overflow in baseline position
            if baseline < 0:
                logger.warning('Integer overflow in baseline position. Aborting.')
                return
            if baseline > print_space_offset + page_print_space:
                break
            s_idx, e_idx = line.start_index, line.length
            line_text = utf8_text[s_idx:s_idx+e_idx].decode('utf-8')
            if line_text := line_text.strip():
                # line direction determines reference point of extents
                line_dir = line.get_resolved_direction()
                ink_extents, log_extents = line.get_extents()
                Pango.extents_to_pixels(ink_extents)
                bl = Pango.units_to_double(baseline - print_space_offset) + top_margin
                top = bl + ink_extents.y
                bottom = top + ink_extents.height
                if line_dir == Pango.Direction.RTL:
                    right = (width - right_margin) - ink_extents.x
                    left = right - ink_extents.width
                    lleft = (width - right_margin) - Pango.units_to_double(log_extents.x + log_extents.width)
                elif line_dir == Pango.Direction.LTR:
                    left = ink_extents.x + left_margin
                    lleft = Pango.units_to_double(log_extents.x) + left_margin
                    right = left + ink_extents.width
                line_splits.append({'id': f'_{uuid.uuid4()}',
                                    'text': line_text,
                                    'baseline': int(round(bl / _mm_point)),
                                    'top': int(math.floor(top / _mm_point)),
                                    'bottom': int(math.ceil(bottom / _mm_point)),
                                    'left': int(math.floor(left / _mm_point)),
                                    'right': int(math.ceil(right / _mm_point))})
                context.move_to(lleft - left_margin, bl - top_margin)
                PangoCairo.show_layout_line(context, line)
            line_it.next_line()

        # write ALTO XML file
        with open(alto_output_path, 'w') as fo:
            fo.write(tmpl.render(pdf_path=pdf_output_path.name,
                                 language=pango_lang.to_string(),
                                 base_dir={'L': 'ltr', 'R': 'rtl', None: None}[base_dir],
                                 text_block_id=f'_{uuid.uuid4()}',
                                 page_width=paper_size[0],
                                 page_height=paper_size[1],
                                 lines=line_splits))

        pdf_surface.finish()
        if line_it.at_last_line():
            break
