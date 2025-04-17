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

import click

from pathlib import Path
from rich.progress import Progress

from typing import Tuple, Literal, Optional

logging.captureWarnings(True)
logger = logging.getLogger('pangoline')


@click.group(chain=False)
@click.version_option()
@click.option('-v', '--verbose', default=0, count=True, show_default=True)
def cli(verbose):
    """
    Base command for repository interaction.
    """
    ctx = click.get_current_context()
    ctx.meta['verbose'] = verbose

    logger.setLevel(level=30 - min(10 * verbose, 20))


@cli.command('render')
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
@click.option('-b', '--base-dir', default=None, type=click.Choice(['L, 'R'']),
              help='Base direction for Unicode BiDi algorithm.')
@click.option('-O', '--output-dir', type=click.Path(exists=False,
                                                    dir_okay=True,
                                                    file_okay=False,
                                                    writable=True,
                                                    path_type=Path),
              show_default=True,
              default=Path('.'),
              help='Suffix for output files from batch and PDF inputs.')
@click.argument('docs', type=click.File('r'), nargs=-1)
def render(paper_size: Tuple[int, int],
           margins: Tuple[int, int, int, int],
           font: str,
           language: str,
           base_dir: Optional[Literal['L', 'R']],
           output_dir: 'PathLike',
           docs):
    """
    Retrieves a model description from the repository.
    """
    from pangoline.render import render_text
    output_dir.mkdir(exist_ok=True)
    with Progress() as progress:
        render_task = progress.add_task('Rendering', total=len(docs), visible=True)
        for doc in docs:
            progress.update(render_task, total=len(docs), advance=1, description=f'Rendering {doc.name}')
            render_text(doc.read(),
                        output_dir / Path(doc.name).name,
                        paper_size=paper_size,
                        margins=margins,
                        font=font,
                        language=language,
                        base_dir=base_dir)
