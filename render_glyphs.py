"""
Render PUA glyphs from Medium.ttf as a grid image.
Helps visually identify which PUA codepoint = which Thai word.

Usage:
  python render_glyphs.py           # render all 2208 glyphs, 40 per page
  python render_glyphs.py --start 0 --count 100  # first 100 glyphs
  python render_glyphs.py --start 500 --count 50  # glyphs 500-549
"""

import argparse
import os
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = r"C:\Users\Administrator\Desktop\PUA\Medium.ttf"
OUTPUT_DIR = r"C:\Users\Administrator\Desktop\PUA\glyph_sheets"
PUA_START = 0xF000
PUA_END = 0xF89F

COLS = 10
ROWS = 4  # 40 glyphs per sheet
CELL_W = 120
CELL_H = 80
FONT_SIZE = 48
LABEL_SIZE = 14


def render_sheet(start_idx: int, count: int):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        font_large = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        font_small = ImageFont.truetype(FONT_PATH, LABEL_SIZE)
    except OSError:
        # fallback: use default font for labels if TTF fails at small size
        font_large = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        font_small = ImageFont.load_default()

    glyphs_remaining = count
    sheet_num = 0

    for base in range(start_idx, start_idx + count, COLS * ROWS):
        batch_end = min(base + COLS * ROWS, start_idx + count)
        batch_count = batch_end - base

        img_w = COLS * CELL_W
        img_h = ROWS * CELL_H
        img = Image.new("RGB", (img_w, img_h), "white")
        draw = ImageDraw.Draw(img)

        for i in range(batch_count):
            cp = PUA_START + base + i
            if cp > PUA_END:
                break

            row = i // COLS
            col = i % COLS
            x = col * CELL_W
            y = row * CELL_H

            char = chr(cp)

            # Draw border
            draw.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], outline="#CCCCCC")

            # Draw PUA glyph
            bbox = draw.textbbox((0, 0), char, font=font_large)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(
                (x + (CELL_W - tw) / 2, y + 10),
                char,
                font=font_large,
                fill="black",
            )

            # Draw codepoint label
            label = f"U+{cp:04X}"
            draw.text((x + 4, y + CELL_H - 18), label, font=font_small, fill="#666666")

        # Grid lines
        for col in range(1, COLS):
            draw.line([(col * CELL_W, 0), (col * CELL_W, img_h)], fill="#CCCCCC", width=1)
        for row in range(1, ROWS):
            draw.line([(0, row * CELL_H), (img_w, row * CELL_H)], fill="#CCCCCC", width=1)

        out_path = os.path.join(OUTPUT_DIR, f"pua_{PUA_START+base:04X}_{PUA_START+batch_end-1:04X}.png")
        img.save(out_path)
        print(f"Saved: {out_path}  (glyphs {base}–{batch_end-1})")

        sheet_num += 1

    print(f"\nDone. {count} glyphs across {sheet_num} sheet(s) in {OUTPUT_DIR}")


def main():
    total = PUA_END - PUA_START + 1  # 2208
    parser = argparse.ArgumentParser(description="Render PUA glyph sheets")
    parser.add_argument("--start", type=int, default=0, help=f"Start index (0-{total-1})")
    parser.add_argument("--count", type=int, default=40, help="Glyphs to render")
    args = parser.parse_args()

    if args.start < 0 or args.start >= total:
        print(f"Error: start must be 0-{total-1}")
        return

    actual_count = min(args.count, total - args.start)
    print(f"Rendering {actual_count} glyphs starting at index {args.start} (U+{PUA_START+args.start:04X})")
    render_sheet(args.start, actual_count)


if __name__ == "__main__":
    main()
