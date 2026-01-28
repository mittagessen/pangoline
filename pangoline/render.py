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
from typing import Union, Literal, Optional, TYPE_CHECKING, Sequence, Dict

from jinja2 import Environment, PackageLoader

from .layout import PageTemplate, load_template, default_single_column_template

if TYPE_CHECKING:
    from os import PathLike

logger = logging.getLogger(__name__)

# Alignment mapping for Pango
ALIGNMENT_MAP = {
    'left': Pango.Alignment.LEFT,
    'center': Pango.Alignment.CENTER,
    'right': Pango.Alignment.RIGHT,
    'justify': Pango.Alignment.LEFT,  # justify uses LEFT + set_justify(True)
}

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
                raise_unrenderable: bool = False,
                template_path: Optional[Union[str, 'PathLike']] = None,
                parallel_texts: Optional[Dict[int, str]] = None,
                line_spacing: Optional[float] = None,
                baseline_position: Optional[float] = None,
                padding_all: Optional[float] = None,
                padding_horizontal: Optional[float] = None,
                padding_vertical: Optional[float] = None,
                padding_left: Optional[float] = None,
                padding_right: Optional[float] = None,
                padding_top: Optional[float] = None,
                padding_bottom: Optional[float] = None,
                padding_baseline: Optional[float] = None):
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
        template_path: Optional path to a JSON template file defining page
                       frames. If None, uses default single-column layout.
        parallel_texts: Optional dictionary mapping frame index to text content.
                       When provided, enables parallel bilingual column rendering.
                       Each frame renders independently with its own text. Frame indices
                       start at 0. If a frame has text in the template JSON, that takes
                       precedence over parallel_texts. Example: {0: "English text", 1: "Hebrew text"}
        line_spacing: Additional space between lines in points. None for default.
        baseline_position: Adjust baseline position vertically in mm. Positive values move
                          baseline up, negative values move it down.
        padding_all: Padding in mm applied to all sides of bounding boxes and baselines.
        padding_horizontal: Padding in mm applied to left and right sides of bounding boxes and baselines.
        padding_vertical: Padding in mm applied to top and bottom sides of bounding boxes.
        padding_left: Padding in mm applied to left side of bounding boxes and baselines.
        padding_right: Padding in mm applied to right side of bounding boxes and baselines.
        padding_top: Padding in mm applied to top side of bounding boxes.
        padding_bottom: Padding in mm applied to bottom side of bounding boxes.
        padding_baseline: Padding in mm applied to left and right endpoints of baselines only.

    Raises:
        ValueError if the text contains unrenderable glyphs and
        raise_unrenderable is set to True.
        FileNotFoundError if template_path is provided but file doesn't exist.
    """
    output_base_path = Path(output_base_path)

    loader = PackageLoader('pangoline', 'templates')
    tmpl = Environment(loader=loader).get_template('alto.tmpl')

    _mm_point = 72 / 25.4
    width, height = paper_size[0] * _mm_point, paper_size[1] * _mm_point
    top_margin, bottom_margin, left_margin, right_margin = [
        m * _mm_point for m in margins
    ]

    # Determine text direction
    # Priority: explicit base_dir > language-based detection > None
    if base_dir:
        is_rtl = (base_dir == 'R')
    elif language:
        # Detect RTL from language code (Hebrew, Arabic, etc.)
        lang_lower = language.lower()
        is_rtl = lang_lower.startswith('he') or lang_lower.startswith('ar') or lang_lower.startswith('yi')
    else:
        is_rtl = False

    # Load template or use default single-column
    if template_path:
        page_template = load_template(template_path)
        # Reverse frame order for RTL languages (right column first, then left)
        if is_rtl and len(page_template.frames) > 1:
            # Create a new template with reversed frames
            from .layout import PageTemplate, Frame
            reversed_frames = list(reversed(page_template.frames))
            page_template = PageTemplate(reversed_frames)
            logger.info(f'RTL detected: reversed {len(reversed_frames)} frames for right-to-left column flow')
    else:
        page_template = default_single_column_template(
            paper_size[0], paper_size[1],
            margins[2], margins[0], margins[3], margins[1]  # left, top, right, bottom
        )

    font_desc = Pango.font_description_from_string(font)
    font_desc.set_features('liga=1, clig=1, dlig=1, hlig=1')
    if language:
        pango_lang = Pango.language_from_string(language)
    else:
        pango_lang = Pango.language_get_default()
    pango_dir = {'R': Pango.Direction.RTL,
                 'L': Pango.Direction.LTR,
                 None: (Pango.Direction.RTL if is_rtl else Pango.Direction.LTR)}[base_dir]

    dummy_surface = cairo.PDFSurface(None, 1, 1)
    dummy_context = cairo.Context(dummy_surface)

    # Process markup and prepare text/attributes for layout
    processed_text = text
    processed_attrs = None

    if enable_markup:
        if random_markup_probability > 0.0:
            logger.warning('Input markup parsing and random markup are both enabled. Disabling random markup.')
        _, processed_attrs, processed_text, _ = Pango.parse_markup(text, -1, u'\x00')
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
        _, processed_attrs, processed_text, _ = Pango.parse_markup(marked_text, -1, u'\x00')

    # Check for unknown glyphs using a temporary layout
    temp_layout = PangoCairo.create_layout(dummy_context)
    temp_layout.set_font_description(font_desc)
    temp_layout.set_text(processed_text)
    if processed_attrs:
        temp_layout.set_attributes(processed_attrs)
    if unk_glyphs := temp_layout.get_unknown_glyphs_count():
        msg = f'{unk_glyphs} unknown glyphs in text with output {output_base_path}'
        if raise_unrenderable:
            raise ValueError(msg)
        logger.warning(msg)

    utf8_text = processed_text.encode('utf-8')
    text_len = len(processed_text)
    text_cursor = 0  # Character position in processed_text

    # Detect parallel mode: frames have text or parallel_texts is provided
    parallel_mode = False
    if parallel_texts or any(frame.text for frame in page_template.frames):
        parallel_mode = True
        logger.info('Parallel bilingual column mode enabled')
        # Prepare frame texts: priority is frame.text > parallel_texts > main text
        frame_texts = {}
        for idx, frame in enumerate(page_template.frames):
            if frame.text:
                frame_texts[idx] = frame.text
            elif parallel_texts and idx in parallel_texts:
                frame_texts[idx] = parallel_texts[idx]
            else:
                # Fallback to main text if no frame-specific text
                frame_texts[idx] = processed_text
        # Process markup for each frame text if needed
        processed_frame_texts = {}
        for idx, frame_text in frame_texts.items():
            if enable_markup:
                _, _, processed_frame_text, _ = Pango.parse_markup(frame_text, -1, u'\x00')
                processed_frame_texts[idx] = processed_frame_text
            else:
                processed_frame_texts[idx] = frame_text
        # Track cursors for each frame independently
        frame_cursors = {idx: 0 for idx in frame_texts.keys()}
        frame_text_lens = {idx: len(text) for idx, text in processed_frame_texts.items()}

    # Helper function to create a layout for a frame
    def create_frame_layout(frame_text: str, frame_width_mm: float, frame_alignment: str,
                           frame_language: Optional[str] = None, frame_base_dir: Optional[str] = None,
                           frame_font: Optional[str] = None):
        """Create a PangoLayout configured for a specific frame."""
        layout = PangoCairo.create_layout(dummy_context)
        # Use frame-specific font if provided, otherwise use global font
        if frame_font:
            frame_font_desc = Pango.font_description_from_string(frame_font)
            frame_font_desc.set_features('liga=1, clig=1, dlig=1, hlig=1')
            layout.set_font_description(frame_font_desc)
        else:
            layout.set_font_description(font_desc)
        # Convert frame width from mm to points, then to Pango units
        frame_width_pt = frame_width_mm * _mm_point
        layout.set_width(Pango.units_from_double(frame_width_pt))
        layout.set_alignment(ALIGNMENT_MAP.get(frame_alignment, Pango.Alignment.LEFT))
        layout.set_justify(frame_alignment == "justify")
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        p_context = layout.get_context()
        # Use frame-specific language if provided, otherwise use global
        if frame_language:
            p_context.set_language(Pango.language_from_string(frame_language))
        else:
            p_context.set_language(pango_lang)
        # Use frame-specific base_dir if provided, otherwise use global
        frame_pango_dir = None
        if frame_base_dir:
            frame_pango_dir = {'R': Pango.Direction.RTL, 'L': Pango.Direction.LTR}.get(frame_base_dir)
        elif pango_dir:
            frame_pango_dir = pango_dir
        if frame_pango_dir:
            p_context.set_base_dir(frame_pango_dir)
        layout.context_changed()
        layout.set_text(frame_text)
        # Note: We skip applying processed_attrs here because they're indexed for the full
        # processed_text, but frame_text is a slice. Properly adjusting attribute indices
        # for frame slices is complex and would require creating new attribute ranges.
        # For now, markup styling will work but attributes won't be preserved across frames.
        # TODO: Implement proper attribute range adjustment for multi-frame layouts
        return layout

    for page_idx in count():
        # Check if we should continue (sequential mode) or if all frames are done (parallel mode)
        if parallel_mode:
            # In parallel mode, check if all frames are exhausted
            if all(frame_cursors[idx] >= frame_text_lens[idx] for idx in frame_cursors.keys()):
                break
        else:
            # Sequential mode: check main text cursor
            if text_cursor >= text_len:
                break

        pdf_output_path = output_base_path.with_suffix(f'.{page_idx}.pdf')
        alto_output_path = output_base_path.with_suffix(f'.{page_idx}.xml')

        logger.info(f'Rendering page {page_idx} to {pdf_output_path}')

        pdf_surface = cairo.PDFSurface(pdf_output_path, width, height)
        context = cairo.Context(pdf_surface)

        # Collect all text blocks for this page (one per frame)
        page_text_blocks = []

        # Process each frame on this page
        for frame_idx, frame in enumerate(page_template.frames):
            if parallel_mode:
                # Parallel mode: use frame-specific text and cursor
                if frame_idx not in frame_cursors or frame_cursors[frame_idx] >= frame_text_lens[frame_idx]:
                    continue  # This frame is exhausted, skip it
                frame_text = processed_frame_texts[frame_idx][frame_cursors[frame_idx]:]
                frame_cursor = frame_cursors[frame_idx]
            else:
                # Sequential mode: use main text and shared cursor
                if text_cursor >= text_len:
                    break
                frame_text = processed_text[text_cursor:]
                frame_cursor = text_cursor

            if not frame_text.strip():
                if parallel_mode:
                    frame_cursors[frame_idx] = frame_text_lens[frame_idx]  # Mark as exhausted
                continue

            # Get frame-specific language, direction, and font
            frame_lang = frame.language if frame.language else language
            frame_dir = frame.base_dir if frame.base_dir else base_dir
            frame_font = frame.font if frame.font else None

            # Create layout for this frame with frame-specific settings
            frame_layout = create_frame_layout(
                frame_text, frame.width, frame.alignment,
                frame_language=frame_lang, frame_base_dir=frame_dir,
                frame_font=frame_font
            )
            line_count = frame_layout.get_line_count()

            # Convert frame coordinates from mm to points
            frame_x_pt = frame.x * _mm_point
            frame_y_pt = frame.y * _mm_point
            frame_height_pt = frame.height * _mm_point

            # Encode frame_text to UTF-8 for byte-level indexing
            frame_utf8_text = frame_text.encode('utf-8')

            # Collect lines for this frame
            frame_lines = []
            used_height = 0.0
            consumed_chars = 0

            for i in range(line_count):
                line = frame_layout.get_line(i)
                ink_extents, log_extents = line.get_extents()
                # Convert extents from Pango units to points (avoid extents_to_pixels to prevent segfault)
                ink_x_pt = Pango.units_to_double(ink_extents.x)
                ink_y_pt = Pango.units_to_double(ink_extents.y)
                ink_width_pt = Pango.units_to_double(ink_extents.width)
                ink_height_pt = Pango.units_to_double(ink_extents.height)
                line_height_pt = Pango.units_to_double(log_extents.height)

                # Check if line fits in frame BEFORE processing it
                # If it doesn't fit, we want to stop BEFORE this line so it renders on next page
                if used_height + line_height_pt > frame_height_pt:
                    # Line doesn't fit - cursor should point to start of this line for next page
                    # line.start_index is in UTF-8 BYTES, not characters!
                    # We need to convert it to character count by decoding the bytes up to that position
                    # frame_utf8_text is the UTF-8 encoded version of frame_text
                    consumed_bytes = line.start_index
                    # Convert bytes to characters by decoding up to that byte position
                    consumed_chars = len(frame_utf8_text[:consumed_bytes].decode('utf-8'))
                    break
                
                # Get line text (indices are relative to frame_text)
                s_idx = line.start_index
                e_idx = s_idx + line.length

                # Calculate baseline position
                baseline_pt = frame_y_pt + used_height + (line_height_pt * 0.8)
                # Apply baseline position adjustment if specified (positive = up, negative = down)
                if baseline_position is not None:
                    baseline_pt -= baseline_position * _mm_point  # Subtract because positive moves up (decreases y)

                # Get line text (indices are relative to frame_text)
                # line.start_index and line.length are in UTF-8 BYTES, not characters!
                s_idx = line.start_index
                e_idx = s_idx + line.length
                line_text_bytes = frame_utf8_text[s_idx:e_idx]
                line_text = line_text_bytes.decode('utf-8')
                if not line_text.strip():
                    used_height += line_height_pt
                    # line.length is in bytes, convert to characters
                    consumed_chars += len(line_text)
                    continue

                # Calculate bounding box (using converted extents)
                line_dir = line.get_resolved_direction()
                top_pt = baseline_pt + ink_y_pt
                bottom_pt = top_pt + ink_height_pt

                if line_dir == Pango.Direction.RTL:
                    right_pt = frame_x_pt + frame.width * _mm_point - ink_x_pt
                    left_pt = right_pt - ink_width_pt
                    draw_x_pt = frame_x_pt + frame.width * _mm_point - Pango.units_to_double(log_extents.x + log_extents.width)
                elif line_dir == Pango.Direction.LTR:
                    left_pt = frame_x_pt + ink_x_pt
                    draw_x_pt = frame_x_pt + Pango.units_to_double(log_extents.x)
                    right_pt = left_pt + ink_width_pt
                else:
                    # Default to LTR
                    left_pt = frame_x_pt + ink_x_pt
                    draw_x_pt = frame_x_pt + Pango.units_to_double(log_extents.x)
                    right_pt = left_pt + ink_width_pt

                # Apply padding to coordinates
                padding_left_val = 0.0
                padding_right_val = 0.0
                padding_top_val = 0.0
                padding_bottom_val = 0.0
                
                # Calculate padding values based on parameters
                if padding_all is not None:
                    padding_left_val += padding_all
                    padding_right_val += padding_all
                    padding_top_val += padding_all
                    padding_bottom_val += padding_all
                
                if padding_horizontal is not None:
                    padding_left_val += padding_horizontal
                    padding_right_val += padding_horizontal
                
                if padding_vertical is not None:
                    padding_top_val += padding_vertical
                    padding_bottom_val += padding_vertical
                
                if padding_left is not None:
                    padding_left_val += padding_left
                
                if padding_right is not None:
                    padding_right_val += padding_right
                
                if padding_top is not None:
                    padding_top_val += padding_top
                
                if padding_bottom is not None:
                    padding_bottom_val += padding_bottom
                
                # Apply padding to coordinates (convert mm to points)
                if padding_left_val != 0.0 or padding_right_val != 0.0 or padding_top_val != 0.0 or padding_bottom_val != 0.0:
                    padding_left_pt = padding_left_val * _mm_point
                    padding_right_pt = padding_right_val * _mm_point
                    padding_top_pt = padding_top_val * _mm_point
                    padding_bottom_pt = padding_bottom_val * _mm_point
                    
                    # Apply padding to bounding box
                    left_pt -= padding_left_pt
                    right_pt += padding_right_pt
                    top_pt -= padding_top_pt
                    bottom_pt += padding_bottom_pt
                    
                    # Apply baseline padding if specified
                    if padding_baseline is not None:
                        baseline_padding_pt = padding_baseline * _mm_point
                        left_pt -= baseline_padding_pt
                        right_pt += baseline_padding_pt

                # Draw line
                context.move_to(draw_x_pt, baseline_pt)
                PangoCairo.show_layout_line(context, line)

                # Store line data for ALTO
                frame_lines.append({
                    'id': f'_{uuid.uuid4()}',
                    'text': line_text.strip(),
                    'baseline': int(round(baseline_pt / _mm_point)),
                    'top': int(math.floor(top_pt / _mm_point)),
                    'bottom': int(math.ceil(bottom_pt / _mm_point)),
                    'left': int(math.floor(left_pt / _mm_point)),
                    'right': int(math.ceil(right_pt / _mm_point))
                })

                used_height += line_height_pt
                # line.length is in UTF-8 bytes, but we need character count
                # Use the actual decoded line text length instead
                consumed_chars += len(line_text)

            # Update text cursor (parallel mode: per-frame, sequential mode: shared)
            # Only update if we actually consumed text (either rendered lines or broke early)
            if parallel_mode:
                # In parallel mode, update the frame cursor
                # consumed_chars is either:
                # - The total characters rendered (if we finished all lines)
                # - The start_index of the line that didn't fit (if we broke early due to height)
                if consumed_chars > 0 or frame_lines:
                    # Only update cursor if we've consumed text or rendered lines
                    # (consumed_chars might be 0 if we broke on the first line, but line.start_index should be > 0)
                    old_cursor = frame_cursors[frame_idx]
                    frame_cursors[frame_idx] += consumed_chars
                    # Verify cursor is within bounds
                    if frame_cursors[frame_idx] > frame_text_lens[frame_idx]:
                        # Cursor went past end - clamp it
                        logger.warning(f"Frame {frame_idx}: Cursor {frame_cursors[frame_idx]} > text_len {frame_text_lens[frame_idx]}, clamping")
                        frame_cursors[frame_idx] = frame_text_lens[frame_idx]
            else:
                text_cursor += consumed_chars

            # Store text block for this frame
            if frame_lines:
                # Calculate TextBlock coordinates from actual line positions
                # This ensures the TextBlock encompasses all lines
                min_left = min(line['left'] for line in frame_lines)
                max_right = max(line['right'] for line in frame_lines)
                min_top = min(line['top'] for line in frame_lines)
                max_bottom = max(line['bottom'] for line in frame_lines)
                
                block_x = min_left
                block_y = min_top
                block_width = max_right - min_left
                block_height = max_bottom - min_top
                
                # Determine base_dir for this frame's TextBlock
                frame_alto_base_dir = None
                if frame_dir:
                    frame_alto_base_dir = {'L': 'ltr', 'R': 'rtl'}[frame_dir]
                elif frame_lang:
                    # Auto-detect from language
                    lang_lower = frame_lang.lower()
                    if lang_lower.startswith('he') or lang_lower.startswith('ar') or lang_lower.startswith('yi'):
                        frame_alto_base_dir = 'rtl'
                
                page_text_blocks.append({
                    'id': f'_{uuid.uuid4()}',
                    'x': block_x,
                    'y': block_y,
                    'width': block_width,
                    'height': block_height,
                    'lines': frame_lines,
                    'base_dir': frame_alto_base_dir  # Per-frame direction for ALTO
                })

        # If no text blocks were created on this page, skip writing it and break
        # This prevents creating empty pages when all frames are exhausted
        if not page_text_blocks:
            pdf_surface.finish()
            # Remove the empty PDF file if it was created
            try:
                pdf_output_path.unlink()
            except FileNotFoundError:
                pass
            break

        # Determine base_dir for ALTO output
        if base_dir:
            alto_base_dir = {'L': 'ltr', 'R': 'rtl'}[base_dir]
        elif is_rtl:
            alto_base_dir = 'rtl'
        else:
            alto_base_dir = None

        # Write ALTO XML file
        with open(alto_output_path, 'w') as fo:
            fo.write(tmpl.render(pdf_path=pdf_output_path.name,
                                 language=pango_lang.to_string(),
                                 base_dir=alto_base_dir,
                                 text_blocks=page_text_blocks,
                                 page_width=paper_size[0],
                                 page_height=paper_size[1]))

        pdf_surface.finish()
