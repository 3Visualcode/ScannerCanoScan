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

from PIL import Image, ImageChops, ImageTk

APP_NAME = "ScannerCanoScan"
APP_VERSION = "1.1.0"

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

# Full flatbed area in mm (the backend default is only 103x76mm).
BED_W_MM = 215.0
BED_H_MM = 297.0
# Anything smaller than this is treated as a stray click, not a selection.
MIN_SEL_MM = 5.0

CREATE_NO_WINDOW = 0x08000000


def to_cygpath(path):
    """C:\\dir\\file -> /cygdrive/c/dir/file (scanimage is a Cygwin binary)."""
    drive, rest = os.path.splitdrive(path)
    return "/cygdrive/" + drive[0].lower() + rest.replace("\\", "/")


def scanimage_cmd():
    """The scanimage command line. SCANNERCANOSCAN_SCANIMAGE overrides it
    (used by tools/mock_scanimage.py to develop without the hardware)."""
    override = os.environ.get("SCANNERCANOSCAN_SCANIMAGE")
    if not override:
        return [SCANIMAGE]
    if override.lower().endswith(".py"):
        if getattr(sys, "frozen", False):
            # sys.executable is this app, not a Python interpreter.
            raise RuntimeError(
                "SCANNERCANOSCAN_SCANIMAGE must point to an .exe in the packaged build; "
                "the .py mock only works when running from source."
            )
        return [sys.executable, override]
    return [override]


def run_scanimage(args, timeout=900):
    cwd = SANE_BIN if os.path.isdir(SANE_BIN) else APP_DIR
    p = subprocess.run(
        scanimage_cmd() + args, capture_output=True, timeout=timeout,
        cwd=cwd, creationflags=CREATE_NO_WINDOW,
    )
    return p.returncode, p.stdout, p.stderr


# ---------------- Geometry (pure functions, unit-testable without Tk) ----------------

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def area_args(sel_mm=None):
    """SANE geometry: -l/-t = top-left corner, -x/-y = width/height, in mm."""
    left, top, width, height = sel_mm if sel_mm else (0.0, 0.0, BED_W_MM, BED_H_MM)
    return ["-l", f"{left:.1f}", "-t", f"{top:.1f}",
            "-x", f"{width:.1f}", "-y", f"{height:.1f}"]


def canvas_to_mm(cx, cy, disp):
    """Canvas pixel -> flatbed mm. disp = (x0, y0, w, h) of the preview on canvas."""
    x0, y0, w, h = disp
    fx = clamp((cx - x0) / w, 0.0, 1.0)
    fy = clamp((cy - y0) / h, 0.0, 1.0)
    return fx * BED_W_MM, fy * BED_H_MM


def mm_to_canvas(mx, my, disp):
    x0, y0, w, h = disp
    return x0 + (mx / BED_W_MM) * w, y0 + (my / BED_H_MM) * h


def rect_to_sel_mm(p0, p1, disp):
    """Two canvas points -> (left, top, width, height) in mm, None if too small."""
    ax, ay = canvas_to_mm(p0[0], p0[1], disp)
    bx, by = canvas_to_mm(p1[0], p1[1], disp)
    left, top = min(ax, bx), min(ay, by)
    width, height = abs(bx - ax), abs(by - ay)
    if width < MIN_SEL_MM or height < MIN_SEL_MM:
        return None
    return left, top, width, height


def _border_level(gray, band=4):
    """Median grey level of the image border = the empty flatbed background."""
    w, h = gray.size
    band = max(1, min(band, w, h))
    px = []
    px += list(gray.crop((0, 0, w, band)).getdata())
    px += list(gray.crop((0, h - band, w, h)).getdata())
    px += list(gray.crop((0, 0, band, h)).getdata())
    px += list(gray.crop((w - band, 0, w, h)).getdata())
    px.sort()
    return px[len(px) // 2]


def autocrop_sel_mm(img, tolerance=18, margin_mm=1.0):
    """Bounding box of the document on a full-bed preview -> (l, t, w, h) in mm.

    The background level is measured on the image border, so it works both with
    the lid closed (white) and open (dark)."""
    gray = img.convert("L")
    bg = _border_level(gray)
    diff = ImageChops.difference(gray, Image.new("L", gray.size, bg))
    box = diff.point(lambda p: 255 if p > tolerance else 0).getbbox()
    if not box:
        return None
    iw, ih = gray.size
    left = clamp(box[0] / iw * BED_W_MM - margin_mm, 0.0, BED_W_MM)
    top = clamp(box[1] / ih * BED_H_MM - margin_mm, 0.0, BED_H_MM)
    right = clamp(box[2] / iw * BED_W_MM + margin_mm, 0.0, BED_W_MM)
    bottom = clamp(box[3] / ih * BED_H_MM + margin_mm, 0.0, BED_H_MM)
    if right - left < MIN_SEL_MM or bottom - top < MIN_SEL_MM:
        return None
    return left, top, right - left, bottom - top


def describe_sel(sel_mm):
    if not sel_mm:
        return f"Scan area: full bed ({BED_W_MM:.0f} x {BED_H_MM:.0f} mm)"
    left, top, width, height = sel_mm
    return (f"Scan area: {width:.0f} x {height:.0f} mm "
            f"(offset {left:.0f}, {top:.0f} mm)")


class ScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION} — SANE LM983x scanner")
        self.geometry("980x640")
        self.minsize(760, 480)
        self.busy = False
        self.preview_img = None      # PIL image of the last full-bed preview
        self.tk_img = None           # keep a reference or Tk garbage-collects it
        self.disp = None             # (x0, y0, w, h) of the preview on the canvas
        self.sel_mm = None           # selected area in mm, None = full bed
        self._drag_from = None
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

        ttk.Separator(left).pack(fill="x", pady=(14, 8))
        ttk.Label(left, text="Scan area", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.area_var = tk.StringVar(value=describe_sel(None))
        ttk.Label(left, textvariable=self.area_var, wraplength=170,
                  foreground="#333333").pack(anchor="w", pady=(2, 6))
        ttk.Label(left, text="Drag on the preview to select an area.",
                  wraplength=170, foreground="#777777").pack(anchor="w", pady=(0, 6))
        self.btn_autocrop = ttk.Button(left, text="Auto-crop", command=self.do_autocrop)
        self.btn_autocrop.pack(fill="x", pady=2)
        ttk.Button(left, text="Reset to full area", command=self.clear_selection).pack(
            fill="x", pady=2
        )

        ttk.Separator(left).pack(fill="x", pady=(14, 8))
        ttk.Button(left, text="Open Scans folder", command=self.open_folder).pack(
            fill="x", pady=2
        )
        ttk.Button(left, text="Check scanner", command=lambda: self._start_bg(self.check_scanner)).pack(
            fill="x", pady=2
        )
        ttk.Label(left, text=f"v{APP_VERSION}", foreground="#999999").pack(
            anchor="w", pady=(16, 0)
        )

        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(right, bg="#2b2b2b", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Configure>", lambda e: self._render())

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

    def _scan_to_file(self, dpi, mode, fmt, win_path, sel_mm=None, timeout=900):
        args = ["--mode", mode, "--resolution", str(dpi)] + area_args(sel_mm) + [
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
        # The preview is always the full bed: that is what you select an area on.
        self.set_status("Preview in progress…", spinning=True)
        tmp = os.path.join(os.environ.get("TEMP", APP_DIR), "canoscan_preview.png")
        self._scan_to_file(75, "Color", "png", tmp)
        img = Image.open(tmp)
        img.load()
        self.set_status("Preview done ✔ — drag on the image to select an area")
        self.after(0, lambda: self._set_preview(img))

    def do_scan(self):
        self._start_bg(self._scan_job)

    def _scan_job(self):
        dpi = self.dpi_var.get()
        mode = MODES[self.mode_var.get()]
        fmt = self.fmt_var.get().lower()
        sel = self.sel_mm
        ext = {"png": "png", "jpeg": "jpg", "pdf": "pdf", "tiff": "tif"}[fmt]
        os.makedirs(SCAN_DIR, exist_ok=True)
        name = datetime.now().strftime("scan_%Y-%m-%d_%H-%M-%S") + "." + ext
        path = os.path.join(SCAN_DIR, name)

        area = "full bed" if not sel else f"{sel[2]:.0f}x{sel[3]:.0f} mm"
        self.set_status(f"Scanning {area} at {dpi} DPI… (may take minutes)", spinning=True)
        self._scan_to_file(dpi, mode, fmt, path, sel_mm=sel)
        self.set_status(f"Saved: {name} ✔")

        if fmt == "png":
            self.after(0, lambda: self._show_result(path))
        else:
            self.after(0, self.canvas.delete, "all")
            self.after(0, lambda: self.canvas.create_text(
                20, 20, anchor="nw", fill="#dddddd", font=("Segoe UI", 11),
                text=f"File saved:\n{path}\n\n(on-screen preview available for PNG only)"
            ))

    def do_autocrop(self):
        if self.preview_img is None:
            self.set_status("Run a preview first, then Auto-crop.")
            return
        sel = autocrop_sel_mm(self.preview_img)
        if not sel:
            self.set_status("Auto-crop: no document detected — keeping the full area.")
            return
        self._set_selection(sel)
        self.set_status(f"Auto-crop: {sel[2]:.0f} x {sel[3]:.0f} mm ✔")

    def clear_selection(self):
        self._set_selection(None)
        self.set_status("Scan area reset to the full bed.")

    # ---------------- Preview rendering & selection ----------------
    def _set_preview(self, pil_img):
        # A scanned result is not a full-bed image, so it must not be selectable.
        self.preview_img = pil_img
        self._render()

    def _show_result(self, path):
        """Display a finished scan. Not usable as a selection surface."""
        try:
            img = Image.open(path)
            img.load()
        except OSError:
            return
        if self.sel_mm is None:
            self.preview_img = img
        self.tk_img = None
        self._render(override=img)

    def _set_selection(self, sel_mm):
        self.sel_mm = sel_mm
        self.area_var.set(describe_sel(sel_mm))
        self._render()

    def _render(self, override=None):
        self.canvas.delete("all")
        img = override if override is not None else self.preview_img
        if img is None:
            self.disp = None
            self.canvas.create_text(
                20, 20, anchor="nw", fill="#dddddd", font=("Segoe UI", 11),
                text="No preview yet.\n\nClick \"Preview (75 DPI)\" to scan the whole bed,\n"
                     "then drag on the image to select the area to scan."
            )
            return

        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)
        iw, ih = img.size
        scale = min(cw / iw, ch / ih)
        dw, dh = max(1, int(iw * scale)), max(1, int(ih * scale))
        x0, y0 = (cw - dw) // 2, (ch - dh) // 2
        self.tk_img = ImageTk.PhotoImage(img.resize((dw, dh), Image.LANCZOS))
        self.canvas.create_image(x0, y0, anchor="nw", image=self.tk_img)

        if override is None:
            self.disp = (x0, y0, dw, dh)
            self._draw_selection()
        else:
            self.disp = None

    def _draw_selection(self):
        if not self.sel_mm or not self.disp:
            return
        left, top, width, height = self.sel_mm
        x0, y0 = mm_to_canvas(left, top, self.disp)
        x1, y1 = mm_to_canvas(left + width, top + height, self.disp)
        dx, dy, dw, dh = self.disp
        # Dim everything outside the selection.
        for box in ((dx, dy, dx + dw, y0), (dx, y1, dx + dw, dy + dh),
                    (dx, y0, x0, y1), (x1, y0, dx + dw, y1)):
            self.canvas.create_rectangle(*box, fill="#000000", outline="",
                                         stipple="gray50", tags="sel")
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#00c853", width=2, tags="sel")

    def _on_press(self, event):
        if not self.disp:
            return
        self._drag_from = (event.x, event.y)

    def _on_drag(self, event):
        if not self._drag_from:
            return
        self.canvas.delete("rubber")
        self.canvas.create_rectangle(
            self._drag_from[0], self._drag_from[1], event.x, event.y,
            outline="#00c853", width=2, dash=(4, 3), tags="rubber",
        )

    def _on_release(self, event):
        if not self._drag_from:
            return
        start, self._drag_from = self._drag_from, None
        self.canvas.delete("rubber")
        sel = rect_to_sel_mm(start, (event.x, event.y), self.disp)
        if sel is None:
            # A click (or a selection under 5 mm) means "back to the full bed".
            self._set_selection(None)
            self.set_status("Scan area reset to the full bed.")
            return
        self._set_selection(sel)
        self.set_status(f"Selected area: {sel[2]:.0f} x {sel[3]:.0f} mm ✔")

    def open_folder(self):
        os.makedirs(SCAN_DIR, exist_ok=True)
        os.startfile(SCAN_DIR)


if __name__ == "__main__":
    if not os.environ.get("SCANNERCANOSCAN_SCANIMAGE") and not os.path.exists(SCANIMAGE):
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"scanimage.exe not found:\n{SCANIMAGE}")
        sys.exit(1)
    app = ScannerApp()
    app.mainloop()
