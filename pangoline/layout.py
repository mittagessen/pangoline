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
pangoline.layout
~~~~~~~~~~~~~~~~

Layout frame and template definitions for multi-column and complex page layouts.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from os import PathLike


@dataclass
class Frame:
    """
    A rectangular region on a page where text can flow.

    Args:
        x: X position of the frame's left edge in mm
        y: Y position of the frame's top edge in mm
        width: Width of the frame in mm
        height: Height of the frame in mm
        alignment: Text alignment within the frame. One of: "left", "center",
                   "right", "justify". Defaults to "justify".
        text: Optional text content for this frame (for parallel bilingual columns).
              If provided, this frame will render independently with its own text.
        language: Optional language code for this frame (e.g., "he", "en", "ar").
                  If provided, overrides the global language setting for this frame.
        base_dir: Optional base direction for this frame ("L" for LTR, "R" for RTL).
                 If provided, overrides the global base_dir setting for this frame.
        font: Optional font description for this frame (e.g., "Serif Normal 12").
              If provided, overrides the global font setting for this frame.
    """
    x: float
    y: float
    width: float
    height: float
    alignment: str = "justify"
    text: Optional[str] = None
    language: Optional[str] = None
    base_dir: Optional[str] = None
    font: Optional[str] = None

    def __post_init__(self):
        """Validate alignment and base_dir values."""
        valid_alignments = {"left", "center", "right", "justify"}
        if self.alignment not in valid_alignments:
            raise ValueError(
                f"Invalid alignment '{self.alignment}'. "
                f"Must be one of: {valid_alignments}"
            )
        if self.base_dir is not None and self.base_dir not in {"L", "R"}:
            raise ValueError(
                f"Invalid base_dir '{self.base_dir}'. "
                f"Must be one of: 'L', 'R', or None"
            )


@dataclass
class PageTemplate:
    """
    A page template containing one or more frames.

    Args:
        frames: List of Frame objects defining the layout regions
    """
    frames: list[Frame]

    def __post_init__(self):
        """Validate that frames list is not empty."""
        if not self.frames:
            raise ValueError("PageTemplate must contain at least one frame")


def load_template(path: Union[str, 'PathLike']) -> PageTemplate:
    """
    Load a page template from a JSON file.

    The JSON file should have the following structure:
    {
        "frames": [
            {
                "x": 20.0,
                "y": 20.0,
                "width": 80.0,
                "height": 250.0,
                "alignment": "justify"
            },
            ...
        ]
    }

    Args:
        path: Path to the JSON template file

    Returns:
        PageTemplate object

    Raises:
        FileNotFoundError: If the template file doesn't exist
        ValueError: If the JSON structure is invalid
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "frames" not in data:
        raise ValueError("Template JSON must contain a 'frames' key")

    frames = []
    for i, fr in enumerate(data["frames"]):
        try:
            frames.append(Frame(
                x=float(fr["x"]),
                y=float(fr["y"]),
                width=float(fr["width"]),
                height=float(fr["height"]),
                alignment=fr.get("alignment", "justify"),
                text=fr.get("text"),  # Optional: for parallel bilingual columns
                language=fr.get("language"),  # Optional: per-frame language
                base_dir=fr.get("base_dir"),  # Optional: per-frame direction
                font=fr.get("font"),  # Optional: per-frame font
            ))
        except KeyError as e:
            raise ValueError(
                f"Frame {i} missing required field: {e.args[0]}"
            ) from e
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Frame {i} has invalid value: {e}"
            ) from e

    return PageTemplate(frames)


def default_single_column_template(
    page_width_mm: float,
    page_height_mm: float,
    margin_left_mm: float,
    margin_top_mm: float,
    margin_right_mm: float,
    margin_bottom_mm: float,
) -> PageTemplate:
    """
    Create a default single-column template matching the traditional pangoline
    layout.

    Args:
        page_width_mm: Page width in mm
        page_height_mm: Page height in mm
        margin_left_mm: Left margin in mm
        margin_top_mm: Top margin in mm
        margin_right_mm: Right margin in mm
        margin_bottom_mm: Bottom margin in mm

    Returns:
        PageTemplate with a single justified frame
    """
    width = page_width_mm - margin_left_mm - margin_right_mm
    height = page_height_mm - margin_top_mm - margin_bottom_mm
    return PageTemplate([
        Frame(
            x=margin_left_mm,
            y=margin_top_mm,
            width=width,
            height=height,
            alignment="justify",
        )
    ])
