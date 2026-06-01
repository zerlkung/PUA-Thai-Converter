"""
Render PUA file contents using the PUA font to PNG images.
Shows the rendered Thai text (as it would appear in Sublime Text).

Usage:
  python render_file.py                    # render first 50 lines
  python render_file.py --lines 20        # first 20 lines
  python render_file.py --start 100 --lines 30  # lines 100-130
"""

import argparse
import os
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Medium.ttf")
ORI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Ori_LocalizedStrings.txt")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendered_sheets")

FONT_SIZE = 22
LINE_HEIGHT = 28
MARGIN = 20
MAX_WIDTH = 1200


def render_file(start_line: int = 0, num_lines: int = 50):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load text
    with open(ORI_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    end_line = min(start_line + num_lines, len(lines))
    selected = lines[start_line:end_line]

    print(f"Rendering lines {start_line}-{end_line-1} of {len(lines)}")

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        font_small = ImageFont.truetype(FONT_PATH, 12)
    except Exception:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        font_small = ImageFont.load_default()

    # Calculate dimensions
    max_width = max(
        font.getbbox(line.rstrip())[2] if line.strip() else 100
        for line in selected
    ) + MARGIN * 2
    max_width = min(max_width, MAX_WIDTH)

    total_height = LINE_HEIGHT * len(selected) + MARGIN * 2

    img = Image.new("RGB", (max_width, total_height), "white")
    draw = ImageDraw.Draw(img)

    y = MARGIN
    for i, line in enumerate(selected):
        line_num = start_line + i + 1
        display = line.rstrip()

        # Draw line number
        draw.text((4, y), str(line_num), font=font_small, fill="#AAAAAA")

        # Draw the text (PUA chars will render as Thai glyphs via the font)
        if display:
            draw.text((MARGIN + 30, y), display, font=font, fill="black")

        y += LINE_HEIGHT

    out_path = os.path.join(OUTPUT_DIR, f"lines_{start_line:05d}_{end_line:05d}.png")
    img.save(out_path)
    print(f"Saved: {out_path}")

    # Also write a codepoint-annotated version for mapping
    out_txt = os.path.join(OUTPUT_DIR, f"lines_{start_line:05d}_{end_line:05d}_codepoints.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        for i, line in enumerate(selected):
            line_num = start_line + i + 1
            f.write(f"[Line {line_num}]\n")
            for c in line.rstrip():
                cp = ord(c)
                if 0xF000 <= cp <= 0xF8FF:
                    f.write(f"[U+{cp:04X}]")
                else:
                    f.write(c)
            f.write("\n\n")

    print(f"Codepoints: {out_txt}")
    print(f"\nNow: look at the PNG to see the readable Thai text.")
    print(f"Type the Thai text you see for these {num_lines} lines into a file.")
    print(f"Then run: python align_mapping.py --thai-file your_text.txt --pua-start {start_line}")


def main():
    parser = argparse.ArgumentParser(description="Render PUA file with font to images")
    parser.add_argument("--start", type=int, default=0, help="Start line (0-indexed)")
    parser.add_argument("--lines", type=int, default=50, help="Number of lines to render")
    args = parser.parse_args()

    render_file(start_line=args.start, num_lines=args.lines)


if __name__ == "__main__":
    main()
