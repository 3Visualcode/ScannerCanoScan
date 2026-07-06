"""
ScannerCanoScan - Free scanning software for LM983x-based USB scanners
(Canon CanoScan N670U and other models supported by the SANE "plustek" backend).

100% native Windows: SANE (plustek backend) compiled for Windows (Cygwin port),
scanner accessed through the WinUSB driver (installed once with Zadig).
No external runtime dependencies: everything is bundled inside the executable.
"""

import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

if getattr(sys, "frozen", False):
    BUNDLE_DIR = sys._MEIPASS            # resources extracted by PyInstaller
    APP_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BUNDLE_DIR

SANE_BIN = os.path.join(BUNDLE_DIR, "sane-win64", "bin")
SCANIMAGE = os.path.join(SANE_BIN, "scanimage.exe")
SCAN_DIR = os.path.join(APP_DIR, "Scans")

MODES = {"Color": "Color", "Grayscale": "Gray", "Black & white": "Lineart"}
DPI_VALUES = ["75", "150", "300", "600"]
FORMATS = ["PNG", "JPEG", "PDF", "TIFF"]
# full flatbed area in mm (backend default is only 103x76mm)
FULL_AREA = ["-l", "0", "-t", "0", "-x", "215", "-y", "297"]

CREATE_NO_WINDOW = 0x08000000


def to_cygpath(path):
    """C:\\dir\\file -> /cygdrive/c/dir/file (scanimage is a Cygwin binary)."""
    drive, rest = os.path.splitdrive(path)
    return "/cygdrive/" + drive[0].lower() + rest.replace("\\", "/")


def run_scanimage(args, timeout=900):
    p = subprocess.run(
        [SCANIMAGE] + args, capture_output=True, timeout=timeout,
        cwd=SANE_BIN, creationflags=CREATE_NO_WINDOW,
    )
    return p.returncode, p.stdout, p.stderr


class ScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ScannerCanoScan — SANE LM983x scanner")
        self.geometry("980x640")
        self.minsize(760, 480)
        self.preview_img = None
        self.busy = False
        self._build_ui()
        self.after(200, lambda: self._start_bg(self.check_scanner))

    # ---------------- UI ----------------
    def _build_ui(self):
        left = ttk.Frame(self, padding=12)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Settings", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        ttk.Label(left, text="Mode").pack(anchor="w")
        self.mode_var = tk.StringVar(value="Color")
        ttk.Combobox(
            left, textvariable=self.mode_var, values=list(MODES), state="readonly", width=18
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(left, text="Resolution (DPI)").pack(anchor="w")
        self.dpi_var = tk.StringVar(value="300")
        ttk.Combobox(
            left, textvariable=self.dpi_var, values=DPI_VALUES, state="readonly", width=18
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(left, text="File format").pack(anchor="w")
        self.fmt_var = tk.StringVar(value="PNG")
        ttk.Combobox(
            left, textvariable=self.fmt_var, values=FORMATS, state="readonly", width=18
        ).pack(anchor="w", pady=(0, 16))

        self.btn_preview = ttk.Button(left, text="Preview (75 DPI)", command=self.do_preview)
        self.btn_preview.pack(fill="x", pady=2)
        self.btn_scan = ttk.Button(left, text="SCAN", command=self.do_scan)
        self.btn_scan.pack(fill="x", pady=2)
        ttk.Button(left, text="Open Scans folder", command=self.open_folder).pack(
            fill="x", pady=(16, 2)
        )
        ttk.Button(left, text="Check scanner", command=lambda: self._start_bg(self.check_scanner)).pack(
            fill="x", pady=2
        )

        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(right, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Starting…")
        bar = ttk.Frame(self)
        bar.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=160)
        ttk.Label(bar, textvariable=self.status_var, padding=(8, 4)).pack(side="left")
        self.progress.pack(side="right", padx=8, pady=4)

    def set_status(self, text, spinning=False):
        def _apply():
            self.status_var.set(text)
            if spinning:
                self.progress.start(12)
            else:
                self.progress.stop()
        self.after(0, _apply)

    def _start_bg(self, fn, *args):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._bg_wrapper, args=(fn,) + args, daemon=True).start()

    def _bg_wrapper(self, fn, *args):
        try:
            fn(*args)
        except Exception as e:
            self.set_status(f"Error: {e}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.busy = False

    # ---------------- Scanner ----------------
    def check_scanner(self):
        self.set_status("Detecting scanner…", spinning=True)
        rc, out, err = run_scanimage(["-L"], timeout=120)
        txt = (out + err).decode(errors="replace")
        if "plustek" in txt:
            self.set_status("Scanner ready ✔")
            return True
        self.set_status(
            "Scanner not detected: check the USB cable and the WinUSB driver (see README)."
        )
        return False

    def _scan_to_file(self, dpi, mode, fmt, win_path, timeout=900):
        args = ["--mode", mode, "--resolution", str(dpi)] + FULL_AREA + [
            f"--format={fmt}", "-o", to_cygpath(win_path)
        ]
        rc, out, err = run_scanimage(args, timeout=timeout)
        ok = rc == 0 and os.path.exists(win_path) and os.path.getsize(win_path) > 0
        if not ok:
            output = (out + err).decode(errors="replace")
            raise RuntimeError(f"Scan failed:\n{output.strip()[:800]}")

    # ---------------- Actions ----------------
    def do_preview(self):
        self._start_bg(self._preview_job)

    def _preview_job(self):
        self.set_status("Preview in progress…", spinning=True)
        tmp = os.path.join(os.environ.get("TEMP", APP_DIR), "canoscan_preview.png")
        self._scan_to_file(75, "Color", "png", tmp)
        self.set_status("Preview done ✔")
        self.after(0, lambda: self._show_image(tmp))

    def do_scan(self):
        self._start_bg(self._scan_job)

    def _scan_job(self):
        dpi = self.dpi_var.get()
        mode = MODES[self.mode_var.get()]
        fmt = self.fmt_var.get().lower()
        ext = {"png": "png", "jpeg": "jpg", "pdf": "pdf", "tiff": "tif"}[fmt]
        os.makedirs(SCAN_DIR, exist_ok=True)
        name = datetime.now().strftime("scan_%Y-%m-%d_%H-%M-%S") + "." + ext
        path = os.path.join(SCAN_DIR, name)

        self.set_status(f"Scanning at {dpi} DPI… (may take minutes)", spinning=True)
        self._scan_to_file(dpi, mode, fmt, path)
        self.set_status(f"Saved: {name} ✔")

        if fmt == "png":
            self.after(0, lambda: self._show_image(path))
        else:
            self.after(0, self.canvas.delete, "all")
            self.after(0, lambda: self.canvas.create_text(
                20, 20, anchor="nw", fill="#dddddd", font=("Segoe UI", 11),
                text=f"File saved:\n{path}\n\n(on-screen preview available for PNG only)"
            ))

    def _show_image(self, path):
        try:
            img = tk.PhotoImage(file=path)
        except tk.TclError:
            return
        cw = max(self.canvas.winfo_width(), 200)
        ch = max(self.canvas.winfo_height(), 200)
        factor = max(1, (img.width() + cw - 1) // cw, (img.height() + ch - 1) // ch)
        if factor > 1:
            img = img.subsample(factor, factor)
        self.preview_img = img
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=img)

    def open_folder(self):
        os.makedirs(SCAN_DIR, exist_ok=True)
        os.startfile(SCAN_DIR)


if __name__ == "__main__":
    if not os.path.exists(SCANIMAGE):
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"scanimage.exe not found:\n{SCANIMAGE}")
        sys.exit(1)
    app = ScannerApp()
    app.mainloop()
