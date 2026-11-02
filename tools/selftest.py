"""
Headless checks for the geometry and auto-crop logic - no scanner, no GUI.

    python tools\\selftest.py

Covers what can be verified without hardware. What it cannot prove is that the
plustek backend interprets -l/-t/-x/-y with the same origin we assume
(top-left of the glass); that needs one run on the real device.
"""

import os
import sys

# Status texts contain ✔/—; a cp1252 console must not abort the run.
sys.stdout.reconfigure(errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

import scanner_app
from scanner_app import (BACKENDS, BED_H_MM, BED_W_MM, FIRMWARE_NAMES, area_args,
                         autocrop_sel_mm, canvas_to_mm, describe_sel,
                         find_firmware, firmware_ready, install_firmware,
                         mm_to_canvas, parse_device_list, parse_dpi_choices,
                         rect_to_sel_mm, scan_bytes, scan_pixels, scan_timeout,
                         to_cygpath)
from tools.mock_scanimage import ALLOWED_DPI, DEVICES, HELP_RESOLUTION, from_cygpath

FAILURES = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def close(a, b, eps=0.5):
    return abs(a - b) <= eps


DISP = (100, 50, 400, 552)   # preview drawn at x=100,y=50, 400x552 px


def test_geometry():
    print("geometry")
    check("top-left corner maps to 0,0 mm",
          canvas_to_mm(100, 50, DISP) == (0.0, 0.0))
    bx, by = canvas_to_mm(500, 602, DISP)
    check("bottom-right corner maps to the full bed",
          close(bx, BED_W_MM) and close(by, BED_H_MM), f"{bx:.1f} x {by:.1f}")
    cx, cy = canvas_to_mm(300, 326, DISP)
    check("centre maps to half the bed",
          close(cx, BED_W_MM / 2) and close(cy, BED_H_MM / 2), f"{cx:.1f}, {cy:.1f}")
    ox, oy = canvas_to_mm(-500, 9999, DISP)
    check("points outside the preview are clamped to the bed",
          ox == 0.0 and close(oy, BED_H_MM))

    for mx, my in ((0, 0), (50, 70), (BED_W_MM, BED_H_MM)):
        rx, ry = canvas_to_mm(*mm_to_canvas(mx, my, DISP), DISP)
        check(f"mm->canvas->mm round trip at {mx},{my}", close(rx, mx) and close(ry, my))


def test_selection():
    print("selection")
    sel = rect_to_sel_mm((150, 100), (350, 400), DISP)
    check("drag produces a positive-size area", sel is not None)
    left, top, width, height = sel
    check("left/top come from the top-left corner of the drag",
          close(left, 50 / 400 * BED_W_MM) and close(top, 50 / 552 * BED_H_MM),
          f"{left:.1f}, {top:.1f}")
    check("width/height are extents, not corners",
          close(width, 200 / 400 * BED_W_MM) and close(height, 300 / 552 * BED_H_MM),
          f"{width:.1f} x {height:.1f}")

    rev = rect_to_sel_mm((350, 400), (150, 100), DISP)
    check("dragging bottom-right to top-left gives the same area",
          all(close(a, b) for a, b in zip(sel, rev)))
    check("a stray click is not a selection",
          rect_to_sel_mm((200, 200), (202, 203), DISP) is None)


def test_area_args():
    print("scanimage arguments")
    check("no selection scans the full bed",
          area_args(None) == ["-l", "0.0", "-t", "0.0", "-x", "215.0", "-y", "297.0"],
          " ".join(area_args(None)))
    args = area_args((10.0, 20.0, 100.0, 150.0))
    check("-x/-y carry the size, not the far corner",
          args == ["-l", "10.0", "-t", "20.0", "-x", "100.0", "-y", "150.0"],
          " ".join(args))


def _bed_with_doc(box, bg=244, fg=40, size=(645, 891)):
    img = Image.new("RGB", size, (bg, bg, bg))
    ImageDraw.Draw(img).rectangle(box, fill=(fg, fg, fg))
    return img


def test_autocrop():
    print("auto-crop")
    # Document at 1/4..1/2 of the bed, on a light background.
    img = _bed_with_doc([161, 222, 322, 445])
    sel = autocrop_sel_mm(img)
    check("document found on a light background", sel is not None)
    left, top, width, height = sel
    check("bounding box matches the document",
          close(left, BED_W_MM * 0.25, 2) and close(top, BED_H_MM * 0.25, 2)
          and close(width, BED_W_MM * 0.25, 3) and close(height, BED_H_MM * 0.25, 3),
          f"{left:.0f},{top:.0f} {width:.0f}x{height:.0f} mm")

    dark = _bed_with_doc([161, 222, 322, 445], bg=20, fg=230)
    sel_dark = autocrop_sel_mm(dark)
    check("works with the lid open (dark background)",
          sel_dark is not None and close(sel_dark[2], BED_W_MM * 0.25, 3))

    blank = Image.new("RGB", (645, 891), (244, 244, 244))
    check("an empty bed yields no selection", autocrop_sel_mm(blank) is None)

    full = Image.new("RGB", (645, 891), (10, 10, 10))
    check("a bed fully covered still yields an area", autocrop_sel_mm(full) is None
          or close(autocrop_sel_mm(full)[2], BED_W_MM, 3))


def test_paths():
    print("path conversion")
    cyg = to_cygpath(r"C:\Users\me\Scans\a.png")
    check("windows path to cygwin", cyg == "/cygdrive/c/Users/me/Scans/a.png", cyg)
    back = from_cygpath(cyg)
    check("cygwin path back to windows", back == r"C:\Users\me\Scans\a.png", back)


def test_labels():
    print("labels")
    check("full-bed label", "full bed" in describe_sel(None), describe_sel(None))
    check("selection label shows size and offset",
          "100 x 150 mm" in describe_sel((10.0, 20.0, 100.0, 150.0)),
          describe_sel((10.0, 20.0, 100.0, 150.0)))


def test_backends():
    print("backend detection")
    info = parse_device_list(DEVICES["plustek"])
    check("plustek device line is parsed",
          info is not None and info[0] == "plustek" and "N670U" in info[2], str(info))
    info = parse_device_list(DEVICES["artec_eplus48u"])
    check("artec_eplus48u device line is parsed",
          info is not None and info[0] == "artec_eplus48u"
          and info[2] == "Trust Easy Webscan 19200 flatbed scanner", str(info))
    real = ("\ndevice `artec_eplus48u:libusb:001:007' is a Trust Easy Webscan 19200 "
            "flatbed scanner\n")
    check("real scanimage formatting (backticks, leading newline)",
          parse_device_list(real) == ("artec_eplus48u", "libusb:001:007",
                                      "Trust Easy Webscan 19200 flatbed scanner"))
    check("no device -> None", parse_device_list("No scanners were identified.") is None)
    check("a known backend wins over an unknown one",
          parse_device_list("device `net:x' is a Foo\n" + DEVICES["plustek"])[0] == "plustek")
    for name, prof in BACKENDS.items():
        check(f"{name}: preview DPI is in its own DPI list",
              str(prof["preview_dpi"]) in prof["dpi"])
        check(f"{name}: default 300 DPI is available", "300" in prof["dpi"])
    check("the mock artec help matches the app's fixed list",
          parse_dpi_choices(HELP_RESOLUTION["artec_eplus48u"]) == BACKENDS["artec_eplus48u"]["dpi"])
    check("mock and app agree on the artec DPI list",
          [str(d) for d in ALLOWED_DPI["artec_eplus48u"]] == BACKENDS["artec_eplus48u"]["dpi"])
    check("every mock device is a known backend",
          all(parse_device_list(line)[0] in BACKENDS for line in DEVICES.values()))


def test_dpi_choices():
    print("resolution discovery")
    cases = (
        ("range up to 600", "    --resolution 50..600dpi [50]",
         ["75", "150", "300", "600"]),
        ("range up to 1200", "    --resolution 50..1200dpi [50]",
         ["75", "150", "300", "600", "1200"]),
        ("range up to 2400", "    --resolution 50..2400dpi [50]",
         ["75", "150", "300", "600", "1200", "2400"]),
        ("max between two steps", "    --resolution 50..800dpi [50]",
         ["75", "150", "300", "600"]),
        ("step 1 keeps every value", "    --resolution 50..600dpi (in steps of 1) [50]",
         ["75", "150", "300", "600"]),
        ("a step excludes values off the grid", "    --resolution 0..600dpi (in steps of 100) [50]",
         ["300", "600"]),
        ("fixed-point values", "    --resolution 50.00..1200.00dpi [50]",
         ["75", "150", "300", "600", "1200"]),
        ("word list is taken as is", "    --resolution 50|100|300|1200dpi [300]",
         ["50", "100", "300", "1200"]),
        ("automatic prefix", "    --resolution auto|75..600dpi [auto]",
         ["75", "150", "300", "600"]),
        ("inactive option is still parsed", "    --resolution 50..600dpi [inactive]",
         ["75", "150", "300", "600"]),
    )
    for name, line, expected in cases:
        got = parse_dpi_choices("Options specific to device:\n" + line + "\n")
        check(name, got == expected, str(got))
    check("generic scanimage usage has no choices",
          parse_dpi_choices("Usage: scanimage [OPTION]...\n--mode something") is None)
    check("garbage in the values is not fatal",
          parse_dpi_choices("    --resolution a..bdpi [1]") is None)
    check("a range with no usable step is unknown",
          parse_dpi_choices("    --resolution 10..50dpi [10]") is None)


def test_scan_size():
    print("scan size and timeout")
    check("1200 DPI full bed is about 142 Mpx",
          142_000_000 < scan_pixels(1200) < 143_000_000, str(scan_pixels(1200)))
    check("1200 DPI full-bed colour is about 430 MB",
          420_000_000 < scan_bytes(1200, "Color") < 435_000_000, str(scan_bytes(1200, "Color")))
    check("grey is a third of colour",
          scan_bytes(600, "Gray") == scan_bytes(600, "Color") // 3)
    check("short scans keep the minimum timeout",
          scan_timeout(75, "Color") == scanner_app.SCAN_TIMEOUT_MIN_S)
    check("1200 DPI full-bed colour gets over two hours",
          scan_timeout(1200, "Color") > 2 * 3600, str(scan_timeout(1200, "Color")))
    check("a small selection at 1200 DPI keeps the minimum timeout",
          scan_timeout(1200, "Color", (0, 0, 30, 30)) == scanner_app.SCAN_TIMEOUT_MIN_S)
    check("600 DPI full bed is still displayed on screen",
          scan_pixels(600) <= scanner_app.MAX_ONSCREEN_PIXELS, str(scan_pixels(600)))
    check("1200 DPI full bed is not loaded for display",
          scan_pixels(1200) > scanner_app.MAX_ONSCREEN_PIXELS)


def test_firmware():
    print("firmware")
    import tempfile
    tmp = tempfile.mkdtemp(prefix="scc_fw_")
    home = os.path.join(tmp, "home")
    fwdir = os.path.join(tmp, "bundle", "artec_eplus48u")
    os.makedirs(home)
    saved = (scanner_app.FIRMWARE_HOME, scanner_app.FIRMWARE_DIR)
    scanner_app.FIRMWARE_HOME, scanner_app.FIRMWARE_DIR = home, fwdir
    try:
        check("nothing found in an empty folder", find_firmware(home) is None)
        check("missing folder is handled", find_firmware(os.path.join(tmp, "nope")) is None)
        check("not ready without any file", firmware_ready() is False)
        src = os.path.join(home, "artec48.USB")      # wrong case, as users type it
        with open(src, "wb") as fh:
            fh.write(b"\x00" * 8192)
        check("firmware found case-insensitively", find_firmware(home) == src)
        check("ready once the file is next to the exe", firmware_ready() is True)
        dst = os.path.join(fwdir, FIRMWARE_NAMES[0])
        check("copied into the backend folder with the exact conf spelling",
              os.path.isfile(dst) and os.path.getsize(dst) == 8192, dst)
        check("ready is idempotent", firmware_ready() is True)
        elsewhere = os.path.join(tmp, "1200.usb")
        with open(elsewhere, "wb") as fh:
            fh.write(b"\x01" * 16)
        out = install_firmware(elsewhere)
        check("install from elsewhere lands in the backend folder",
              out == os.path.join(fwdir, "1200.usb") and os.path.isfile(out))
        check("...and is kept next to the exe", os.path.isfile(os.path.join(home, "1200.usb")))
    finally:
        scanner_app.FIRMWARE_HOME, scanner_app.FIRMWARE_DIR = saved
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for fn in (test_geometry, test_selection, test_area_args, test_autocrop,
               test_paths, test_labels, test_backends, test_dpi_choices,
               test_scan_size, test_firmware):
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: " + ", ".join(FAILURES))
        sys.exit(1)
    print("all checks passed")
