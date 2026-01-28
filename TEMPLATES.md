# PangoLine Multi-Frame Layout Templates

## Table of Contents

1. [Overview](#overview)
2. [What Changed](#what-changed)
3. [Template System](#template-system)
4. [Template Format](#template-format)
5. [Creating Templates](#creating-templates)
6. [Examples](#examples)
7. [Parallel Bilingual Columns](#parallel-bilingual-columns)
8. [RTL Support](#rtl-support)
9. [Alignment Options](#alignment-options)
10. [Best Practices](#best-practices)
11. [Common Use Cases](#common-use-cases)
12. [Troubleshooting](#troubleshooting)

---

## Overview

PangoLine now supports **multi-frame layouts** through JSON template files. This allows you to create complex page layouts including:

- Multi-column documents (2, 3, or more columns)
- Centered headers with columns below
- Sidebars and complex arrangements
- Poetry layouts
- Any custom layout you can imagine

All while maintaining **perfect bounding boxes and baselines** for ATR training data.

---

## What Changed

### Enhancements Summary

1. **Multi-Frame Layout System**
   - Added `Frame` and `PageTemplate` classes (`pangoline/layout.py`)
   - Text flows sequentially through frames
   - Each frame becomes a separate `<TextBlock>` in ALTO XML

2. **Template Support**
   - JSON-based template files define page layouts
   - CLI option `--template` to specify templates
   - Backward compatible: works without templates (default single-column)

3. **RTL (Right-to-Left) Support**
   - Automatic RTL detection from `--language` flag (Hebrew, Arabic, Yiddish)
   - Frames automatically reversed for RTL column flow
   - `BASE_DIRECTION=rtl` set in ALTO XML

4. **Bug Fixes**
   - Fixed hardcoded margins bug
   - Fixed TextBlock coordinates to match actual line positions
   - Fixed segfault in Pango extents handling
   - Fixed TextBlock coordinate scaling during rasterization

5. **Alignment Options**
   - Each frame can have independent alignment: `left`, `center`, `right`, `justify`

---

## Template System

### How It Works

The template system uses **frames** - rectangular regions on a page where text can flow.

**Key Concepts:**

1. **Frame**: A rectangular region (x, y, width, height) with alignment
2. **PageTemplate**: A list of frames that define the page layout
3. **Text Flow**: Text flows sequentially through frames in order
4. **Frame Order**: First frame fills completely, then second, then third, etc.

### Text Flow Logic

```
Source Text: "Title\n\nBody text..."
Template: [Frame1 (centered), Frame2 (justified), Frame3 (justified)]

Flow:
1. "Title" → Frame1 (fills to height limit)
2. Remaining text → Frame2 (fills completely)
3. Remaining text → Frame3 (fills completely)
4. If more text → New page with same template
```

**Important**: Text flows **sequentially** through frames. Structure your source text accordingly!

---

## Template Format

### JSON Structure

Templates are JSON files with this structure:

```json
{
  "frames": [
    {
      "x": 20.0,
      "y": 20.0,
      "width": 80.0,
      "height": 257.0,
      "alignment": "justify"
    },
    {
      "x": 110.0,
      "y": 20.0,
      "width": 80.0,
      "height": 257.0,
      "alignment": "justify"
    }
  ]
}
```

### Frame Parameters

Each frame object has the following parameters:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `x` | number | X position of frame's left edge in millimeters | `20` |
| `y` | number | Y position of frame's top edge in millimeters | `20` |
| `width` | number | Width of the frame in millimeters | `80` |
| `height` | number | Height of the frame in millimeters | `257` |
| `alignment` | string | Text alignment: `"left"`, `"center"`, `"right"`, or `"justify"` | `"justify"` |
| `text` | string | (Optional) Text content for parallel bilingual columns | `"English text..."` |
| `language` | string | (Optional) Language code for this frame | `"en"`, `"he"`, `"ar"` |
| `base_dir` | string | (Optional) Text direction: `"L"` (LTR) or `"R"` (RTL) | `"R"` |
| `font` | string | (Optional) Font description for this frame (overrides global font) | `"Serif Normal 12"`, `"Sans Bold 8"` |

**Notes:**
- All coordinates are in **millimeters**
- `x=0, y=0` is the **top-left corner** of the page
- `alignment` defaults to `"justify"` if not specified
- Frames can overlap (though usually they don't)

---

## Creating Templates

### Step-by-Step Guide

1. **Determine Page Size**
   - Default: A4 (210mm × 297mm)
   - Can be changed with `--paper-size` flag

2. **Plan Your Layout**
   - Decide number of columns/regions
   - Calculate frame positions and sizes
   - Consider margins

3. **Calculate Frame Coordinates**
   ```
   Example: Two columns with 20mm margins
   - Page width: 210mm
   - Usable width: 210 - 20 (left) - 20 (right) = 170mm
   - Column width: (170 - 10 gutter) / 2 = 80mm
   - Column 1: x=20, width=80
   - Column 2: x=110 (20 + 80 + 10 gutter), width=80
   ```

4. **Create JSON File**
   - Save as `.json` file
   - Use the template format above

5. **Test Your Template**
   ```bash
   pangoline render --template your_template.json test.txt
   ```

### Template Calculator

For a page with:
- Width: `W` mm
- Height: `H` mm
- Left margin: `L` mm
- Right margin: `R` mm
- Top margin: `T` mm
- Bottom margin: `B` mm
- Number of columns: `N`
- Gutter between columns: `G` mm

**Column width:**
```
column_width = (W - L - R - (N-1) * G) / N
```

**Column positions:**
```
Column 1: x = L
Column 2: x = L + column_width + G
Column 3: x = L + 2*(column_width + G)
...
```

**Frame height:**
```
frame_height = H - T - B
```

---

## Examples

### Example 1: Two Columns

**Template:** `two_columns.json`

```json
{
  "frames": [
    {
      "x": 20,
      "y": 20,
      "width": 80,
      "height": 257,
      "alignment": "justify"
    },
    {
      "x": 110,
      "y": 20,
      "width": 80,
      "height": 257,
      "alignment": "justify"
    }
  ]
}
```

**Usage:**
```bash
pangoline render --template pangoline/templates/two_columns.json document.txt
```

**Source Text Structure:**
```
This is the first paragraph. It will fill the left column first...

More text continues here and flows into the right column...
```

**Result:**
- Text fills left column (x=20) completely
- Then flows to right column (x=110)
- Creates two `<TextBlock>` elements in ALTO XML

---

### Example 2: Centered Header + Two Columns

**Template:** `header_two_columns.json`

```json
{
  "frames": [
    {
      "x": 20,
      "y": 15,
      "width": 170,
      "height": 25,
      "alignment": "center"
    },
    {
      "x": 20,
      "y": 50,
      "width": 80,
      "height": 227,
      "alignment": "justify"
    },
    {
      "x": 110,
      "y": 50,
      "width": 80,
      "height": 227,
      "alignment": "justify"
    }
  ]
}
```

**Usage:**
```bash
pangoline render --template pangoline/templates/header_two_columns.json document.txt
```

**Source Text Structure:**
```
MY DOCUMENT TITLE

This is the body text. It starts after the title fills the header frame...

More body text flows into the columns below...
```

**Result:**
- Title fills centered header frame (Frame 1)
- Body text flows into left column (Frame 2)
- Then right column (Frame 3)
- Creates three `<TextBlock>` elements

---

### Example 3: Three Columns

**Template:** `three_columns.json`

```json
{
  "frames": [
    {
      "x": 15,
      "y": 20,
      "width": 55,
      "height": 257,
      "alignment": "justify"
    },
    {
      "x": 75,
      "y": 20,
      "width": 55,
      "height": 257,
      "alignment": "justify"
    },
    {
      "x": 135,
      "y": 20,
      "width": 55,
      "height": 257,
      "alignment": "justify"
    }
  ]
}
```

**Usage:**
```bash
pangoline render --template pangoline/templates/three_columns.json document.txt
```

**Result:**
- Text flows: Column 1 → Column 2 → Column 3 → New page

---

### Example 4: Sidebar Layout

**Template:** `sidebar.json`

```json
{
  "frames": [
    {
      "x": 20,
      "y": 20,
      "width": 50,
      "height": 257,
      "alignment": "left"
    },
    {
      "x": 80,
      "y": 20,
      "width": 110,
      "height": 257,
      "alignment": "justify"
    }
  ]
}
```

**Usage:**
```bash
pangoline render --template sidebar.json document.txt
```

**Result:**
- Left frame: Narrow sidebar (50mm wide, left-aligned)
- Right frame: Main content (110mm wide, justified)

---

### Example 5: Poetry Layout (Centered)

**Template:** `poetry.json`

```json
{
  "frames": [
    {
      "x": 50,
      "y": 20,
      "width": 110,
      "height": 257,
      "alignment": "center"
    }
  ]
}
```

**Usage:**
```bash
pangoline render --template poetry.json poem.txt
```

**Result:**
- Single centered column for poetry
- Each line centered within the frame

---

## RTL Support

### Automatic RTL Detection

When using `--language` flag with RTL languages, frames are automatically reversed:

**Supported RTL Languages:**
- Hebrew (`he`, `he-IL`)
- Arabic (`ar`, `ar-SA`, etc.)
- Yiddish (`yi`)

**Example:**
```bash
pangoline render --language he --template pangoline/templates/two_columns.json heb.txt
```

**What Happens:**
1. Language `he` detected as RTL
2. Frame order reversed: Right column first, then left
3. `BASE_DIRECTION=rtl` set in ALTO XML
4. Text flows right-to-left through columns

### Manual RTL Control

You can also explicitly set RTL:
```bash
pangoline render --base-dir R --template pangoline/templates/two_columns.json heb.txt
```

**Frame Reversal Logic:**
- **LTR**: Frames processed in template order (left → right)
- **RTL**: Frames reversed (right → left)

**Example:**
```
Template: [Frame1 (x=20), Frame2 (x=110)]
LTR: Text flows Frame1 → Frame2
RTL: Text flows Frame2 → Frame1 (reversed)
```

---

## Parallel Bilingual Columns

### Overview

**Parallel bilingual columns** allow you to render two or more independent text streams side-by-side, each flowing independently in its own column. This is perfect for:

- **Bilingual books**: English on the left, Hebrew on the right
- **Parallel translations**: Original text and translation side-by-side
- **Polyglot documents**: Multiple languages rendered independently
- **Commentary layouts**: Main text and commentary in separate columns

Unlike sequential multi-column layouts (where text flows from column 1 to column 2), parallel columns render **independently** - each column has its own text source and flows separately.

### Key Differences: Sequential vs Parallel

| Feature | Sequential Multi-Column | Parallel Bilingual Columns |
|---------|------------------------|---------------------------|
| **Text Source** | Single text file | Multiple text sources (one per column) |
| **Text Flow** | Flows sequentially: Column 1 → Column 2 → Column 3 | Each column flows independently |
| **Use Case** | Single language, multiple columns | Multiple languages, side-by-side |
| **Example** | Newspaper article in 2 columns | English-Hebrew bilingual book |

### How It Works

Parallel mode is automatically enabled when:

1. **Template frames have `text` field**: Each frame specifies its own text content
2. **`parallel_texts` parameter provided**: Dictionary mapping frame indices to text content
3. **`--parallel-texts` CLI option**: JSON file mapping frame indices to text files

Each frame renders independently with:
- Its own text source
- Its own text cursor (position tracking)
- Its own language settings
- Its own text direction (LTR/RTL)

### Method 1: Text in Template JSON

The simplest way is to include text directly in the template JSON:

```json
{
  "frames": [
    {
      "x": 20,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "en",
      "base_dir": "L",
      "text": "This is English text that will flow independently in the left column..."
    },
    {
      "x": 115,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "he",
      "base_dir": "R",
      "text": "זהו טקסט בעברית שיזרום באופן עצמאי בעמודה הימנית..."
    }
  ]
}
```

**Usage:**
```bash
pangoline render --template bilingual_template.json input.txt
```

Note: The `input.txt` file is still required but its content is ignored when frames have `text` fields.

### Method 2: Parallel Texts Dictionary (Python API)

When using the Python API, pass a dictionary mapping frame indices to text:

```python
from pangoline.render import render_text

parallel_texts = {
    0: "English text for left column...",
    1: "Hebrew text for right column..."
}

render_text(
    text="",  # Ignored when parallel_texts is provided
    output_base_path="output",
    template_path="bilingual_template.json",
    parallel_texts=parallel_texts
)
```

### Method 3: Parallel Texts JSON File (CLI) - **TWO JSON FILES REQUIRED**

For CLI usage, you need **TWO JSON files**:

1. **Template JSON file** - Defines the layout (frames, positions, languages)
2. **Parallel texts JSON file** - Maps frame indices to text file paths

**Step 1: Create Template JSON** (`bilingual_template.json`)

This file defines the page layout with frames:

```json
{
  "frames": [
    {
      "x": 20,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "en",
      "base_dir": "L"
    },
    {
      "x": 115,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "he",
      "base_dir": "R"
    }
  ]
}
```

**Step 2: Create Parallel Texts JSON** (`parallel_texts.json`)

This file maps frame indices (starting at 0) to text file paths:

```json
{
  "0": "english.txt",
  "1": "hebrew.txt"
}
```

**Important Notes:**
- Frame indices start at **0** (first frame = 0, second frame = 1, etc.)
- File paths are **relative to the parallel_texts.json file's directory**
- Absolute paths also work
- The frame index corresponds to the order of frames in the template JSON

**Step 3: Run the Command**

```bash
pangoline render \
  --template bilingual_template.json \
  --parallel-texts parallel_texts.json \
  english.txt
```

**Complete Example:**

**Template file:** `hebrew_syriac_template.json`
```json
{
  "frames": [
    {
      "x": 20,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "he",
      "base_dir": "R"
    },
    {
      "x": 115,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "syr",
      "base_dir": "R"
    }
  ]
}
```

**Parallel texts file:** `parallel_texts.json`
```json
{
  "0": "heb.txt",
  "1": "syr.txt"
}
```

**Command:**
```bash
pangoline render \
  --template hebrew_syriac_template.json \
  --parallel-texts parallel_texts.json \
  heb.txt
```

**File Path Resolution:**
- Relative paths are resolved relative to the `parallel_texts.json` file's directory
- Absolute paths work as-is
- Frame indices start at 0 (first frame = 0, second frame = 1, etc.)

### Template Parameters for Parallel Columns

Each frame can specify:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `text` | string | Text content for this frame (optional) | `"English text..."` |
| `language` | string | Language code for this frame (optional) | `"en"`, `"he"`, `"ar"`, `"syr"` |
| `base_dir` | string | Text direction: `"L"` (LTR) or `"R"` (RTL) | `"R"` for Hebrew |

**Priority Order:**
1. Frame's `text` field (highest priority)
2. `parallel_texts` dictionary/file
3. Main `text` parameter (fallback, sequential mode)

### Complete Example: English-Hebrew Bilingual

**Template: `bilingual_parallel.json`**
```json
{
  "frames": [
    {
      "x": 20,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "en",
      "base_dir": "L"
    },
    {
      "x": 115,
      "y": 25,
      "width": 75,
      "height": 242,
      "alignment": "justify",
      "language": "he",
      "base_dir": "R"
    }
  ]
}
```

**English text: `english.txt`**
```
The quick brown fox jumps over the lazy dog.
This is a sample English text for the left column.
It will flow independently from the Hebrew text.
```

**Hebrew text: `hebrew.txt`**
```
שועל חום מהיר קופץ מעל הכלב העצלן.
זהו טקסט לדוגמה בעברית לעמודה הימנית.
הוא יזרום באופן עצמאי מהטקסט באנגלית.
```

**Parallel texts mapping: `parallel_texts.json`**
```json
{
  "0": "english.txt",
  "1": "hebrew.txt"
}
```

**Command:**
```bash
pangoline render \
  --template pangoline/templates/bilingual_parallel.json \
  --parallel-texts parallel_texts.json \
  english.txt
```

**Result:**
- Left column: English text flows independently, LTR
- Right column: Hebrew text flows independently, RTL
- Each column paginates separately
- ALTO XML has separate `<TextBlock>` elements with correct `BASE_DIRECTION`

### Per-Frame Language and Direction

Each frame can have its own language and text direction:

```json
{
  "frames": [
    {
      "x": 20,
      "y": 25,
      "width": 80,
      "height": 242,
      "language": "en",
      "base_dir": "L",
      "text": "English text..."
    },
    {
      "x": 110,
      "y": 25,
      "width": 80,
      "height": 242,
      "language": "ar",
      "base_dir": "R",
      "text": "نص عربي..."
    }
  ]
}
```

**Benefits:**
- Correct language-specific rendering (ligatures, shaping, etc.)
- Proper RTL/LTR text direction per column
- Accurate ALTO XML with per-frame `BASE_DIRECTION`

### ALTO XML Output

In parallel mode, each frame becomes a separate `<TextBlock>` with its own `BASE_DIRECTION`:

```xml
<TextBlock ID="..." HPOS="20" VPOS="25" WIDTH="75" HEIGHT="242" BASE_DIRECTION="ltr">
  <!-- English lines -->
</TextBlock>
<TextBlock ID="..." HPOS="115" VPOS="25" WIDTH="75" HEIGHT="242" BASE_DIRECTION="rtl">
  <!-- Hebrew lines -->
</TextBlock>
```

### Best Practices for Parallel Columns

1. **Equal Column Heights**: Make sure both columns have the same `height` for visual alignment
2. **Consistent Margins**: Use consistent `y` positions for top alignment
3. **Language-Specific Fonts**: Consider using different fonts per language if needed
4. **Text Length**: Columns paginate independently - they may have different page counts
5. **Template Text vs Files**: Prefer `text` in template for short texts, use files for longer content
6. **Two JSON Files**: Remember you need both the template JSON and the parallel texts JSON when using CLI

### Troubleshooting Parallel Columns

**Problem**: Columns render sequentially instead of in parallel
- **Solution**: Ensure frames have `text` fields OR `parallel_texts` is provided

**Problem**: Wrong text direction in a column
- **Solution**: Set `base_dir` in the frame: `"L"` for LTR, `"R"` for RTL

**Problem**: Wrong language rendering
- **Solution**: Set `language` in the frame (e.g., `"he"` for Hebrew, `"en"` for English)

**Problem**: Text files not found
- **Solution**: Check file paths in `parallel_texts.json` - they're relative to the JSON file's directory

**Problem**: Columns have different page counts
- **Solution**: This is expected! Each column paginates independently based on its text length

**Problem**: "File not found" error for parallel texts
- **Solution**: Make sure you have **TWO JSON files**:
  1. Template JSON (with `--template`)
  2. Parallel texts JSON (with `--parallel-texts`)
  Both files must exist and be readable

---

## Alignment Options

Each frame can have independent text alignment:

### `"justify"` (Default)
- Text justified (spaced to fill width)
- Both left and right edges aligned
- Best for body text

```json
{
  "alignment": "justify"
}
```

### `"left"`
- Left-aligned, ragged right edge
- Good for sidebars, notes

```json
{
  "alignment": "left"
}
```

### `"center"`
- Centered text
- Perfect for titles, poetry, headers

```json
{
  "alignment": "center"
}
```

### `"right"`
- Right-aligned, ragged left edge
- Useful for RTL languages or special layouts

```json
{
  "alignment": "right"
}
```

### Mixed Alignment Example

```json
{
  "frames": [
    {
      "x": 20,
      "y": 15,
      "width": 170,
      "height": 25,
      "alignment": "center"    // Centered title
    },
    {
      "x": 20,
      "y": 50,
      "width": 80,
      "height": 227,
      "alignment": "left"      // Left-aligned sidebar
    },
    {
      "x": 110,
      "y": 50,
      "width": 80,
      "height": 227,
      "alignment": "justify"   // Justified main text
    }
  ]
}
```

---

## Per-Frame Font Support

Each frame can have its own font size and style, independent of the global font setting. This is essential for complex layouts like Talmud pages, academic papers with footnotes, or documents with multiple text hierarchies.

### Font Format

Fonts are specified using Pango font descriptions in the format:
```
"Family Style Size"
```

**Examples:**
- `"Serif Normal 12"` - Serif font, normal weight, 12pt
- `"Sans Bold 8"` - Sans-serif font, bold weight, 8pt
- `"Monospace Normal 10"` - Monospace font, normal weight, 10pt

### Usage

Add a `font` field to any frame in your template:

```json
{
  "frames": [
    {
      "x": 20,
      "y": 20,
      "width": 80,
      "height": 257,
      "alignment": "justify",
      "font": "Serif Normal 14"
    },
    {
      "x": 110,
      "y": 20,
      "width": 80,
      "height": 257,
      "alignment": "justify",
      "font": "Serif Normal 8"
    }
  ]
}
```

**Priority:**
- If a frame has a `font` field, it uses that font
- If a frame doesn't have a `font` field, it uses the global font (from `--font` CLI option or default)

### Example: Different Font Sizes

**Template:** `different_fonts.json`
```json
{
  "frames": [
    {
      "x": 20,
      "y": 20,
      "width": 170,
      "height": 30,
      "alignment": "center",
      "font": "Serif Bold 16"
    },
    {
      "x": 20,
      "y": 60,
      "width": 80,
      "height": 217,
      "alignment": "justify",
      "font": "Serif Normal 12"
    },
    {
      "x": 110,
      "y": 60,
      "width": 80,
      "height": 217,
      "alignment": "justify",
      "font": "Serif Normal 10"
    }
  ]
}
```

**Result:**
- Title frame: Large bold font (16pt)
- Left column: Medium font (12pt)
- Right column: Smaller font (10pt)

### Use Cases

**1. Talmud-like Layout:**
- Main text (Gemara): Large font (12-14pt)
- Rashi commentary: Smaller font (8-9pt)
- Tosafot commentary: Smaller font (8-9pt)
- Cross-references: Even smaller font (6-7pt)

**2. Academic Papers:**
- Title: Large bold font
- Abstract: Medium font
- Body text: Standard font
- Footnotes: Smaller font

**3. Multi-level Documents:**
- Headers: Large font
- Main content: Standard font
- Sidebars: Smaller font
- Notes: Small font

### Backward Compatibility

✅ **Fully backward compatible**: Templates without `font` fields work exactly as before, using the global font setting.

---

## Best Practices

### 1. Text Structure

**Match text order to frame order:**

```
✅ Good:
Title text here

Body text starts here...

❌ Bad:
Body text first...

Title at the end
```

### 2. Frame Sizing

- **Don't make frames too small**: Minimum ~40mm width for readability
- **Consider line length**: Very wide columns (150mm+) can be hard to read
- **Standard column widths**: 70-90mm for two columns on A4

### 3. Margins

- **Consistent margins**: Use same margins across frames
- **Standard margins**: 20-25mm on all sides
- **Gutter spacing**: 10-15mm between columns

### 4. Frame Heights

- **Full height**: Usually frames span full page height (minus margins)
- **Partial height**: Can create headers/footers with shorter frames
- **Overlapping**: Frames can overlap, but usually don't

### 5. Testing

- **Start simple**: Test with two columns first
- **Verify ALTO**: Check that TextBlocks contain their lines
- **Test RTL**: Verify RTL languages work correctly
- **Check rasterization**: Ensure coordinates scale properly

---

## Common Use Cases

### Use Case 1: Academic Paper

**Layout:**
- Centered title
- Two-column body text
- Footnotes area

**Template:**
```json
{
  "frames": [
    {
      "x": 20,
      "y": 15,
      "width": 170,
      "height": 20,
      "alignment": "center"
    },
    {
      "x": 20,
      "y": 45,
      "width": 80,
      "height": 220,
      "alignment": "justify"
    },
    {
      "x": 110,
      "y": 45,
      "width": 80,
      "height": 220,
      "alignment": "justify"
    },
    {
      "x": 20,
      "y": 275,
      "width": 170,
      "height": 12,
      "alignment": "left"
    }
  ]
}
```

**Source Text:**
```
Paper Title

Abstract text here...

Introduction paragraph...

Footnote text...
```

---

### Use Case 2: Newspaper Layout

**Layout:**
- Headline (full width, centered)
- Two columns below

**Template:**
```json
{
  "frames": [
    {
      "x": 15,
      "y": 10,
      "width": 180,
      "height": 30,
      "alignment": "center"
    },
    {
      "x": 15,
      "y": 50,
      "width": 85,
      "height": 237,
      "alignment": "justify"
    },
    {
      "x": 110,
      "y": 50,
      "width": 85,
      "height": 237,
      "alignment": "justify"
    }
  ]
}
```

---

### Use Case 3: Bilingual Document

**Layout:**
- Left column: Language A
- Right column: Language B

**Template:**
```json
{
  "frames": [
    {
      "x": 20,
      "y": 20,
      "width": 80,
      "height": 257,
      "alignment": "justify"
    },
    {
      "x": 110,
      "y": 20,
      "width": 80,
      "height": 257,
      "alignment": "justify"
    }
  ]
}
```

**Note**: You'd need to manually structure text or use separate files for each language.

---

### Use Case 4: Hebrew/Arabic Document

**Layout:**
- RTL two-column layout

**Usage:**
```bash
pangoline render --language he --template pangoline/templates/two_columns.json heb.txt
```

**What Happens:**
- Frames automatically reversed
- Right column fills first
- Left column fills second
- `BASE_DIRECTION=rtl` in ALTO

---

## Troubleshooting

### Problem: Lines appear outside TextBlocks

**Solution**: Fixed in recent version. TextBlock coordinates now calculated from actual line positions.

**Verify:**
```bash
# Check ALTO XML
python -c "
from lxml import etree
tree = etree.parse('output.0.xml')
blocks = tree.findall('.//{*}TextBlock')
for block in blocks:
    print(f'Block: HPOS={block.get(\"HPOS\")}, VPOS={block.get(\"VPOS\")}')
    lines = block.findall('.//{*}TextLine')
    if lines:
        hpos = int(lines[0].get('HPOS'))
        print(f'  First line HPOS: {hpos}')
"
```

---

### Problem: Parallel bilingual columns stop after first page

**Symptom:** When using parallel bilingual columns (e.g., English-Hebrew), one language stops rendering after the first page even though more text remains.

**Solution:** This was a bug where Pango's byte indices were used instead of character counts. Fixed in recent version. The issue affected non-ASCII languages (Hebrew, Arabic, Chinese, etc.) where characters are multi-byte.

**Verify Fix:**
```bash
# Check if Hebrew continues on page 1
python3 << 'EOF'
import xml.etree.ElementTree as ET
import glob

for xml_file in sorted(glob.glob('output.*.xml')):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    page_num = xml_file.split('.')[-2]
    
    hebrew_lines = 0
    for textblock in root.findall('.//{http://www.loc.gov/standards/alto/ns-v4#}TextBlock'):
        base_dir = textblock.get('BASE_DIRECTION')
        if base_dir == 'rtl':
            lines = textblock.findall('.//{http://www.loc.gov/standards/alto/ns-v4#}String')
            hebrew_lines = len(lines)
            break
    
    print(f"Page {page_num}: {hebrew_lines} Hebrew lines")
EOF
```

**If Still Occurring:** Ensure you're using the latest version with the UTF-8 bytes fix.

---

### Problem: Text doesn't flow to second column

**Possible Causes:**
1. **Not enough text**: First column not full yet
2. **Frame height too large**: Text fits in first column
3. **Template order**: Check frame order in template

**Solution:**
- Add more text to your source file
- Reduce frame heights
- Verify template JSON is valid

---

### Problem: RTL columns in wrong order

**Solution**: Use `--language` flag or `--base-dir R`:
```bash
pangoline render --language he --template two_columns.json heb.txt
```

**Verify:**
- Check `BASE_DIRECTION=rtl` in ALTO XML
- Right column should have higher HPOS than left column

---

### Problem: Centered text not centered

**Check:**
1. Frame `alignment` set to `"center"`?
2. Frame width appropriate for text?
3. Text actually in that frame?

**Example:**
```json
{
  "x": 20,
  "y": 15,
  "width": 170,    // Wide enough for title
  "height": 25,
  "alignment": "center"  // Must be "center"
}
```

---

### Problem: Template not found

**Error:** `FileNotFoundError: Template file not found`

**Solutions:**
1. Use absolute path: `--template /full/path/to/template.json`
2. Use relative path: `--template pangoline/templates/two_columns.json`
3. Check file exists: `ls -la template.json`

---

## Advanced Topics

### Frame Overlap

Frames can overlap, but text still flows sequentially:

```json
{
  "frames": [
    {
      "x": 20,
      "y": 20,
      "width": 100,
      "height": 100,
      "alignment": "justify"
    },
    {
      "x": 80,    // Overlaps with first frame
      "y": 50,
      "width": 100,
      "height": 100,
      "alignment": "justify"
    }
  ]
}
```

**Note**: Overlapping frames may cause text to overlap visually. Usually avoided.

---

### Dynamic Template Generation

You can programmatically create templates:

```python
from pangoline.layout import PageTemplate, Frame

# Create two-column template
template = PageTemplate([
    Frame(x=20, y=20, width=80, height=257, alignment="justify"),
    Frame(x=110, y=20, width=80, height=257, alignment="justify"),
])

# Save to JSON
import json
with open('custom.json', 'w') as f:
    json.dump({
        'frames': [
            {
                'x': frame.x,
                'y': frame.y,
                'width': frame.width,
                'height': frame.height,
                'alignment': frame.alignment
            }
            for frame in template.frames
        ]
    }, f, indent=2)
```

---

### Template Validation

Validate your template before use:

```python
from pangoline.layout import load_template

try:
    template = load_template('my_template.json')
    print(f"✓ Template valid: {len(template.frames)} frames")
    for i, frame in enumerate(template.frames):
        print(f"  Frame {i+1}: {frame.width}mm × {frame.height}mm at ({frame.x}, {frame.y})")
except Exception as e:
    print(f"✗ Template error: {e}")
```

---

## Summary

**Key Points:**

1. **Templates define frames** - rectangular regions where text flows
2. **Text flows sequentially** - first frame, then second, then third
3. **Each frame = one TextBlock** in ALTO XML
4. **RTL automatically reverses** frame order for right-to-left flow
5. **Alignment per frame** - independent control of text alignment
6. **Structure your text** to match frame order

**Quick Reference:**

```bash
# Basic usage
pangoline render --template template.json document.txt

# With RTL language
pangoline render --language he --template template.json heb.txt

# With markup
pangoline render --markup --template template.json document.txt

# Custom page size
pangoline render -p 216 279 --template template.json document.txt
```

**Template Location:**
- Example templates: `pangoline/templates/*.json`
- Create your own: Save as `.json` file
- Use absolute or relative paths

---

## Further Reading

- [Pango Documentation](https://docs.gtk.org/Pango/)
- [ALTO XML Specification](https://www.loc.gov/standards/alto/)
- [README.md](README.md) - General PangoLine documentation
