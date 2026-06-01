# PUA Thai Converter

Convert between standard Thai Unicode and Private Use Area (PUA) encoded text for custom Thai fonts.

## What This Does

Some game localization files use custom fonts that map Thai characters to PUA codepoints (U+F000–U+F8FF). These files appear as random symbols in normal text editors but display correctly when the custom font is applied. This tool lets you:

- **Encode**: Convert standard Thai text → PUA-encoded text (using a mapping table)
- **Decode**: Convert PUA-encoded text → readable Thai (revert back)
- **Extract Remaining**: Find lines that still have unmapped PUA characters, with line numbers for easy identification

## Who Is This For

- Game modders and localizers working with custom PUA fonts
- Anyone dealing with text files that use Private Use Area encoded Thai characters
- Translators who need to convert between standard Thai and PUA-encoded formats

## How PUA Encoding Works

A custom font assigns Thai character glyphs to PUA codepoints. For example:
- `ก +  ั = กั` might be encoded as `U+F000`
- `ก +  ่ = ก่` might be encoded as `U+F170`
- `ก +  ำ = กำ` might be encoded as `U+F256` (rendered as `U+F256` + `า`)

The tool uses a `mapping.json` file that defines these relationships. Each Thai character cluster (consonant + vowel + tone) maps to a specific PUA codepoint.

## Quick Start

### GUI
```bash
python pua_gui.py
```

Features:
- Select input file (.txt or .csv)
- Dropdown: Encode (Thai → PUA) or Decode (PUA → Thai)
- Auto-names output files (`filename_encode.txt`, `filename_decode.txt`)
- Extract Remaining PUA — scans a file for unmapped PUA, outputs lines with line numbers

### Command Line
```bash
# Thai → PUA
python replace_pua.py input.txt                    # outputs input_encode.txt
python replace_pua.py input.txt -p                 # preview only

# PUA → Thai  
python replace_pua.py input.txt --revert           # outputs input_decode.txt
python replace_pua.py input.txt -r -p              # preview only

# View mapping table
python replace_pua.py --dump-mapping
```

## The Mapping File (mapping.json)

The heart of the system. Two types of entries:

### Standard Mapping
```json
{
  "กั": "F000",
  "ก่": "F170",
  "กี้": "F450"
}
```
Thai cluster → single PUA hex codepoint.

### Contextual Mapping
```json
{
  "กำ": ["F256", "0E32"],
  "ก่ำ": ["F7E8", "0E32"]
}
```
Used for sara am (สระอำ) clusters where the font requires PUA codepoint + trailing `า` (U+0E32) to render correctly.

## How to Build Your Mapping

### Method 1: Grid Pattern (Fastest)
PUA codepoints in custom fonts typically follow a systematic grid:

```
Vowel Group Base + Consonant Index = PUA Codepoint
```

For example, if `สระอิ + ไม้เอก` starts at `U+F33C`:
- `กิ่` = `U+F33C + 0` = `U+F33C` (ก is consonant #0)
- `ขิ่` = `U+F33C + 1` = `U+F33D` (ข is consonant #1)
- `คิ่` = `U+F33C + 3` = `U+F33F` (ค is consonant #3)

Thai consonants order: `ก ข ฃ ค ฅ ฆ ง จ ฉ ช ซ ฌ ญ ฎ ฏ ฐ ฑ ฒ ณ ด ต ถ ท ธ น บ ป ผ ฝ พ ฟ ภ ม ย ร ล ว ศ ษ ส ห ฬ อ ฮ`

Common vowel+tone grid ranges:
| PUA Range | Pattern | Example |
|-----------|---------|---------|
| F000-F02B | Consonant + สระอะ ( ั) | กั, ขั, คั... |
| F170-F227 | Consonant + Tone marks | ก่, ก้, ก๊, ก๋... |
| F256-F283 | Consonant + สระอำ ( ำ) | กำ, ขำ, คํา... |
| F284-F33B | Consonant +  ั + Tone | กั่, กั้, กั๊, กั๋... |
| F33C-F3F3 | Consonant +  ิ + Tone | กิ่, กิ้, กิ๊, กิ๋... |
| F7E8-F89F | Consonant +  ำ + Tone | ก่ำ, ก้ำ, ก๊ำ, ก๋ำ... |

### Method 2: OCR Alignment
Place original Thai text next to PUA-encoded version, and use `align_mapping.py` to auto-extract:
```bash
python align_mapping.py --thai "สวัสดีครับ" --pua-start 0
```

### Method 3: Extract from Glyphs
Use `extract_mapping.py` to compare font glyph outlines between standard Thai and PUA codepoints.

### Method 4: Manual via GUI
1. Decode your PUA file with the GUI
2. Click "Extract Remaining PUA" to find unmapped characters
3. Read the surrounding Thai text to identify what word it is
4. Add the mapping to `mapping.json`

## Tools Included

| File | Purpose |
|------|---------|
| `pua_gui.py` | GUI application for encode/decode/extract |
| `replace_pua.py` | CLI tool for encode/decode |
| `extract_mapping.py` | Auto-extract mapping from font glyph comparison |
| `align_mapping.py` | Align Thai text with PUA text to extract mappings |
| `render_glyphs.py` | Render PUA glyphs to PNG for visual identification |

## Requirements

```bash
pip install customtkinter fonttools Pillow
```

## Example

**Input (standard Thai):**
```
สวัสดีครับ กำลังไปล่าสัตว์
```

**After encode:**
```
ส[U+F029]ส[U+F06F]ค[U+F022]บ [U+F256]า[U+F024]งไป[U+F194]า[U+F029]ต[U+F24E]
```

When viewed with the PUA font, these codepoints render as the original Thai text.

**Decode reverses this back to readable Thai.**

## Notes

- The `mapping.json` included is a template — you must fill in your font's specific mappings
- Contextual mappings (arrays) handle sara am clusters that need trailing า
- The revert function automatically cleans up leftover `า` after sara am
- Works with both TXT and CSV files
- Supports UTF-8, UTF-8-SIG, TIS-620, and CP874 encodings
