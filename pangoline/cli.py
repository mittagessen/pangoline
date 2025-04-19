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
pangoline.cli
~~~~~~~~~~~~~

Command line driver for rendering text.
"""
import logging
import random
import os

import click

from pathlib import Path
from rich.progress import Progress
from multiprocessing import Pool
from functools import partial

from typing import Tuple, Literal, Optional

logging.captureWarnings(True)
logger = logging.getLogger('pangoline')

@click.group(chain=False)
@click.version_option()
@click.option('--workers', show_default=True, default=1, type=click.IntRange(1), help='Number of worker processes.')
def cli(workers):
    """
    Base command for the text renderer
    """
    ctx = click.get_current_context()
    ctx.meta['workers'] = workers

def _render_doc(doc, output_dir, paper_size, margins, font, language,
                base_dir):
    from pangoline.render import render_text

    with open(doc, 'r') as fp:
        render_text(text=fp.read(),
                    output_base_path=output_dir / doc,
                    paper_size=paper_size,
                    margins=margins,
                    font=font,
                    language=language,
                    base_dir=base_dir)

@cli.command('render')
@click.pass_context
@click.option('-p', '--paper-size', default=(210, 297), show_default=True,
              type=(int, int),
              help='Paper size `(width, height)` in mm.')
@click.option('-m', '--margins', default=(25, 30, 20, 20), show_default=True,
              type=(int, int, int, int),
              help='Page margins `(top, bottom, left, right)` in mm.')
@click.option('-f', '--font', default='Serif Normal 10', show_default=True,
              help='Font specification to render the text in.')
@click.option('-l', '--language', default=None,
              help='Language in country code-language format to set for '
              'language-specific rendering. If none is set, the system '
              'default will be used.')
@click.option('-b', '--base-dir', default=None, type=click.Choice(['L', 'R']),
              help='Base direction for Unicode BiDi algorithm.')
@click.option('-O', '--output-dir',
              type=click.Path(exists=False,
                              dir_okay=True,
                              file_okay=False,
                              writable=True,
                              path_type=Path),
              show_default=True,
              default=Path('.'),
              help='Base output path to place PDF and XML outputs into.')
@click.argument('docs',
                type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
                nargs=-1)
def render(ctx,
           paper_size: Tuple[int, int],
           margins: Tuple[int, int, int, int],
           font: str,
           language: str,
           base_dir: Optional[Literal['L', 'R']],
           output_dir: 'PathLike',
           docs):
    """
    Renders text files into PDF documents and creates parallel ALTO facsimiles.
    """
    output_dir.mkdir(exist_ok=True)

    with Pool(ctx.meta['workers'], maxtasksperchild=1000) as pool, Progress() as progress:
        render_task = progress.add_task('Rendering', total=len(docs), visible=True)
        for _ in pool.imap_unordered(partial(_render_doc,
                                             output_dir=output_dir,
                                             paper_size=paper_size,
                                             margins=margins,
                                             font=font,
                                             language=language,
                                             base_dir=base_dir), docs):
            progress.update(render_task, total=len(docs), advance=1)

@cli.command('rasterize')
@click.pass_context
@click.option('-d', '--dpi', default=300, show_default=True,
              help='Resolution for PDF rasterization.')
@click.option('--backgrounds', default=None, type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path),
              help='Path to folder containing background images.')
@click.option('-O', '--output-dir',
              type=click.Path(exists=False,
                              dir_okay=True,
                              file_okay=False,
                              writable=True,
                              path_type=Path),
              show_default=True,
              default=Path('.'),
              help='Base output path to place image and rewritten XML files into.')
@click.argument('docs',
                type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
                nargs=-1)
def rasterize(ctx,
              dpi: int,
              backgrounds: Optional[Path],
              output_dir: 'PathLike',
              docs):
    """
    Accepts ALTO XML files created with `pangoline render`, rasterizes PDF
    files linked in them with the chosen resolution, and rewrites the physical
    coordinates in the ALTO to the rasterized pixel coordinates.
    """
    from pangoline.rasterize import rasterize_document
    output_dir.mkdir(exist_ok=True)
    with Pool(ctx.meta['workers'], maxtasksperchild=1000) as pool, Progress() as progress:
        rasterize_task = progress.add_task('Rasterizing', total=len(docs), visible=True)
        for _ in pool.imap_unordered(partial(rasterize_document, output_base_path=output_dir, dpi=dpi, backgrounds=backgrounds), docs):
            progress.update(rasterize_task, total=len(docs), advance=1)
