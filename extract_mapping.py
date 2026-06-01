"""
Auto-extract PUA->Thai mapping by comparing glyph outlines directly.
Matches glyph contours, point counts, and bounding boxes.

Usage:
  python extract_mapping.py                    # full extraction
  python extract_mapping.py --show-unmatched   # list unmatched PUA glyphs
"""

import argparse
import json
import os
import sys

from fontTools.ttLib import TTFont

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Medium.ttf")
MAPPING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping.json")


def get_glyph_signature(font, glyph_name):
    """Return geometric signature of a glyph."""
    glyf = font["glyf"]
    if glyph_name not in glyf:
        return None

    g = glyf[glyph_name]

    # Skip compound glyphs
    if hasattr(g, "components") and g.components:
        return ("compound", tuple(c.glyphName for c in g.components))

    # Skip empty glyphs
    if not hasattr(g, "endPtsOfContours") or not g.endPtsOfContours:
        return None

    contours = list(g.endPtsOfContours)
    num_contours = len(contours)
    num_points = contours[-1] + 1 if contours else 0

    if num_points == 0:
        return None

    coords = list(g.coordinates)
    if not coords or len(coords) != num_points:
        return None

    # Round coordinates for comparison
    rounded_coords = tuple((round(x), round(y)) for x, y in coords)
    contour_tuple = tuple(contours)

    # Bounding box
    bounds = (g.xMin, g.yMin, g.xMax, g.yMax)

    return (num_contours, num_points, contour_tuple, rounded_coords, bounds)


def extract_mapping(show_unmatched: bool = False):
    print("Loading font...")
    font = TTFont(FONT_PATH)
    cmap = font.getBestCmap()
    glyf = font["glyf"]

    # Collect Thai glyph signatures
    print("Computing Thai glyph signatures...")
    thai_sigs = {}  # cp -> (glyph_name, signature)
    for cp in range(0x0E01, 0x0E60):
        name = cmap.get(cp)
        if name:
            sig = get_glyph_signature(font, name)
            if sig:
                thai_sigs[cp] = (name, sig)

    print(f"Thai glyphs with signatures: {len(thai_sigs)}")

    # Collect PUA glyph signatures
    print("Computing PUA glyph signatures...")
    pua_sigs = {}  # cp -> (glyph_name, signature)
    for cp in range(0xF000, 0xF8A0):
        name = cmap.get(cp)
        if name:
            sig = get_glyph_signature(font, name)
            if sig:
                pua_sigs[cp] = (name, sig)

    print(f"PUA glyphs with signatures: {len(pua_sigs)}")

    # Match by exact signature
    print("\nMatching...")
    matched = {}
    thai_sig_to_cp = {}
    for thai_cp, (tname, tsig) in thai_sigs.items():
        thai_sig_to_cp[tsig] = thai_cp

    for pua_cp, (pname, psig) in pua_sigs.items():
        if psig in thai_sig_to_cp:
            thai_cp = thai_sig_to_cp[psig]
            thai_char = chr(thai_cp)
            matched[pua_cp] = (thai_cp, thai_char)

    unmatched_pua = [cp for cp in pua_sigs if cp not in matched]

    print(f"Exact matches: {len(matched)}")
    print(f"Unmatched PUA: {len(unmatched_pua)}")

    # Write ASCII-safe match report to file
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matching_report.txt")
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(f"=== PUA GLYPH MATCHING REPORT ===\n\n")
        rf.write(f"Exact matches: {len(matched)}\n")
        rf.write(f"Unmatched PUA: {len(unmatched_pua)}\n\n")

        rf.write("=== MATCHED (PUA -> Thai) ===\n")
        for pua_cp, (thai_cp, thai_char) in sorted(matched.items()):
            rf.write(f"  U+{pua_cp:04X} -> U+{thai_cp:04X} ({thai_char})\n")

        if show_unmatched and unmatched_pua:
            rf.write(f"\n=== UNMATCHED PUA ({len(unmatched_pua)}) ===\n")
            for cp in sorted(unmatched_pua)[:200]:
                name, sig = pua_sigs[cp]
                sig_desc = f"contours={sig[0]}, pts={sig[1]}"
                if sig[0] == "compound":
                    sig_desc = f"compound({','.join(sig[1][:4])})"
                rf.write(f"  U+{cp:04X} ({name}) {sig_desc}\n")

    print(f"Report saved: {report_path}")

    # Also print matches to terminal (ASCII-safe)
    print("\n=== MATCHED (first 30) ===")
    for pua_cp, (thai_cp, thai_char) in sorted(matched.items())[:30]:
        # Use repr to avoid encoding issues
        print(f"  U+{pua_cp:04X} -> U+{thai_cp:04X} ({ascii(thai_char)})")

    # Save to mapping.json
    if matched:
        existing = {}
        if os.path.exists(MAPPING_PATH):
            with open(MAPPING_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)

        new_entries = {}
        for pua_cp, (thai_cp, thai_char) in sorted(matched.items()):
            new_entries[thai_char] = f"{pua_cp:04X}"

        merged = {}
        merged["_instructions"] = "Thai word -> PUA hex codepoint. Auto-extracted + manual entries."
        for k, v in new_entries.items():
            merged[k] = v
        for k, v in existing.items():
            if k.startswith("_"):
                continue
            if k not in merged:
                merged[k] = v

        with open(MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        print(f"\nSaved {len(new_entries)} mappings to mapping.json")

    return matched, unmatched_pua


def main():
    parser = argparse.ArgumentParser(description="Auto-extract PUA mapping via glyph outline comparison")
    parser.add_argument("--show-unmatched", action="store_true", help="List unmatched PUA glyphs in report")
    args = parser.parse_args()

    matched, unmatched = extract_mapping(show_unmatched=args.show_unmatched)

    if unmatched:
        print(f"\n{len(unmatched)} unmatched PUA glyphs remain.")
        print("These may be compound glyphs or typographic variants.")
        print("Use: python render_glyphs.py to review them visually.")
        print(f"See matching_report.txt for details.")


if __name__ == "__main__":
    main()
