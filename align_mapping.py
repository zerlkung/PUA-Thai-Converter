"""
Align Thai source text with PUA-encoded text to extract mapping.
User provides small Thai text (re-typed from reading PUA file with font),
script aligns it with the PUA source to find character-level mappings.

Usage:
  python align_mapping.py --thai "เธอเป็นคนดี" --pua-start 100 --pua-end 150
  python align_mapping.py --thai-file thai_text.txt --pua-file Ori_LocalizedStrings.txt --pua-offset 42
"""

import argparse
import json
import os
import sys

ORI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Ori_LocalizedStrings.txt")
MAPPING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping.json")


def load_pua_file() -> str:
    with open(ORI_PATH, "r", encoding="utf-8") as f:
        return f.read()


def extract_pua_segment(text: str, start: int, end: int) -> str:
    """Extract a segment by character index."""
    return text[start:end]


def find_pua_segment(text: str, search: str) -> list:
    """Find PUA positions matching a search string (non-PUA chars only)."""
    results = []
    for i in range(len(text) - len(search) + 1):
        match = True
        for j, sc in enumerate(search):
            tc = text[i + j]
            if ord(sc) < 128 and ord(tc) < 128:  # ASCII must match exactly
                if sc != tc:
                    match = False
                    break
            elif 0x0E00 <= ord(sc) <= 0x0E7F and 0x0E00 <= ord(tc) <= 0x0E7F:
                # Thai chars — must match exactly (non-PUA Thai)
                if sc != tc:
                    match = False
                    break
            elif 0xF000 <= ord(sc) <= 0xF8FF:  # Already PUA
                if sc != tc:
                    match = False
                    break
            # Otherwise treat as wildcard
        if match:
            results.append(i)
    return results


def align_and_extract(thai_text: str, pua_text: str) -> dict:
    """
    Align Thai text with PUA text character by character.
    Thai chars that correspond to PUA codepoints get mapped.

    Strategy: walk through both strings.
    - If chars match (identical Thai codepoint) -> skip (already Thai)
    - If PUA char encountered in pua_text and Thai char in thai_text -> record mapping
    """
    mapping = {}
    ti = 0  # index in thai_text
    pi = 0  # index in pua_text

    while ti < len(thai_text) and pi < len(pua_text):
        tc = thai_text[ti]
        pc = pua_text[pi]
        tcp = ord(tc)
        pcp = ord(pc)

        # If same character (both Thai or both ASCII), advance both
        if tc == pc:
            ti += 1
            pi += 1
            continue

        # If pua_text has PUA char at this position, map it
        if 0xF000 <= pcp <= 0xF8FF:
            if tc not in mapping:
                mapping[tc] = f"{pcp:04X}"
            elif mapping[tc] != f"{pcp:04X}":
                pass  # ignore inconsistent mapping
            ti += 1
            pi += 1
            continue

        # If thai_text has Thai char but pua_text has different Thai char — skip
        # (probable alignment error)
        ti += 1
        pi += 1

    return mapping


def show_context(text: str, pos: int, window: int = 30):
    """Show context around a position in text."""
    start = max(0, pos - window)
    end = min(len(text), pos + window)
    segment = text[start:end]
    marker_pos = pos - start

    # Build safe display string
    parts = []
    for i, c in enumerate(segment):
        cp = ord(c)
        if i == marker_pos:
            parts.append(f">>[{ascii(c)}]<<")
        elif 0xF000 <= cp <= 0xF8FF:
            parts.append(f"[PUA:{cp:04X}]")
        elif cp < 128:
            parts.append(c)
        else:
            parts.append(ascii(c))
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Align Thai text with PUA text to extract mapping")
    parser.add_argument("--thai", help="Thai text that corresponds to PUA segment")
    parser.add_argument("--thai-file", help="File containing Thai text")
    parser.add_argument("--pua-file", default=ORI_PATH, help="Path to PUA-encoded file")
    parser.add_argument("--pua-offset", type=int, help="Character offset in PUA file where matching starts")
    parser.add_argument("--pua-start", type=int, help="Starting index in PUA file")
    parser.add_argument("--pua-end", type=int, help="Ending index in PUA file")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive alignment mode")
    parser.add_argument("--show", type=int, default=0, help="Show PUA text at given offset with codepoints")
    parser.add_argument("--search-thai", help="Search for a Thai text segment in PUA file")
    args = parser.parse_args()

    pua_text = load_pua_file()
    print(f"Loaded PUA file: {len(pua_text)} chars")

    # Show mode
    if args.show >= 0 and not args.thai and not args.thai_file and not args.search_thai:
        pos = args.show
        print(f"\n=== PUA file at offset {pos} ===")
        for i in range(pos, min(pos + 20, len(pua_text)), 1):
            c = pua_text[i]
            cp = ord(c)
            if cp < 128:
                label = c
            elif 0xF000 <= cp <= 0xF8FF:
                label = f"[U+{cp:04X}]"
            else:
                label = ascii(c)
        # Print 200 chars starting at pos
        segment = pua_text[pos:pos+200]
        # Write to file to preserve characters
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_segment.txt")
        with open(out, "w", encoding="utf-8") as f:
            for i, c in enumerate(segment):
                cp = ord(c)
                if 0xF000 <= cp <= 0xF8FF:
                    f.write(f"[U+{cp:04X}]")
                else:
                    f.write(c)
        print(f"Segment saved: {out}")
        return

    # Search mode
    if args.search_thai:
        query = args.search_thai
        print(f"Searching for: {ascii(query)}")
        # Search for ASCII-only parts (more reliable for localization files)
        # Try to find by surrounding non-PUA context
        # For now, search for the exact Thai chars in non-PUA positions
        matches = find_pua_segment(pua_text, query)
        print(f"Found {len(matches)} matches")
        if matches:
            for m in matches[:5]:
                print(f"  Offset {m}: {show_context(pua_text, m)}")
        return

    # Alignment mode
    thai_text = args.thai
    if args.thai_file:
        with open(args.thai_file, "r", encoding="utf-8") as f:
            thai_text = f.read()

    if not thai_text:
        print("Error: provide --thai or --thai-file for alignment")
        print("Example: python align_mapping.py --thai \"สวัสดี\" --pua-start 0")
        sys.exit(1)

    # Extract PUA segment
    if args.pua_offset is not None:
        pua_segment = pua_text[args.pua_offset : args.pua_offset + len(thai_text) * 2 + 100]
    elif args.pua_start is not None and args.pua_end is not None:
        pua_segment = pua_text[args.pua_start : args.pua_end]
    else:
        # Search for matching context
        pua_segment = pua_text[: len(thai_text) * 2 + 100]

    print(f"Thai text: {len(thai_text)} chars")
    print(f"PUA segment: {len(pua_segment)} chars")

    mapping = align_and_extract(thai_text, pua_segment)

    print(f"\n=== EXTRACTED MAPPING ({len(mapping)} entries) ===")
    for thai_char, pua_hex in sorted(mapping.items()):
        print(f"  {ascii(thai_char)} -> U+{pua_hex}")

    # Save to mapping.json
    if mapping:
        existing = {}
        if os.path.exists(MAPPING_PATH):
            with open(MAPPING_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)

        for k, v in mapping.items():
            existing[k] = v

        with open(MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        print(f"\nSaved {len(mapping)} entries to mapping.json")


if __name__ == "__main__":
    main()
