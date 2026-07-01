"""
PUA Thai Converter CLI v2.1
Scan TXT/CSV files and replace Thai text with PUA characters (or revert PUA -> Thai).

Usage:
  python replace_pua.py input.txt                      # Thai -> PUA
  python replace_pua.py input.csv                      # Thai -> PUA
  python replace_pua.py input.txt --output out.txt     # custom output path
  python replace_pua.py input.txt --preview            # preview only, no write
  python replace_pua.py input.txt --dump-mapping       # show mapping table
  python replace_pua.py input.txt --revert             # PUA -> Thai
"""

import argparse
import json
import os
import sys

MAPPING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping.json")
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Medium.ttf")


def load_mapping():
    """Load mapping.json. Returns (standard_dict, contextual_dict).
    Auto-creates empty mapping.json if not found.
    Standard: {"Thai": "F5B4"} — value is hex string.
    Contextual: {"กำ": ["F256", "0E32"]} — value is list of hex codes for multi-char output.
    """
    if not os.path.exists(MAPPING_PATH):
        default = {
            "_instructions": "Thai cluster -> PUA hex. Edit this file to add mappings.",
            "กั": "F000"
        }
        os.makedirs(os.path.dirname(MAPPING_PATH), exist_ok=True)
        with open(MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        print(f"Created new mapping.json at {MAPPING_PATH}")
    else:
        # Verify existing file isn't corrupt/truncated
        try:
            with open(MAPPING_PATH, "r", encoding="utf-8") as f:
                test = json.load(f)
            real_entries = sum(1 for k in test if not k.startswith("_"))
            if real_entries < 2:
                print(f"Warning: mapping.json has only {real_entries} entries. Consider rebuilding.")
        except (json.JSONDecodeError, IOError):
            print(f"Warning: mapping.json appears corrupt. Restore from backup if available.")

    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    standard = {}
    contextual = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        if isinstance(v, list):
            contextual[k] = v
        else:
            standard[k] = v.upper()
    return standard, contextual


def apply_mapping(text: str, standard: dict, contextual: dict) -> str:
    """Replace Thai words with PUA chars. Contextual first, longest match first."""
    result = text

    # Phase 1: Contextual mappings (multi-char output)
    for word in sorted(contextual.keys(), key=len, reverse=True):
        try:
            out = "".join(chr(int(h, 16)) for h in contextual[word])
        except (ValueError, OverflowError):
            print(f"  Warning: invalid hex in contextual '{word}', skipping")
            continue
        result = result.replace(word, out)

    # Phase 2: Standard mappings (single PUA char output)
    for word in sorted(standard.keys(), key=len, reverse=True):
        hex_code = standard[word]
        try:
            pua_char = chr(int(hex_code, 16))
        except (ValueError, OverflowError):
            print(f"  Warning: invalid hex '{hex_code}' for '{word}', skipping")
            continue
        result = result.replace(word, pua_char)

    return result


def revert_mapping(text: str, standard: dict, contextual: dict) -> str:
    """Replace PUA characters back to Thai text. Longest match first."""
    # Build reverse map: PUA codepoint -> Thai string
    reverse = {}
    for thai, hex_code in standard.items():
        try:
            cp = int(hex_code, 16)
            if cp not in reverse or len(thai) > len(reverse[cp]):
                reverse[cp] = thai
        except (ValueError, OverflowError):
            continue

    # Contextual: PUA + vowel -> Thai cluster  OR  multi-PUA sequence -> Thai word
    ctx_reverse = {}  # (pua_cp, vowel_cp) -> thai  (2-char format)
    multi_reverse = []  # (pua_sequence_str, thai) for multi-PUA entries
    for thai, hex_list in contextual.items():
        if len(hex_list) == 2:
            try:
                pua_cp = int(hex_list[0], 16)
                vowel_cp = int(hex_list[1], 16)
                ctx_reverse[(pua_cp, vowel_cp)] = thai
                continue
            except (ValueError, OverflowError):
                pass
        # Multi-PUA: build sequence string
        try:
            seq = ''.join(chr(int(h, 16)) for h in hex_list)
            multi_reverse.append((seq, thai))
        except (ValueError, OverflowError):
            continue

    result = text

    # Phase 1: Contextual revert (PUA + vowel -> Thai cluster)
    for (pua_cp, vowel_cp), thai in sorted(ctx_reverse.items(), key=lambda x: -len(x[1])):
        pua_char = chr(pua_cp)
        vowel_char = chr(vowel_cp)
        pattern = pua_char + vowel_char
        result = result.replace(pattern, thai)

    # Phase 1b: Multi-PUA revert (sequence of PUA chars -> Thai word)
    for seq, thai in sorted(multi_reverse, key=lambda x: -len(x[1])):
        result = result.replace(seq, thai)

    # Phase 2: Standard revert (PUA -> Thai)
    # Sort by Thai length descending so longer clusters match first
    for cp in sorted(reverse.keys(), key=lambda x: -len(reverse[x])):
        thai = reverse[cp]
        result = result.replace(chr(cp), thai)

    # Phase 3: Cleanup leftover า after sara am from contextual revert
    # When PUA+า is reverted, the า should be consumed; if not, strip it
    result = result.replace('ำา', 'ำ')  # ำา -> ำ

    return result


def process_file(input_path: str, output_path: str, standard: dict, contextual: dict, preview: bool):
    """Read input file, apply mapping, write output."""
    encodings_to_try = ["utf-8", "utf-8-sig", "tis-620", "cp874"]
    content = None
    used_encoding = None

    for enc in encodings_to_try:
        try:
            with open(input_path, "r", encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        print(f"Error: could not decode {input_path}. Tried: {encodings_to_try}")
        sys.exit(1)

    total_entries = len(standard) + len(contextual)
    print(f"Read: {input_path}  ({len(content)} chars, encoding={used_encoding})")
    print(f"Mapping entries: {total_entries} ({len(standard)} standard + {len(contextual)} contextual)")

    result = apply_mapping(content, standard, contextual)

    original_pua = sum(1 for c in content if 0xF000 <= ord(c) <= 0xF8FF)
    final_pua = sum(1 for c in result if 0xF000 <= ord(c) <= 0xF8FF)
    new_replacements = final_pua - original_pua

    print(f"PUA chars: {original_pua} (original) -> {final_pua} (after)  [+{new_replacements}]")

    if preview:
        preview_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_preview.txt")
        with open(preview_path, "w", encoding="utf-8") as pf:
            pf.write(result[:2000])
        print(f"\nPreview saved: {preview_path}  (first 2000 chars)")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Saved: {output_path}")


def process_revert(input_path: str, output_path: str, standard: dict, contextual: dict, preview: bool):
    """Read PUA-encoded file, revert to Thai."""
    encodings_to_try = ["utf-8", "utf-8-sig", "tis-620", "cp874"]
    content = None
    used_encoding = None

    for enc in encodings_to_try:
        try:
            with open(input_path, "r", encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        print(f"Error: could not decode {input_path}. Tried: {encodings_to_try}")
        sys.exit(1)

    total_entries = len(standard) + len(contextual)
    print(f"Read: {input_path}  ({len(content)} chars, encoding={used_encoding})")
    print(f"Mapping entries: {total_entries}")

    result = revert_mapping(content, standard, contextual)

    original_pua = sum(1 for c in content if 0xF000 <= ord(c) <= 0xF8FF)
    final_pua = sum(1 for c in result if 0xF000 <= ord(c) <= 0xF8FF)
    reverted = original_pua - final_pua

    print(f"PUA chars: {original_pua} (original) -> {final_pua} (after)  [reverted {reverted}]")

    if preview:
        preview_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_preview.txt")
        with open(preview_path, "w", encoding="utf-8") as pf:
            pf.write(result[:2000])
        print(f"\nPreview saved: {preview_path}  (first 2000 chars)")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Saved: {output_path}")


def dump_mapping(standard: dict, contextual: dict):
    """Print mapping table (writes to file to avoid terminal encoding issues)."""
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping_report.txt")
    total = len(standard) + len(contextual)
    lines = [f"=== PUA MAPPING TABLE ({total} entries) ===\n"]
    lines.append(f"{'Thai':<20} {'Hex':>12}  {'Codepoint':>10}\n")
    lines.append("-" * 50 + "\n")

    for word, hex_code in sorted(standard.items(), key=lambda x: len(x[0]), reverse=True):
        try:
            cp = int(hex_code, 16)
            pua_char = chr(cp)
            lines.append(f"{word:<20} {hex_code:>12}  U+{cp:04X} ({cp})\n")
        except (ValueError, OverflowError):
            lines.append(f"{word:<20} {hex_code:>12}  INVALID\n")

    for word, hex_list in sorted(contextual.items(), key=lambda x: len(x[0]), reverse=True):
        hex_str = "+".join(hex_list)
        lines.append(f"{word:<20} {hex_str:>12}  [contextual]\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Mapping report saved: {out_path}")

    # ASCII-safe terminal output
    print(f"\n=== PUA MAPPING TABLE ({total} entries) ===\n")
    print(f"{'Thai (escaped)':<36} {'Hex':>12}")
    print("-" * 52)
    for word, hex_code in sorted(standard.items(), key=lambda x: len(x[0]), reverse=True):
        try:
            cp = int(hex_code, 16)
            print(f"{ascii(word):<36} {hex_code:>12}  U+{cp:04X}")
        except (ValueError, OverflowError):
            print(f"{ascii(word):<36} {hex_code:>12}  INVALID")
    for word, hex_list in sorted(contextual.items(), key=lambda x: len(x[0]), reverse=True):
        hex_str = "+".join(hex_list)
        print(f"{ascii(word):<36} {hex_str:>12}  [ctx]")


def main():
    parser = argparse.ArgumentParser(description="Replace Thai text with PUA characters")
    parser.add_argument("input", nargs="?", help="Input TXT or CSV file path")
    parser.add_argument("--output", "-o", help="Output file path (default: input_pua.ext)")
    parser.add_argument("--preview", "-p", action="store_true", help="Preview only, do not write")
    parser.add_argument("--dump-mapping", "-d", action="store_true", help="Show current mapping table")
    parser.add_argument("--revert", "-r", action="store_true", help="Revert PUA -> Thai (reverse direction)")
    args = parser.parse_args()

    standard, contextual = load_mapping()
    total_entries = len(standard) + len(contextual)

    if args.dump_mapping:
        dump_mapping(standard, contextual)
        if not args.input:
            return

    if not args.input:
        parser.print_help()
        print("\nNo input file specified.")
        return

    if total_entries == 0:
        print("Error: no mapping entries found in mapping.json (only _ keys)")
        print('Add entries like:  "เรื่อง": "F5B4"')
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.input)
        suffix = "_thai" if args.revert else "_pua"
        output_path = f"{base}{suffix}{ext}"

    if args.revert:
        process_revert(args.input, output_path, standard, contextual, args.preview)
    else:
        process_file(args.input, output_path, standard, contextual, args.preview)


if __name__ == "__main__":
    main()
