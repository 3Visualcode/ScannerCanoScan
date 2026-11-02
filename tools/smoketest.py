"""
End-to-end check of the GUI against the simulated scanner - still no hardware.

    python tools\\smoketest.py

Drives the real ScannerApp: preview, auto-crop, mouse drag selection and scan,
then verifies the geometry that reached scanimage and the files produced.
Then switches the simulated scanner to a GT6816 model (artec_eplus48u backend)
and checks the firmware handling and the per-backend DPI list, and finally
checks that a plustek model's DPI list comes from what the backend reports.
A Tk window opens for a moment and closes by itself.
"""

import os
import sys

# Status texts contain ✔/—; a cp1252 console must not abort the run.
sys.stdout.reconfigure(errors="replace")
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

LOG = os.path.join(tempfile.gettempdir(), "smoketest_scanimage.log")
if os.path.exists(LOG):
    os.remove(LOG)
os.environ["SCANNERCANOSCAN_SCANIMAGE"] = os.path.join(ROOT, "tools", "mock_scanimage.py")
os.environ["SCANNERCANOSCAN_MOCK_LOG"] = LOG

from PIL import Image                                       # noqa: E402

import scanner_app                                          # noqa: E402
from tools.mock_scanimage import DOC_MM                      # noqa: E402

import shutil                                               # noqa: E402

OUT_DIR = os.path.join(tempfile.gettempdir(), "scannercanoscan_smoketest")
FW_ROOT = os.path.join(tempfile.gettempdir(), "scannercanoscan_smoketest_fw")
for d in (OUT_DIR, FW_ROOT):          # leftovers of an aborted run must not count
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
scanner_app.SCAN_DIR = OUT_DIR
# Keep the firmware test away from the real sane-win64 tree and the exe folder.
FW_HOME = os.path.join(FW_ROOT, "home")
FW_DIR = os.path.join(FW_ROOT, "bundle")
scanner_app.FIRMWARE_HOME = FW_HOME
scanner_app.FIRMWARE_DIR = FW_DIR
os.environ.pop("SCANNERCANOSCAN_MOCK_DEVICE", None)

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
    app.prompt_firmware = False       # never block on a file dialog
    app.geometry("980x640")
    app.update()

    print("detection")
    check("mock scanner is detected", app.check_scanner() is True)
    app.update()
    check("backend is plustek", app.backend == "plustek", app.backend)
    check("scanner name shown in the panel", "N670U" in app.scanner_var.get(),
          app.scanner_var.get())
    check("plustek DPI list offered", list(app.dpi_box.cget("values")) == ["75", "150", "300", "600"],
          str(app.dpi_box.cget("values")))

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

    print("GT6816 scanner (artec_eplus48u backend)")
    shutil.rmtree(FW_HOME, ignore_errors=True)
    shutil.rmtree(FW_DIR, ignore_errors=True)
    os.makedirs(FW_HOME)
    os.environ["SCANNERCANOSCAN_MOCK_DEVICE"] = "artec_eplus48u"
    app.dpi_var.set("150")
    check("detected but not ready without firmware", app.check_scanner() is False)
    app.update()
    check("backend switched to artec_eplus48u", app.backend == "artec_eplus48u", app.backend)
    check("status explains the missing firmware", "Artec48.usb" in app.status_var.get(),
          app.status_var.get())
    check("DPI list switched to the artec one",
          list(app.dpi_box.cget("values")) == ["50", "100", "200", "300", "600", "1200"],
          str(app.dpi_box.cget("values")))
    check("an invalid DPI (150) fell back to 300", app.dpi_var.get() == "300", app.dpi_var.get())
    check("preview button shows 50 DPI", "50 DPI" in app.btn_preview.cget("text"),
          app.btn_preview.cget("text"))

    with open(os.path.join(FW_HOME, "Artec48.usb"), "wb") as fh:
        fh.write(b"\x00" * 8192)
    check("ready once Artec48.usb is next to the exe", app.check_scanner() is True)
    app.update()
    check("firmware copied where artec_eplus48u.conf expects it",
          os.path.isfile(os.path.join(FW_DIR, "Artec48.usb")))
    check("status names the scanner", "Trust Easy Webscan 19200" in app.status_var.get(),
          app.status_var.get())

    app._preview_job()
    app.update()
    check("preview on the artec backend runs at 50 DPI", "50" in last_call(), " ".join(last_call()))
    check("preview is still the full bed",
          geometry_of(last_call()) == {"-l": 0.0, "-t": 0.0, "-x": 215.0, "-y": 297.0})
    before = set(os.listdir(OUT_DIR))
    app.fmt_var.set("PNG")
    app.dpi_var.set("200")
    app.clear_selection()
    app._scan_job()
    app.update()
    new_files = set(os.listdir(OUT_DIR)) - before
    check("a 200 DPI scan is accepted by the artec mock",
          len(new_files) == 1 and "200" in last_call(), ", ".join(new_files))

    print("back to the Canon")
    os.environ.pop("SCANNERCANOSCAN_MOCK_DEVICE", None)
    check("plustek detected again", app.check_scanner() is True)
    app.update()
    check("DPI list back to plustek", "75" in app.dpi_box.cget("values"))
    check("200 DPI (artec only) replaced by 300", app.dpi_var.get() == "300", app.dpi_var.get())
    check("panel shows the reported maximum", "up to 600 DPI" in app.scanner_var.get(),
          app.scanner_var.get())

    print("resolution reported by the connected model")
    os.environ["SCANNERCANOSCAN_MOCK_DEVICE"] = "plustek_lide30"
    check("LiDE 30 detected", app.check_scanner() is True)
    app.update()
    check("1200 DPI offered on the LiDE 30",
          list(app.dpi_box.cget("values")) == ["75", "150", "300", "600", "1200"],
          str(app.dpi_box.cget("values")))
    with open(LOG, encoding="utf-8") as fh:
        check("the query names the detected device",
              any("--help" in line and "plustek:libusb:001:004" in line for line in fh))
    check("panel shows 1200 DPI", "up to 1200 DPI" in app.scanner_var.get(),
          app.scanner_var.get())

    app.dpi_var.set("1200")
    app.fmt_var.set("PNG")
    app._set_selection((30.0, 45.0, 30.0, 30.0))
    app._scan_job()
    app.update()
    check("a 1200 DPI scan reaches scanimage", "1200" in last_call(), " ".join(last_call()))
    newest = max((os.path.join(OUT_DIR, f) for f in os.listdir(OUT_DIR)), key=os.path.getmtime)
    with Image.open(newest) as shot:
        check("the file really is 1200 DPI", shot.size == (1417, 1417), str(shot.size))

    saved_limit = scanner_app.MAX_ONSCREEN_PIXELS
    scanner_app.MAX_ONSCREEN_PIXELS = 1
    app._scan_job()
    app.update()
    scanner_app.MAX_ONSCREEN_PIXELS = saved_limit
    shown = " ".join(app.canvas.itemcget(i, "text") for i in app.canvas.find_all()
                     if app.canvas.type(i) == "text")
    check("an oversized scan is saved but not loaded for display",
          "too large to display" in shown, shown.replace("\n", " "))
    app.clear_selection()

    print("backend that does not report its range")
    os.environ["SCANNERCANOSCAN_MOCK_DEVICE"] = "plustek_nohelp"
    check("still ready when --help fails", app.check_scanner() is True)
    app.update()
    check("falls back to the standard list",
          list(app.dpi_box.cget("values")) == ["75", "150", "300", "600"],
          str(app.dpi_box.cget("values")))
    check("1200 DPI (not confirmed here) replaced by 300", app.dpi_var.get() == "300",
          app.dpi_var.get())
    check("panel says the range was not read", "not reported" in app.scanner_var.get(),
          app.scanner_var.get())
    os.environ.pop("SCANNERCANOSCAN_MOCK_DEVICE", None)

    app.destroy()


if __name__ == "__main__":
    main()
    print()
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    shutil.rmtree(FW_ROOT, ignore_errors=True)
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: " + ", ".join(FAILURES))
        sys.exit(1)
    print("all checks passed")
