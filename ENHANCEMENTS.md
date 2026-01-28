# PangoLine Enhancements Summary

## Overview

This document summarizes all enhancements made to PangoLine to add multi-frame layout support while maintaining backward compatibility and production readiness.

---

## Major Enhancements

### 1. Multi-Frame Layout System

**What:** Added support for complex page layouts with multiple text regions (columns, headers, sidebars, etc.)

**Files Added:**
- `pangoline/layout.py` - Frame and PageTemplate classes

**Key Features:**
- Frame-based layout system
- Sequential text flow through frames
- Each frame becomes a separate `<TextBlock>` in ALTO XML
- Maintains perfect bounding boxes and baselines

**Backward Compatibility:** ✅ Fully compatible - default single-column template when no template specified

---

### 2. Template System

**What:** JSON-based template files define page layouts

**Files Modified:**
- `pangoline/cli.py` - Added `--template` option
- `pangoline/render.py` - Template loading and multi-frame rendering
- `pangoline/templates/alto.tmpl` - Support for multiple TextBlocks

**Files Added:**
- `pangoline/templates/two_columns.json`
- `pangoline/templates/three_columns.json`
- `pangoline/templates/header_two_columns.json`

**Usage:**
```bash
pangoline render --template pangoline/templates/two_columns.json document.txt
```

---

### 3. RTL (Right-to-Left) Support

**What:** Automatic RTL language detection and frame reversal

**Files Modified:**
- `pangoline/render.py` - RTL detection and frame reversal logic

**Features:**
- Detects RTL from `--language` flag (Hebrew, Arabic, Yiddish)
- Automatically reverses frame order for RTL column flow
- Sets `BASE_DIRECTION=rtl` in ALTO XML
- Works with `--base-dir R` flag as well

**Example:**
```bash
pangoline render --language he --template two_columns.json heb.txt
# Right column fills first, then left column
```

---

### 4. Parallel Bilingual Columns

**What:** Independent text rendering for multiple languages side-by-side

**Files Modified:**
- `pangoline/layout.py` - Extended Frame to support `text`, `language`, `base_dir`
- `pangoline/render.py` - Added parallel mode rendering logic
- `pangoline/cli.py` - Added `--parallel-texts` option
- `pangoline/templates/alto.tmpl` - Per-frame `BASE_DIRECTION` support

**Files Added:**
- `pangoline/templates/bilingual_parallel.json` - Example template

**Key Features:**
- Each column renders independently with its own text source
- Per-frame language and text direction (LTR/RTL)
- Automatic parallel mode detection
- Three methods: template `text` field, `parallel_texts` dict, or `--parallel-texts` JSON file

**Usage Examples:**

**Method 1: Text in template**
```json
{
  "frames": [
    {"x": 20, "y": 25, "width": 75, "height": 242, "language": "en", "base_dir": "L", "text": "English..."},
    {"x": 115, "y": 25, "width": 75, "height": 242, "language": "he", "base_dir": "R", "text": "Hebrew..."}
  ]
}
```

**Method 2: CLI with parallel texts file**
```bash
pangoline render --template bilingual.json --parallel-texts texts.json input.txt
```

**Backward Compatibility:** ✅ Fully compatible - parallel mode only activates when explicitly enabled

---

### 5. Alignment Options

**What:** Independent text alignment per frame

**Features:**
- `"left"` - Left-aligned text
- `"center"` - Centered text (perfect for titles)
- `"right"` - Right-aligned text
- `"justify"` - Justified text (default)

**Usage:**
```json
{
  "frames": [
    {
      "x": 20,
      "y": 15,
      "width": 170,
      "height": 25,
      "alignment": "center"  // Centered title
    }
  ]
}
```

---

## Bug Fixes

### 1. Hardcoded Margins Bug

**Problem:** Margins were hardcoded instead of using the `margins` parameter

**Fix:** Replaced hardcoded values with parameter usage
```python
# Before:
top_margin = 25 * _mm_point
bottom_margin = 30 * _mm_point
left_margin = 20 * _mm_point
right_margin = 20 * _mm_point

# After:
top_margin, bottom_margin, left_margin, right_margin = [
    m * _mm_point for m in margins
]
```

**File:** `pangoline/render.py` (lines 160-162)

---

### 2. TextBlock Coordinate Mismatch

**Problem:** TextBlock coordinates used frame dimensions, but lines were positioned differently, causing lines to appear outside TextBlocks in ALTO XML

**Fix:** Calculate TextBlock coordinates from actual line positions
```python
# Calculate TextBlock coordinates from actual line positions
min_left = min(line['left'] for line in frame_lines)
max_right = max(line['right'] for line in frame_lines)
min_top = min(line['top'] for line in frame_lines)
max_bottom = max(line['bottom'] for line in frame_lines)
```

**Files:** 
- `pangoline/render.py` (lines 394-400)
- `pangoline/rasterize.py` (lines 107-114) - Also scale TextBlock coordinates

---

### 3. Segfault in Pango Extents

**Problem:** `Pango.extents_to_pixels()` caused segfault due to reference counting issues

When calling `Pango.extents_to_pixels()` on extents returned from `line.get_extents()`, the function attempts to modify the extents object in-place. However, the extents object returned by `get_extents()` may have reference counting issues that cause a segmentation fault when modified.

**Symptoms:**
- Warning: `g_atomic_ref_count_inc: assertion 'old_value > 0' failed`
- Segmentation fault (exit code 139)
- Process crashes during rendering

**Root Cause:**
The `Pango.extents_to_pixels()` function modifies the extents rectangle in-place, converting Pango units to pixels. However, the extents objects returned from `line.get_extents()` are not always safe to modify directly due to internal reference counting in the Pango library. When the function tries to increment the reference count on an object that's already been invalidated or has a zero reference count, it triggers the assertion failure and subsequent segfault.

**Fix:** Use `Pango.units_to_double()` for manual conversion instead

Instead of modifying the extents object in-place, we manually convert each field using `Pango.units_to_double()`, which safely extracts the numeric values without modifying the original object:

```python
# Before (caused segfault):
ink_extents, log_extents = line.get_extents()
Pango.extents_to_pixels(ink_extents)  # ← Modifies object in-place, causes segfault
x = ink_extents.x
y = ink_extents.y
width = ink_extents.width
height = ink_extents.height

# After (safe):
ink_extents, log_extents = line.get_extents()
# Convert extents from Pango units to points (avoid extents_to_pixels to prevent segfault)
ink_x_pt = Pango.units_to_double(ink_extents.x)
ink_y_pt = Pango.units_to_double(ink_extents.y)
ink_width_pt = Pango.units_to_double(ink_extents.width)
ink_height_pt = Pango.units_to_double(ink_extents.height)
```

**Why This Works:**
- `Pango.units_to_double()` is a pure conversion function that doesn't modify objects
- It safely extracts numeric values from Pango unit integers
- No reference counting issues since we're not modifying the original extents object
- The conversion is mathematically equivalent (Pango units / SCALE = points)

**Files:** 
- `pangoline/render.py` (lines 328-333)
- Also fixed in original pangoline installations

---

### 4. UTF-8 Bytes vs Characters Bug in Parallel Bilingual Columns

**Problem:** In parallel bilingual column mode, text pagination stopped prematurely because Pango's `line.start_index` and `line.length` are in UTF-8 bytes, not Python string characters.

When rendering parallel bilingual columns (e.g., English-Hebrew), the Hebrew text would stop after the first page even though more text remained. The cursor was being set using byte indices, causing it to exceed the text length (measured in characters) and be incorrectly marked as exhausted.

**Symptoms:**
- Parallel bilingual columns stop rendering after first page
- Warning: `Frame X: Cursor Y > text_len Z, clamping`
- Text appears exhausted when it's not
- Particularly affects non-ASCII text (Hebrew, Arabic, etc.)

**Root Cause:**
Pango's `line.start_index` and `line.length` return values in **UTF-8 bytes**, not Python string **characters**. For ASCII text, bytes = characters, but for multi-byte characters (Hebrew, Arabic, emoji, etc.), one character can be 2-4 bytes.

When breaking due to frame height:
```python
# WRONG: line.start_index is in bytes, but frame_text_lens is in characters
consumed_chars = line.start_index  # e.g., 5588 bytes
frame_cursors[frame_idx] += consumed_chars  # Now cursor = 5588
# But text_len = 4004 characters, so cursor > text_len → marked as exhausted!
```

**Fix:** Convert byte indices to character counts

```python
# Before (wrong - uses byte indices):
if used_height + line_height_pt > frame_height_pt:
    consumed_chars = line.start_index  # Bytes, not characters!
    break
consumed_chars += line.length  # Also bytes!

# After (correct - converts to characters):
if used_height + line_height_pt > frame_height_pt:
    consumed_bytes = line.start_index
    # Convert bytes to characters by decoding
    consumed_chars = len(frame_utf8_text[:consumed_bytes].decode('utf-8'))
    break
# Use decoded line text length instead of line.length
consumed_chars += len(line_text)  # Characters, not bytes!
```

**Why This Works:**
- `frame_utf8_text` is the UTF-8 encoded version of `frame_text`
- Slicing `frame_utf8_text[:consumed_bytes]` gives us the bytes up to that position
- Decoding and taking `len()` gives us the character count
- `len(line_text)` gives us the character count of the decoded line
- Cursor now correctly tracks character positions, matching `frame_text_lens`

**Files:**
- `pangoline/render.py` (lines 403-417, 429, 467) - Parallel mode cursor tracking

**Impact:**
- Fixes parallel bilingual column pagination for all non-ASCII languages
- Ensures correct text flow across pages in parallel mode
- Critical for Hebrew, Arabic, Chinese, Japanese, and other multi-byte character languages

---

### 5. TextBlock Scaling Missing

**Problem:** During rasterization, TextLine coordinates were scaled but TextBlock coordinates were not

**Fix:** Added TextBlock coordinate scaling in rasterize.py
```python
# Scale TextBlock coordinates
for block in tree.findall('.//{*}TextBlock'):
    block_hpos = int(float(block.get('HPOS')) * coord_scale)
    block_vpos = int(float(block.get('VPOS')) * coord_scale)
    # ... etc
```

**File:** `pangoline/rasterize.py` (lines 107-114)

---

## Technical Details

### Architecture Changes

**Before:**
```
Single PangoLayout → Iterate lines → Break at page height → ALTO output
```

**After:**
```
For each page:
  For each frame in template:
    Create PangoLayout with frame width
    Fill with remaining text
    Draw lines until frame height full
    Track consumed characters
    Emit TextBlock in ALTO
  Advance to next page
```

### Key Implementation Details

1. **Text Cursor Tracking**
   - Maintains position in processed text
   - Advances by characters consumed per frame
   - Enables sequential flow through frames

2. **Frame-Based Layout**
   - Each frame gets its own PangoLayout
   - Independent width, height, alignment
   - Text flows frame-by-frame

3. **ALTO Output**
   - Each frame → one `<TextBlock>`
   - TextBlock coordinates calculated from line positions
   - Maintains backward compatibility (single TextBlock if no template)

4. **RTL Handling**
   - Detects RTL from language code
   - Reverses frame list before processing
   - Sets BASE_DIRECTION in ALTO

---

## Files Changed

### New Files
- `pangoline/layout.py` - Frame and PageTemplate classes
- `pangoline/templates/two_columns.json` - Two-column template
- `pangoline/templates/three_columns.json` - Three-column template
- `pangoline/templates/header_two_columns.json` - Header + columns template
- `TEMPLATES.md` - Comprehensive template documentation
- `ENHANCEMENTS.md` - This file

### Modified Files
- `pangoline/render.py` - Multi-frame rendering logic
- `pangoline/cli.py` - Added `--template` option
- `pangoline/rasterize.py` - TextBlock coordinate scaling
- `pangoline/templates/alto.tmpl` - Multiple TextBlock support
- `README.md` - Updated with template documentation

---

## Testing

### Verified Functionality

✅ **Single-column rendering** (backward compatibility)
✅ **Two-column layout**
✅ **Three-column layout**
✅ **Header + columns layout**
✅ **RTL language support** (Hebrew)
✅ **TextBlock coordinate accuracy**
✅ **Rasterization scaling**
✅ **Markup support** (with templates)
✅ **Alignment options** (left, center, right, justify)

### Test Files Created

- `test_example.txt` - Plain text example
- `test_with_markup.txt` - Markup example
- `test_title_example.txt` - Title + body structure
- `test_header_template.txt` - Header template example
- `test_segfault.py` - Segfault verification script

---

## Performance

**No performance degradation:**
- Frame-based rendering is as efficient as single-column
- Multiple layouts are lightweight (PangoLayouts are cheap)
- Text processing overhead is minimal

**Memory usage:**
- Similar to original (one layout per frame, but frames are smaller)
- No significant memory increase

---

## Backward Compatibility

**100% Backward Compatible:**

- ✅ Works without `--template` flag (uses default single-column)
- ✅ All existing CLI options work unchanged
- ✅ ALTO XML format compatible (just adds multiple TextBlocks)
- ✅ Rasterization works with both old and new ALTO files
- ✅ No breaking changes to API

**Migration Path:**
- Existing users: No changes needed
- New features: Opt-in via `--template` flag

---

## Known Limitations

1. **No Automatic Title Detection**
   - Text flows sequentially through frames
   - User must structure text to match frame order
   - No markdown-style `# Title` parsing

2. **Attribute Handling with Markup**
   - Pango attributes are indexed for full text
   - When text flows between frames, attributes may not be perfectly preserved
   - Markup parsing still works, but attribute ranges may need adjustment

3. **Frame Overlap**
   - Frames can overlap, but text still flows sequentially
   - Visual overlap may occur (usually avoided)

---

## Future Enhancements (Not Implemented)

Potential future improvements:

1. **Semantic Text Parsing**
   - Markdown-style title detection (`# Title`)
   - Automatic paragraph detection
   - Section headers

2. **Smart Frame Assignment**
   - Assign text to frames based on content type
   - Title → header frame, body → column frames

3. **Template Inheritance**
   - Base templates with variations
   - Template composition

4. **Visual Template Editor**
   - GUI for creating templates
   - Preview before rendering

---

## Git History

Key commits:

- `9c86230` - Backup before fixing TextBlock coordinate issue
- `0683d8b` - Fix TextBlock coordinates to match actual line positions
- `7605867` - Add RTL column flow support

All changes are committed and can be reverted if needed.

---

## Summary

**What We Achieved:**

1. ✅ Multi-column layouts (2, 3, or more columns)
2. ✅ Complex page layouts (headers, sidebars, etc.)
3. ✅ RTL language support with automatic frame reversal
4. ✅ Independent alignment per frame
5. ✅ Perfect bounding boxes and baselines
6. ✅ Full backward compatibility
7. ✅ Production-ready code

**Impact:**

- **Users**: Can now create complex document layouts
- **ATR Training**: More realistic multi-column training data
- **RTL Languages**: Proper right-to-left column flow
- **Flexibility**: Template system allows any layout

**Code Quality:**

- ✅ No linter errors
- ✅ Syntax verified
- ✅ Logic tested
- ✅ Git backups created
- ✅ Comprehensive documentation

---

### 6. Line Spacing, Baseline Position, and Padding Controls

**What:** Added fine-grained control over line spacing, baseline positioning, and bounding box padding for improved typography and ATR training data quality.

**Files Modified:**
- `pangoline/render.py` - Added line spacing, baseline position, and padding logic
- `pangoline/cli.py` - Added CLI options for all new parameters

**Key Features:**

1. **Line Spacing** (`--line-spacing FLOAT`)
   - Additional space between lines in points
   - Applied to all frame layouts
   - Useful for adjusting readability and line density
   - Example: `--line-spacing 2.0` adds 2 points between lines

2. **Baseline Position** (`--baseline-position FLOAT`)
   - Adjusts baseline position vertically in mm
   - Positive values move baseline up, negative values move it down
   - Useful for fine-tuning text positioning
   - Example: `--baseline-position 1.0` moves baseline up by 1mm

3. **Padding Options** (all in mm)
   - `--padding-all`: Applied to all sides of bounding boxes and baselines
   - `--padding-horizontal`: Applied to left and right sides
   - `--padding-vertical`: Applied to top and bottom sides
   - `--padding-left`, `--padding-right`, `--padding-top`, `--padding-bottom`: Individual side padding
   - `--padding-baseline`: Applied to left and right endpoints of baselines only
   - Padding values are additive (e.g., `--padding-all 1.0 --padding-left 2.0` = 3mm left, 1mm other sides)

**Usage Examples:**

```bash
# Add line spacing
pangoline render --line-spacing 2.0 document.txt

# Adjust baseline position
pangoline render --baseline-position 1.0 document.txt

# Add padding to all sides
pangoline render --padding-all 2.0 document.txt

# Combine padding options
pangoline render --padding-horizontal 1.0 --padding-top 2.0 document.txt

# Use with templates
pangoline render --template two_columns.json --line-spacing 1.5 --padding-all 1.0 document.txt
```

**How It Works:**

- **Line Spacing**: Applied via `layout.set_spacing()` in Pango, affecting all lines in the layout
- **Baseline Position**: Adjusts the calculated baseline Y coordinate before rendering and ALTO output
- **Padding**: Applied to bounding box coordinates (left, right, top, bottom) before storing in ALTO XML. Padding expands the bounding box outward.

**Technical Details:**

- Line spacing is in **points** (1 point = 1/72 inch)
- Baseline position and padding are in **millimeters**
- Padding is applied after coordinate calculation but before ALTO output
- All parameters are optional and default to `None` (no effect)
- Works seamlessly with multi-frame layouts

**Backward Compatibility:** ✅ Fully compatible - all parameters are optional with `None` defaults

---

## Quick Reference

**Basic Usage:**
```bash
# Single column (default)
pangoline render document.txt

# Two columns
pangoline render --template pangoline/templates/two_columns.json document.txt

# RTL (Hebrew)
pangoline render --language he --template pangoline/templates/two_columns.json heb.txt

# With markup
pangoline render --markup --template pangoline/templates/two_columns.json document.txt

# With typography controls
pangoline render --line-spacing 2.0 --baseline-position 1.0 --padding-all 1.0 document.txt
```

**Template Format:**
```json
{
  "frames": [
    {
      "x": 20,
      "y": 20,
      "width": 80,
      "height": 257,
      "alignment": "justify"
    }
  ]
}
```

**Documentation:**
- `TEMPLATES.md` - Complete template guide with examples
- `README.md` - General PangoLine documentation
- `ENHANCEMENTS.md` - This file
