"""
PUA Thai Converter GUI
- Encode: Thai -> PUA
- Decode: PUA -> Thai
- Extract remaining PUA lines with line numbers
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
from collections import Counter
from replace_pua import load_mapping, apply_mapping, revert_mapping

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
# Force standard Windows font to avoid PUA font interference
ctk.set_widget_scaling(1.0)
ctk.set_window_scaling(1.0)

MAPPING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping.json")

# Clear any font cache and force Segoe UI
FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"

def _font(size=13, weight=None, mono=False):
    family = FONT_MONO if mono else FONT_FAMILY
    kw = dict(family=family, size=size)
    if weight: kw['weight'] = weight
    return ctk.CTkFont(**kw)


T = {
    'en': {
        'title': 'PUA Thai Converter v2.1',
        'input_file': 'Input File',
        'browse': 'Browse',
        'output_file': 'Output File (auto-named)',
        'save_as': 'Save As',
        'direction': 'Direction:',
        'encode': 'Thai -> PUA (Encode)',
        'decode': 'PUA -> Thai (Decode)',
        'convert_encode': '▶ Encode',
        'convert_decode': '▶ Decode',
        'mapping_prefix': 'Mapping:',
        'refresh': '↻',
        'extract': 'Extract Remaining PUA',
        'mapping_tools': 'Mapping Tools:',
        'add_btn': '+ Add',
        'bulk_btn': 'Bulk Import',
        'gfx_btn': 'Create PUA Chars for .gfx',
        'status_ready': '● Ready',
        'status_complete': '● Complete',
        'status_error': '● Error',
        'status_extracting': '● Extracting...',
        'status_converting': '● Converting...',
        'placeholder_input': 'Select .txt or .csv file...',
        'placeholder_output': 'Auto-generated...',
        'lang_toggle': 'TH',
    },
    'th': {
        'title': 'PUA Thai Converter v2.1',
        'input_file': 'ไฟล์นำเข้า',
        'browse': 'เลือกไฟล์',
        'output_file': 'ไฟล์ปลายทาง (ตั้งชื่ออัตโนมัติ)',
        'save_as': 'บันทึกเป็น',
        'direction': 'โหมด:',
        'encode': 'ไทย -> PUA (เข้ารหัส)',
        'decode': 'PUA -> ไทย (ถอดรหัส)',
        'convert_encode': '▶ เข้ารหัส',
        'convert_decode': '▶ ถอดรหัส',
        'mapping_prefix': 'Mapping:',
        'refresh': '↻',
        'extract': 'ค้นหา PUA ที่เหลือ',
        'mapping_tools': 'เครื่องมือ Mapping:',
        'add_btn': '+ เพิ่ม',
        'bulk_btn': 'นำเข้าทีละมาก',
        'gfx_btn': 'สร้าง PUA Chars สำหรับ .gfx',
        'status_ready': '● พร้อม',
        'status_complete': '● เสร็จสิ้น',
        'status_error': '● ผิดพลาด',
        'status_extracting': '● กำลังค้นหา...',
        'status_converting': '● กำลังแปลง...',
        'placeholder_input': 'เลือกไฟล์ .txt หรือ .csv...',
        'placeholder_output': 'ตั้งชื่ออัตโนมัติ...',
        'lang_toggle': 'EN',
    }
}

class PUAConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.lang = 'en'
        self.title(T[self.lang]['title'])
        self.geometry("1050x750")
        self.minsize(900, 650)

        self._widgets = {}  # track widgets for translation
        self.standard, self.contextual = load_mapping()
        self.setup_ui()
        self.refresh_mapping_info()

    def t(self, key):
        return T[self.lang].get(key, key)

    def toggle_language(self):
        self.lang = 'th' if self.lang == 'en' else 'en'
        self.title(self.t('title'))
        self.lang_btn.configure(text=self.t('lang_toggle'))
        # Update all tracked labels
        for name, (widget, key, prefix) in self._widgets.items():
            text = self.t(key)
            if prefix == 'mapping':
                total = len(self.standard) + len(self.contextual)
                text = f'{self.t("mapping_prefix")} {total} entries' if self.lang == 'en' else f'{self.t("mapping_prefix")} {total} รายการ'
            widget.configure(text=text)
        # Update dropdown values
        self.dir_dropdown.configure(values=[self.t('encode'), self.t('decode')])
        if 'Decode' in self.direction_var.get() or 'ถอด' in self.direction_var.get():
            self.direction_var.set(self.t('decode'))
        else:
            self.direction_var.set(self.t('encode'))
        # Update placeholder text
        self.input_entry.configure(placeholder_text=self.t('placeholder_input'))
        self.output_entry.configure(placeholder_text=self.t('placeholder_output'))
        self.status_label.configure(text=self.t('status_ready'))

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # === Row 0: File Selection ===
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        self._widgets['lbl_input'] = (ctk.CTkLabel(file_frame, text=self.t('input_file'),
                           font=_font(size=14, weight="bold")), 'input_file', 'label')
        self._widgets['lbl_input'][0].grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        self.input_var = tk.StringVar()
        self.input_entry = ctk.CTkEntry(file_frame, textvariable=self.input_var,
                     placeholder_text=self.t('placeholder_input'))
        self.input_entry.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew", columnspan=2)

        self._widgets['btn_browse'] = (ctk.CTkButton(file_frame, text=self.t('browse'), width=80,
                      command=self.browse_input), 'browse', 'button')
        self._widgets['btn_browse'][0].grid(row=1, column=2, padx=5, pady=(0, 5))
        ctk.CTkButton(file_frame, text="📁 Folder", width=80,
                      command=self.browse_folder).grid(row=1, column=3, padx=5, pady=(0, 5))

        self._widgets['lbl_output'] = (ctk.CTkLabel(file_frame, text=self.t('output_file'),
                     font=_font(size=14, weight="bold")), 'output_file', 'label')
        self._widgets['lbl_output'][0].grid(row=2, column=0, padx=10, pady=(5, 2), sticky="w")

        self.output_var = tk.StringVar()
        self.output_entry = ctk.CTkEntry(file_frame, textvariable=self.output_var,
                     placeholder_text=self.t('placeholder_output'))
        self.output_entry.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew", columnspan=2)

        self._widgets['btn_saveas'] = (ctk.CTkButton(file_frame, text=self.t('save_as'), width=80,
                      command=self.browse_output), 'save_as', 'button')
        self._widgets['btn_saveas'][0].grid(row=3, column=2, padx=5, pady=(0, 10))

        # === Row 1: Conversion Controls ===
        cvt_frame = ctk.CTkFrame(self)
        cvt_frame.grid(row=1, column=0, padx=15, pady=(5, 2), sticky="ew")

        self._widgets['lbl_dir'] = (ctk.CTkLabel(cvt_frame, text=self.t('direction'),
                     font=_font(size=14)), 'direction', 'label')
        self._widgets['lbl_dir'][0].pack(side="left", padx=(10, 5), pady=8)

        self.direction_var = ctk.StringVar(value=self.t('encode'))
        self.dir_dropdown = ctk.CTkOptionMenu(
            cvt_frame, variable=self.direction_var, width=190,
            values=[self.t('encode'), self.t('decode')],
            command=self.on_direction_change)
        self.dir_dropdown.pack(side="left", padx=5, pady=8)

        self.convert_btn = ctk.CTkButton(cvt_frame, text=self.t('convert_encode'), width=100,
                                         fg_color="#1565C0", font=_font(size=14, weight="bold"),
                                         command=self.run_conversion)
        self.convert_btn.pack(side="left", padx=10, pady=8)

        self.icons_var = tk.BooleanVar(value=False)
        self.icons_cb = ctk.CTkCheckBox(cvt_frame, text="Icons Mode (F999+)", variable=self.icons_var,
                                        font=_font(size=12))
        self.icons_cb.pack(side="left", padx=10, pady=8)

        ctk.CTkLabel(cvt_frame, text="│", text_color="#555", font=_font(size=20)).pack(
            side="left", padx=10, pady=8)

        self.mapping_label = ctk.CTkLabel(cvt_frame, text="",
                                          font=_font(size=13, weight="bold"))
        self.mapping_label.pack(side="left", padx=5, pady=8)
        self._widgets['mapping'] = (self.mapping_label, 'mapping_prefix', 'mapping')

        self.refresh_btn = ctk.CTkButton(cvt_frame, text=self.t('refresh'), width=40, fg_color="#37474F",
                                         command=self.refresh_mapping)
        self.refresh_btn.pack(side="left", padx=2, pady=8)

        self._widgets['btn_extract'] = (ctk.CTkButton(cvt_frame, text=self.t('extract'), width=170,
                                         fg_color="#6A1B9A", command=self.extract_remaining_pua), 'extract', 'button')
        self._widgets['btn_extract'][0].pack(side="right", padx=5, pady=8)

        # === Row 2: Mapping Tools ===
        tool_frame = ctk.CTkFrame(self)
        tool_frame.grid(row=2, column=0, padx=15, pady=(2, 5), sticky="ew")

        self._widgets['lbl_tools'] = (ctk.CTkLabel(tool_frame, text=self.t('mapping_tools'),
                     font=_font(size=13)), 'mapping_tools', 'label')
        self._widgets['lbl_tools'][0].pack(side="left", padx=(10, 5), pady=6)

        self._widgets['btn_add'] = (ctk.CTkButton(tool_frame, text=self.t('add_btn'), width=70, fg_color="#2E7D32",
                                     command=self.open_mapping_editor), 'add_btn', 'button')
        self._widgets['btn_add'][0].pack(side="left", padx=3, pady=6)

        self._widgets['btn_bulk'] = (ctk.CTkButton(tool_frame, text=self.t('bulk_btn'), width=100,
                                      fg_color="#00838F", command=self.open_bulk_import), 'bulk_btn', 'button')
        self._widgets['btn_bulk'][0].pack(side="left", padx=3, pady=6)

        self._widgets['btn_gfx'] = (ctk.CTkButton(tool_frame, text=self.t('gfx_btn'), width=180,
                                     fg_color="#4A148C", command=self.create_gfx_chars), 'gfx_btn', 'button')
        self._widgets['btn_gfx'][0].pack(side="left", padx=3, pady=6)

        # === Row 3: Log ===
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, padx=15, pady=(5, 10), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(log_frame, state="disabled", fg_color="black",
                                      text_color="lightgreen",
                                      font=_font(size=12, mono=True))
        self.log_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # === Row 4: Status ===
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(status_frame, text=self.t('status_ready'), text_color="#10B981",
                                         font=_font(size=13))
        self.status_label.pack(side="left")

        self.lang_btn = ctk.CTkButton(status_frame, text=self.t('lang_toggle'), width=45, height=28,
                                      fg_color="#37474F", font=_font(size=12),
                                      command=self.toggle_language)
        self.lang_btn.pack(side="right", padx=5)

        self.progress_bar = ctk.CTkProgressBar(status_frame, width=250)
        self.progress_bar.pack(side="right", padx=10)
        self.progress_bar.set(0)

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.update()

    def set_status(self, text, color="#6B7280"):
        self.status_label.configure(text=text, text_color=color)
        self.update()

    def refresh_mapping_info(self):
        self.standard, self.contextual = load_mapping()
        total = len(self.standard) + len(self.contextual)
        if self.lang == 'en':
            self.mapping_label.configure(text=f"Mapping: {total} entries")
        else:
            self.mapping_label.configure(text=f"Mapping: {total} รายการ")
        if total <= 1:
            self.log("Note: mapping.json has few entries. Edit it to add your font's PUA mappings.")

    def refresh_mapping(self):
        """Refresh button handler — reload mapping.json and update display."""
        self.refresh_mapping_info()
        self.log(f"Mapping reloaded: {len(self.standard) + len(self.contextual)} entries")

    def create_gfx_chars(self):
        """Generate PUA chars from mapping.json for .gfx font Add Font field."""
        self.refresh_mapping_info()
        pua = set()
        for thai, hex_code in self.standard.items():
            try: pua.add(chr(int(hex_code, 16)))
            except: pass
        for thai, hex_list in self.contextual.items():
            try:
                cp = int(hex_list[0], 16)
                if 0xF000 <= cp <= 0xF8FF: pua.add(chr(cp))
            except: pass
        chars = sorted(pua, key=ord)
        out_path = filedialog.asksaveasfilename(
            initialfile="_unique_pua_chars.txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if not out_path: return
        with open(out_path, 'w', encoding='utf-8') as f:
            for i, c in enumerate(chars):
                f.write(c)
                if (i + 1) % 20 == 0: f.write('\n')
        self.log(f"Created: {os.path.basename(out_path)} ({len(chars)} PUA chars)")
        self.set_status(f"Saved {len(chars)} PUA chars", "#10B981")
        messagebox.showinfo("Done", f"Saved {len(chars)} PUA characters to:\n{out_path}\n\nPaste these into the Add Font field for .gfx fonts.")

    def open_mapping_editor(self):
        """Open a small window to add a single mapping entry."""
        editor = ctk.CTkToplevel(self)
        editor.title("Add Mapping")
        editor.geometry("400x250")
        editor.resizable(False, False)
        editor.grab_set()  # modal

        ctk.CTkLabel(editor, text="Add New Mapping Entry",
                     font=_font(size=16, weight="bold")).pack(pady=(15, 10))

        # Thai input
        thai_frame = ctk.CTkFrame(editor, fg_color="transparent")
        thai_frame.pack(pady=5)
        ctk.CTkLabel(thai_frame, text="Thai:", width=60).pack(side="left", padx=5)
        thai_var = tk.StringVar()
        ctk.CTkEntry(thai_frame, textvariable=thai_var, width=200,
                     placeholder_text="e.g. กั่").pack(side="left")

        # PUA input
        pua_frame = ctk.CTkFrame(editor, fg_color="transparent")
        pua_frame.pack(pady=5)
        ctk.CTkLabel(pua_frame, text="PUA:", width=60).pack(side="left", padx=5)
        pua_var = tk.StringVar()
        ctk.CTkEntry(pua_frame, textvariable=pua_var, width=200,
                     placeholder_text="e.g. F284").pack(side="left")

        # Contextual checkbox
        ctx_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(editor, text="Contextual (สระอำ — adds trailing า)",
                        variable=ctx_var).pack(pady=5)

        # Status label
        status_var = tk.StringVar()
        ctk.CTkLabel(editor, textvariable=status_var, text_color="#6B7280").pack(pady=5)

        def save_mapping():
            thai = thai_var.get().strip()
            pua = pua_var.get().strip().upper()

            if not thai:
                status_var.set("Please enter Thai cluster")
                return
            if not pua or not all(c in '0123456789ABCDEF' for c in pua):
                status_var.set("Invalid PUA hex (e.g. F284)")
                return

            # Backup existing mapping.json
            import shutil
            mapping_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping.json")
            backup_path = mapping_path + ".bak"
            if os.path.exists(mapping_path):
                shutil.copy(mapping_path, backup_path)

            # Load current
            self.refresh_mapping_info()

            if ctx_var.get():
                if thai in self.standard: del self.standard[thai]
                self.contextual[thai] = [pua, '0E32']
            else:
                for k in list(self.standard.keys()):
                    if self.standard[k] == pua: del self.standard[k]
                if thai in self.standard: del self.standard[thai]
                if thai in self.contextual: del self.contextual[thai]
                self.standard[thai] = pua

            # Save
            total = len(self.standard) + len(self.contextual)
            clean = {'_instructions': f'{len(self.standard)} std + {len(self.contextual)} ctx.'}
            for k, v in sorted(self.standard.items(), key=lambda x: (len(x[0]), x[0])):
                clean[k] = v
            for k, v in sorted(self.contextual.items(), key=lambda x: (len(x[0]), x[0])):
                clean[k] = v
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(clean, f, ensure_ascii=False, indent=2)

            self.mapping_label.configure(text=f"Mapping: {total} entries")
            self.log(f"Added: {thai} -> {pua}{' (ctx)' if ctx_var.get() else ''} | Total: {total} | Backup: mapping.json.bak")
            status_var.set(f"Saved! {thai} -> {pua}")
            editor.after(800, editor.destroy)

        ctk.CTkButton(editor, text="Save", width=100, fg_color="#2E7D32",
                      command=save_mapping).pack(pady=15)

    def open_bulk_import(self):
        """Open a window to paste bulk mappings and batch-import them.
        If Thai cluster already exists, it updates the PUA. If PUA already used, it replaces."""
        bulk = ctk.CTkToplevel(self)
        bulk.title("Bulk Import Mappings")
        bulk.geometry("700x650")
        bulk.grab_set()

        ctk.CTkLabel(bulk, text="Paste mappings below (one per line)",
                     font=_font(size=16, weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(bulk, text="Existing PUA will be replaced. Existing Thai gets updated.",
                     text_color="#F59E0B", font=_font(size=12)).pack()

        # Textbox with placeholder
        placeholder = "U+F2A8: ลั่\nU+F15A: น็\nF733 = คู่\nลั้ = F2D6"
        text_box = ctk.CTkTextbox(bulk, width=650, height=350,
                                  font=_font(size=13, mono=True),
                                  fg_color="#1a1a1a")
        text_box.pack(padx=15, pady=10)
        # Insert placeholder
        text_box.insert("1.0", placeholder)
        text_box.configure(text_color="#555555")

        # Clear placeholder on focus
        placeholder_active = [True]
        def on_focus(event=None):
            if placeholder_active[0]:
                text_box.delete("1.0", "end")
                text_box.configure(text_color="lightgreen")
                placeholder_active[0] = False
        text_box.bind("<FocusIn>", on_focus)
        text_box.bind("<Button-1>", on_focus)
        # Right-click paste
        text_box.bind("<Button-3>", lambda e: text_box.event_generate("<<Paste>>"))
        # Ctrl+V
        text_box.bind("<Control-v>", lambda e: text_box.event_generate("<<Paste>>"))

        def load_missing_file():
            filename = filedialog.askopenfilename(
                title="Select _missing.txt file",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not filename: return
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                return

            import re
            found = set()
            for m in re.finditer(r'U\+([0-9A-Fa-f]{4})', content):
                pua = m.group(1).upper()
                found.add(pua)

            # Check which are not yet mapped
            self.refresh_mapping_info()
            mapped_pua = set(v.upper() for v in self.standard.values())
            mapped_pua |= set(v[0].upper() for v in self.contextual.values())
            unmapped = sorted(p for p in found if p not in mapped_pua)

            if not unmapped:
                status_var.set("All PUA in this file are already mapped!")
                return

            # Clear and fill text area
            text_box.delete("1.0", "end")
            text_box.configure(text_color="lightgreen")
            placeholder_active[0] = False

            lines = [f'U+{p}: ' for p in unmapped]
            text_box.insert("1.0", '\n'.join(lines))
            status_var.set(f"Loaded {len(unmapped)} unmapped PUA (from {len(found)} total)")

        btn_frame = ctk.CTkFrame(bulk, fg_color="transparent")
        btn_frame.pack(pady=2)
        ctk.CTkButton(btn_frame, text="Load _missing.txt", width=150,
                      fg_color="#37474F", command=load_missing_file).pack(side="left", padx=5)

        status_var = tk.StringVar(value="")
        ctk.CTkLabel(bulk, textvariable=status_var, text_color="#6B7280").pack()

        def parse_and_save():
            import shutil, re
            raw_text = text_box.get("1.0", "end-1c")
            # Skip placeholder text
            if placeholder_active[0]:
                status_var.set("Paste your mappings first, then click Import")
                return
            lines = raw_text.strip().split('\n')

            # Parse each line
            parsed = []
            for line in lines:
                line = line.strip()
                if not line: continue
                # Try patterns: U+F2A8: ลั่, F2A8 = ลั่, ลั่ = F2A8, Mod = F999 F99A (multi-PUA)
                pua = thai = None
                # Pattern 0: Thai = FXXX FXXX ... (multi-PUA, space-separated hex)
                m = re.match(r'(.+?)\s*[=:]\s*((?:U?\+?[0-9A-Fa-f]{4}\s*)+)', line)
                if m:
                    thai = m.group(1).strip()
                    puas = re.findall(r'U?\+?([0-9A-Fa-f]{4})', m.group(2))
                    if len(puas) > 1 and thai:
                        parsed.append((thai, puas))  # list of hex strings
                        continue
                # Pattern 1: U+FXXX: Thai
                m = re.match(r'U\+([0-9A-Fa-f]{4}):\s*(.+)', line)
                if m: pua, thai = m.group(1).upper(), m.group(2).strip()
                # Pattern 2: FXXX = Thai or FXXX: Thai
                if not pua:
                    m = re.match(r'([0-9A-Fa-f]{4})\s*[=:]\s*(.+)', line)
                    if m: pua, thai = m.group(1).upper(), m.group(2).strip()
                # Pattern 3: Thai = FXXX or Thai: FXXX
                if not pua:
                    m = re.match(r'(.+)\s*[=:]\s*U?\+?([0-9A-Fa-f]{4})', line)
                    if m: thai, pua = m.group(1).strip(), m.group(2).upper()

                if pua and thai and len(thai) <= 5:
                    parsed.append((thai, pua))

            if not parsed:
                status_var.set("No valid mappings found. Use format: U+F2A8: ลั่")
                return

            # Backup
            mapping_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping.json")
            backup_path = mapping_path + ".bak"
            if os.path.exists(mapping_path):
                shutil.copy(mapping_path, backup_path)

            # Load current
            self.refresh_mapping_info()

            added = 0
            for thai, pua in parsed:
                # Multi-PUA: pua is a list of hex strings
                if isinstance(pua, list):
                    if thai in self.standard: del self.standard[thai]
                    if thai in self.contextual: del self.contextual[thai]
                    self.contextual[thai] = pua
                    added += 1
                    continue
                # Auto-detect contextual: if thai has sara am ( ำ)
                is_ctx = chr(0x0E33) in thai
                if is_ctx:
                    if thai in self.standard: del self.standard[thai]
                    self.contextual[thai] = [pua, '0E32']
                else:
                    # Remove any standard entry pointing to this PUA (overwrite)
                    for k in list(self.standard.keys()):
                        if self.standard[k] == pua: del self.standard[k]
                    # Also remove if Thai exists with different PUA (update)
                    if thai in self.standard: del self.standard[thai]
                    if thai in self.contextual: del self.contextual[thai]
                    self.standard[thai] = pua
                added += 1

            # Save
            total = len(self.standard) + len(self.contextual)
            clean = {'_instructions': f'{len(self.standard)} std + {len(self.contextual)} ctx.'}
            for k, v in sorted(self.standard.items(), key=lambda x: (len(x[0]), x[0])):
                clean[k] = v
            for k, v in sorted(self.contextual.items(), key=lambda x: (len(x[0]), x[0])):
                clean[k] = v
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(clean, f, ensure_ascii=False, indent=2)

            self.mapping_label.configure(text=f"Mapping: {total} entries")
            self.log(f"Bulk import: {added} entries | Total: {total} | Backup: mapping.json.bak")
            status_var.set(f"Imported {added} mappings! Total: {total}")
            bulk.after(1000, bulk.destroy)

        ctk.CTkButton(bulk, text="Import All", width=150, fg_color="#2E7D32",
                      font=_font(size=14, weight="bold"),
                      command=parse_and_save).pack(pady=10)

    def on_direction_change(self, choice):
        if "Decode" in choice or "ถอด" in choice:
            self.convert_btn.configure(text=self.t('convert_decode'), fg_color="#6A1B9A")
        else:
            self.convert_btn.configure(text=self.t('convert_encode'), fg_color="#1565C0")
        self.auto_output_name()

    def auto_output_name(self):
        input_path = self.input_var.get()
        if not input_path:
            return
        base, ext = os.path.splitext(input_path)
        suffix = "_decode" if ("Decode" in self.direction_var.get() or "ถอด" in self.direction_var.get()) else "_encode"
        self.output_var.set(f"{base}{suffix}{ext}")

    def browse_input(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.input_var.set(filename)
            self.auto_output_name()

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select folder to batch process")
        if not folder:
            return
        self.refresh_mapping_info()
        is_decode = "Decode" in self.direction_var.get() or "ถอด" in self.direction_var.get()
        suffix = "_decode" if is_decode else "_encode"
        exts = (".txt", ".csv", ".json")
        files = [f for f in os.listdir(folder) if f.lower().endswith(exts)]
        if not files:
            messagebox.showinfo("No files", "No .txt/.csv/.json files found.")
            return
        dir_label = "Decode (PUA→Thai)" if is_decode else "Encode (Thai→PUA)"
        if not messagebox.askyesno("Confirm Batch", f"Folder: {folder}\nFiles: {len(files)}\nMode: {dir_label}\nOutput: *{suffix}{exts[0]}\n\nProceed?"):
            return
        self.log(f"Batch processing {len(files)} files in {folder}...")
        self.set_status("Processing...", "#F59E0B")
        self.progress_bar.set(0)
        done = 0
        for fname in files:
            in_path = os.path.join(folder, fname)
            base, ext = os.path.splitext(fname)
            out_path = os.path.join(folder, f"{base}{suffix}{ext}")
            try:
                for enc in ["utf-8", "utf-8-sig", "tis-620", "cp874"]:
                    try:
                        with open(in_path, "r", encoding=enc) as f: content = f.read()
                        break
                    except: continue
                protected, icons = self._protect_icons(content)
                result = (revert_mapping(protected, self.standard, self.contextual) if is_decode
                          else apply_mapping(protected, self.standard, self.contextual))
                result = self._restore_icons(result, icons)
                with open(out_path, "w", encoding="utf-8") as f: f.write(result)
                done += 1
            except Exception as e:
                self.log(f"  FAIL: {fname} - {e}")
            self.progress_bar.set(done / len(files))
        self.progress_bar.set(1)
        self.log(f"Done: {done}/{len(files)} files -> *{suffix}{ext}")
        self.set_status(f"Batch done: {done} files", "#10B981")
        messagebox.showinfo("Batch Done", f"Processed {done}/{len(files)} files.\nOutput: *{suffix}{ext}")

    def browse_output(self):
        initial = os.path.basename(self.output_var.get()) if self.output_var.get() else ""
        initial_dir = os.path.dirname(self.input_var.get()) if self.input_var.get() else ""
        initial_path = os.path.join(initial_dir, initial) if initial_dir and initial else ""
        filename = filedialog.asksaveasfilename(
            initialfile=initial_path,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.output_var.set(filename)

    def _protect_icons(self, text):
        """If icons mode is on, swap F999+ PUA with temp placeholders so they pass through unchanged."""
        if not self.icons_var.get():
            return text, None
        icons = {}
        import re
        def save(m):
            k = f'\x00I{len(icons):04X}\x00'
            icons[k] = m.group(0)
            return k
        # F999-F9FF range as PUA chars
        icon_range = chr(0xF999) + '-' + chr(0xF9FF)
        protected = re.sub(f'[{icon_range}]', save, text)
        return protected, icons

    def _restore_icons(self, text, icons):
        if not icons: return text
        for k, v in icons.items():
            text = text.replace(k, v)
        return text

    def run_conversion(self):
        input_path = self.input_var.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select an input file.")
            return

        output_path = self.output_var.get()
        if not output_path:
            self.auto_output_name()
            output_path = self.output_var.get()

        self.refresh_mapping_info()
        self.set_status("Converting...", "#F59E0B")
        self.progress_bar.set(0)

        try:
            encodings = ["utf-8", "utf-8-sig", "tis-620", "cp874"]
            content = None
            for enc in encodings:
                try:
                    with open(input_path, "r", encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if content is None:
                messagebox.showerror("Error", f"Cannot decode. Tried: {encodings}")
                return

            self.log(f"Read: {os.path.basename(input_path)} ({len(content):,} chars)")

            is_decode = "Decode" in self.direction_var.get() or "ถอด" in self.direction_var.get()
            protected, icons = self._protect_icons(content)
            if is_decode:
                result = revert_mapping(protected, self.standard, self.contextual)
                result = self._restore_icons(result, icons)
                orig = sum(1 for c in content if 0xF000 <= ord(c) <= 0xF8FF)
                rem = sum(1 for c in result if 0xF000 <= ord(c) <= 0xF8FF)
                self.log(f"PUA: {orig:,} -> {rem:,}  (reverted {orig - rem:,})")
            else:
                result = apply_mapping(protected, self.standard, self.contextual)
                result = self._restore_icons(result, icons)
                new_pua = sum(1 for c in result if 0xF000 <= ord(c) <= 0xF8FF)
                self.log(f"PUA chars in output: {new_pua:,}")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)

            self.progress_bar.set(1)
            self.log(f"Saved: {os.path.basename(output_path)}")
            self.set_status("Complete", "#10B981")
            messagebox.showinfo("Done", f"Output saved:\n{output_path}")

        except Exception as e:
            self.log(f"ERROR: {e}")
            self.set_status("Error", "#EF4444")
            messagebox.showerror("Error", str(e))

    def extract_remaining_pua(self):
        """Pick a file, auto-decode if needed, export lines with remaining PUA."""
        filename = filedialog.askopenfilename(
            title="Select file to scan for remaining PUA",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filename:
            return

        self.refresh_mapping_info()
        self.set_status("Extracting...", "#F59E0B")
        self.progress_bar.set(0)
        self.log(f"Scanning: {os.path.basename(filename)}")

        try:
            encodings = ["utf-8", "utf-8-sig", "tis-620", "cp874"]
            content = None
            for enc in encodings:
                try:
                    with open(filename, "r", encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if content is None:
                messagebox.showerror("Error", "Cannot decode file.")
                return

            # Auto-decode if >5% PUA
            pua_count = sum(1 for c in content if 0xF000 <= ord(c) <= 0xF8FF)
            if pua_count > len(content) * 0.05:
                self.log(f"Auto-decoding ({pua_count:,} PUA detected)...")
                protected, icons = self._protect_icons(content)
                content = revert_mapping(protected, self.standard, self.contextual)
                content = self._restore_icons(content, icons)
                after = sum(1 for c in content if 0xF000 <= ord(c) <= 0xF8FF)
                self.log(f"After decode: {after:,} PUA remaining")
            else:
                self.log(f"Read: {len(content):,} chars, {pua_count:,} PUA")

            # Find lines with remaining PUA
            lines = content.split('\n')
            pua_lines = []
            remaining_pua = Counter()
            for idx, line in enumerate(lines):
                pua_in_line = [(i, ord(c)) for i, c in enumerate(line) if 0xF000 <= ord(c) <= 0xF8FF]
                if pua_in_line:
                    line_num = idx + 1
                    for _, cp in pua_in_line:
                        remaining_pua[cp] += 1
                    pua_lines.append((line_num, line, pua_in_line))

            total_pua = sum(remaining_pua.values())

            if not pua_lines:
                self.log("All clean - no PUA remaining!")
                self.set_status("All Clean!", "#10B981")
                self.progress_bar.set(1)
                messagebox.showinfo("All Clean", "No PUA characters remain.")
                return

            self.log(f"{total_pua:,} PUA in {len(pua_lines)} lines ({len(remaining_pua)} unique)")

            # Output path
            base, ext = os.path.splitext(filename)
            for s in ["_decode", "_encode"]:
                if base.endswith(s):
                    base = base[:-len(s)]
            out_path = f"{base}_missing{ext}"

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"=== LINES WITH REMAINING PUA ===\n")
                f.write(f"Source: {os.path.basename(filename)}\n")
                f.write(f"Total: {total_pua} PUA in {len(pua_lines)} lines ({len(remaining_pua)} unique)\n\n")
                f.write(f"Top unmapped PUA:\n")
                for cp, cnt in remaining_pua.most_common(30):
                    f.write(f"  U+{cp:04X}: {cnt}x\n")
                f.write(f"\n{'=' * 80}\n\n")
                for line_num, line_text, pua_list in pua_lines:
                    f.write(f"[Line {line_num}] ({len(pua_list)} PUA)\n{line_text}\n")
                    f.write(f"PUA: {', '.join(f'U+{cp:04X}' for _, cp in pua_list)}\n")
                    f.write(f"{'-' * 60}\n\n")

            self.progress_bar.set(1)
            self.log(f"Saved: {os.path.basename(out_path)}")
            self.set_status(f"{len(pua_lines)} lines extracted", "#10B981")
            messagebox.showinfo("Done",
                                f"Lines with remaining PUA: {len(pua_lines)}\n"
                                f"Total: {total_pua:,} occurrences\n"
                                f"Unique: {len(remaining_pua)}\n\n"
                                f"Saved: {os.path.basename(out_path)}")

        except Exception as e:
            self.log(f"ERROR: {e}")
            self.set_status("Error", "#EF4444")
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = PUAConverterApp()
    app.mainloop()
