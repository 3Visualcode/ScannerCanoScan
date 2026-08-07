"""
End-to-end check of the GUI against the simulated scanner - still no hardware.

    python tools\\smoketest.py

Drives the real ScannerApp: preview, auto-crop, mouse drag selection and scan,
then verifies the geometry that reached scanimage and the files produced.
A Tk window opens for a moment and closes by itself.
"""

import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

LOG = os.path.join(tempfile.gettempdir(), "smoketest_scanimage.log")
if os.path.exists(LOG):
    os.remove(LOG)
os.environ["SCANNERCANOSCAN_SCANIMAGE"] = os.path.join(ROOT, "tools", "mock_scanimage.py")
os.environ["SCANNERCANOSCAN_MOCK_LOG"] = LOG

import scanner_app                                          # noqa: E402
from tools.mock_scanimage import DOC_MM                      # noqa: E402

OUT_DIR = os.path.join(tempfile.gettempdir(), "scannercanoscan_smoketest")
os.makedirs(OUT_DIR, exist_ok=True)
scanner_app.SCAN_DIR = OUT_DIR

FAILURES = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def last_call():
    with open(LOG, encoding="utf-8") as fh:
        return fh.read().strip().splitlines()[-1].split()


def geometry_of(argv):
    return {k: float(argv[argv.index(k) + 1]) for k in ("-l", "-t", "-x", "-y")}


def event(x, y):
    return types.SimpleNamespace(x=x, y=y)


def main():
    app = scanner_app.ScannerApp()
    app.geometry("980x640")
    app.update()

    print("detection")
    check("mock scanner is detected", app.check_scanner() is True)

    print("preview")
    app._preview_job()
    app.update()
    check("preview image loaded", app.preview_img is not None,
          str(app.preview_img.size) if app.preview_img else "")
    check("preview is a full-bed scan",
          geometry_of(last_call()) == {"-l": 0.0, "-t": 0.0, "-x": 215.0, "-y": 297.0})
    check("preview runs at 75 DPI", "75" in last_call())
    check("canvas knows where the preview is drawn", app.disp is not None, str(app.disp))

    print("auto-crop")
    app.do_autocrop()
    app.update()
    dl, dt, dw, dh = DOC_MM
    sel = app.sel_mm
    check("a document was detected", sel is not None)
    check("auto-crop matches the simulated document within the 1 mm margin",
          sel and abs(sel[0] - dl) <= 2 and abs(sel[1] - dt) <= 2
          and abs(sel[2] - dw) <= 4 and abs(sel[3] - dh) <= 4,
          " ".join(f"{v:.1f}" for v in sel) if sel else "")
    check("the area label follows the selection", "mm" in app.area_var.get(),
          app.area_var.get())

    print("mouse selection")
    x0, y0, w, h = app.disp
    app._on_press(event(x0 + w // 4, y0 + h // 4))
    app._on_drag(event(x0 + w // 2, y0 + h // 2))
    app._on_release(event(x0 + w // 2, y0 + h // 2))
    app.update()
    sel = app.sel_mm
    check("dragging a quarter of the bed selects a quarter of the bed",
          sel and abs(sel[2] - scanner_app.BED_W_MM / 4) < 2
          and abs(sel[3] - scanner_app.BED_H_MM / 4) < 2,
          " ".join(f"{v:.1f}" for v in sel) if sel else "")

    print("scan with the selection")
    app.fmt_var.set("PNG")
    app.dpi_var.set("150")
    app._scan_job()
    app.update()
    geo = geometry_of(last_call())
    check("the selection reached scanimage unchanged",
          abs(geo["-l"] - sel[0]) < 0.1 and abs(geo["-t"] - sel[1]) < 0.1
          and abs(geo["-x"] - sel[2]) < 0.1 and abs(geo["-y"] - sel[3]) < 0.1, str(geo))
    files = sorted(os.listdir(OUT_DIR))
    check("a file was written", len(files) == 1, ", ".join(files))
    if files:
        from PIL import Image
        img = Image.open(os.path.join(OUT_DIR, files[0]))
        expect = (round(sel[2] * 150 / 25.4), round(sel[3] * 150 / 25.4))
        check("the file has the pixel size implied by area x DPI",
              img.size == expect, f"{img.size} vs {expect}")

    print("reset")
    app.clear_selection()
    app.update()
    check("reset goes back to the full bed", app.sel_mm is None)
    app._scan_job()
    app.update()
    check("a scan after reset covers the whole bed",
          geometry_of(last_call()) == {"-l": 0.0, "-t": 0.0, "-x": 215.0, "-y": 297.0})

    print("other formats")
    for fmt, ext in (("JPEG", ".jpg"), ("PDF", ".pdf"), ("TIFF", ".tif")):
        app.fmt_var.set(fmt)
        app._scan_job()
        app.update()
        check(f"{fmt} output written",
              any(f.endswith(ext) for f in os.listdir(OUT_DIR)))

    print("version")
    check("version is in the window title", scanner_app.APP_VERSION in app.title(),
          app.title())

    app.destroy()


if __name__ == "__main__":
    main()
    print()
    for f in os.listdir(OUT_DIR):
        os.remove(os.path.join(OUT_DIR, f))
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: " + ", ".join(FAILURES))
        sys.exit(1)
    print("all checks passed")
