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

MAPPING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapping.json")


class PUAConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PUA Thai Converter v1.0")
        self.geometry("950x750")
        self.minsize(800, 600)

        self.standard, self.contextual = load_mapping()
        self.setup_ui()
        self.refresh_mapping_info()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # === Row 0: File Selection ===
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(file_frame, text="Input File",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        self.input_var = tk.StringVar()
        input_entry = ctk.CTkEntry(file_frame, textvariable=self.input_var, placeholder_text="Select .txt or .csv file...")
        input_entry.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew", columnspan=2)
        ctk.CTkButton(file_frame, text="Browse", width=80, command=self.browse_input).grid(row=1, column=2, padx=5, pady=(0, 5))

        ctk.CTkLabel(file_frame, text="Output File (auto-named)",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=2, column=0, padx=10, pady=(5, 2), sticky="w")
        self.output_var = tk.StringVar()
        output_entry = ctk.CTkEntry(file_frame, textvariable=self.output_var, placeholder_text="Auto-generated...")
        output_entry.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew", columnspan=2)
        ctk.CTkButton(file_frame, text="Save As", width=80, command=self.browse_output).grid(row=3, column=2, padx=5, pady=(0, 10))

        # === Row 1: Controls ===
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        ctk.CTkLabel(ctrl_frame, text="Direction:", font=ctk.CTkFont(size=14)).pack(side="left", padx=(10, 5), pady=10)
        self.direction_var = ctk.StringVar(value="Thai -> PUA (Encode)")
        self.dir_dropdown = ctk.CTkOptionMenu(
            ctrl_frame, variable=self.direction_var, width=200,
            values=["Thai -> PUA (Encode)", "PUA -> Thai (Decode)"],
            command=self.on_direction_change
        )
        self.dir_dropdown.pack(side="left", padx=5, pady=10)

        self.mapping_label = ctk.CTkLabel(ctrl_frame, text="", font=ctk.CTkFont(size=13))
        self.mapping_label.pack(side="left", padx=30, pady=10)

        self.extract_btn = ctk.CTkButton(ctrl_frame, text="Extract Remaining PUA", width=180,
                                         fg_color="#6A1B9A", command=self.extract_remaining_pua)
        self.extract_btn.pack(side="right", padx=10, pady=10)

        self.convert_btn = ctk.CTkButton(ctrl_frame, text="Encode", width=100,
                                         fg_color="#1565C0", font=ctk.CTkFont(size=14, weight="bold"),
                                         command=self.run_conversion)
        self.convert_btn.pack(side="right", padx=5, pady=10)

        # === Row 2: Log ===
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, padx=15, pady=(5, 10), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(log_frame, state="disabled", fg_color="black",
                                      text_color="lightgreen", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # === Row 3: Status ===
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=3, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(status_frame, text="Ready", text_color="#6B7280",
                                         font=ctk.CTkFont(size=13))
        self.status_label.pack(side="left")
        self.progress_bar = ctk.CTkProgressBar(status_frame, width=300)
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
        self.mapping_label.configure(text=f"Mapping: {total} entries")
        if total <= 1:
            self.log("Note: mapping.json has few entries. Edit it to add your font's PUA mappings.")

    def on_direction_change(self, choice):
        if "Decode" in choice:
            self.convert_btn.configure(text="Decode", fg_color="#6A1B9A")
        else:
            self.convert_btn.configure(text="Encode", fg_color="#1565C0")
        self.auto_output_name()

    def auto_output_name(self):
        input_path = self.input_var.get()
        if not input_path:
            return
        base, ext = os.path.splitext(input_path)
        suffix = "_decode" if "Decode" in self.direction_var.get() else "_encode"
        self.output_var.set(f"{base}{suffix}{ext}")

    def browse_input(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.input_var.set(filename)
            self.auto_output_name()

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

            is_decode = "Decode" in self.direction_var.get()
            if is_decode:
                result = revert_mapping(content, self.standard, self.contextual)
                orig = sum(1 for c in content if 0xF000 <= ord(c) <= 0xF8FF)
                rem = sum(1 for c in result if 0xF000 <= ord(c) <= 0xF8FF)
                self.log(f"PUA: {orig:,} -> {rem:,}  (reverted {orig - rem:,})")
            else:
                result = apply_mapping(content, self.standard, self.contextual)
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
                content = revert_mapping(content, self.standard, self.contextual)
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
