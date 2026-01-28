# Talmud-like Layout Template

This template (`talmud.json`) creates a Talmud-style page layout with three columns:

## Layout Structure

**From right to left (RTL Hebrew layout):**

1. **Right Column (HPOS=150, Width=40mm)**: Tosafot commentary
   - Font: `Serif Normal 12`
   - Alignment: Justified
   - Outer margin column (20mm right margin)

2. **Center Column (HPOS=70, Width=70mm)**: Gemara (main text)
   - Font: `Serif Normal 13` (largest)
   - Alignment: Justified
   - Main text column

3. **Left Column (HPOS=20, Width=40mm)**: Rashi commentary
   - Font: `Noto Rashi Hebrew Normal 8` (Rashi script)
   - Alignment: Right-aligned
   - Inner margin column (near binding, 20mm left margin)

## Usage

### Sequential Mode (text flows through all columns)
```bash
pangoline render --template pangoline/templates/talmud.json \
  --language he --base-dir R mishna.txt
```

### Parallel Mode (each column has independent text)
```bash
pangoline render --template pangoline/templates/talmud.json \
  --parallel-texts parallel_texts_talmud.json \
  --language he --base-dir R mishna.txt
```

Where `parallel_texts_talmud.json` contains:
```json
{
  "0": "tosafot.txt",
  "1": "gemara.txt",
  "2": "rashi.txt"
}
```

## Frame Indices

- **Frame 0**: Right column (Tosafot)
- **Frame 1**: Center column (Gemara)
- **Frame 2**: Left column (Rashi)

## Fonts

- **Gemara**: `Serif Normal 13` - Main text, largest
- **Tosafot**: `Serif Normal 12` - Commentary, medium
- **Rashi**: `Noto Rashi Hebrew Normal 8` - Rashi script, smallest

## Customization

To adjust the layout, modify `pangoline/templates/talmud.json`:
- Change `x`, `y`, `width`, `height` for positioning
- Change `font` for different font sizes/styles
- Change `alignment` for text alignment
- Add more frames for additional commentaries

## Notes

- All frames are set to RTL (`base_dir: "R"`) for Hebrew text
- The layout assumes A4 paper (210x297mm)
- Margins are handled by the `y` position (25mm from top)
- Frame heights are 242mm (full page minus margins)
- All columns use justified alignment for traditional Talmud appearance

## Limitations

**Nested Columns:** Pango does not support text wrapping around other text blocks (like CSS `float`). Each frame is a rectangular region with fixed position and size. True Talmud-style nested columns where commentary wraps around the main text would require a more advanced layout engine like LaTeX or specialized typesetting software. This template provides parallel columns with fixed positions, which is the closest approximation possible with Pango.
