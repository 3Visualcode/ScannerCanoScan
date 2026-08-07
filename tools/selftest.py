"""
Headless checks for the geometry and auto-crop logic - no scanner, no GUI.

    python tools\\selftest.py

Covers what can be verified without hardware. What it cannot prove is that the
plustek backend interprets -l/-t/-x/-y with the same origin we assume
(top-left of the glass); that needs one run on the real device.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

from scanner_app import (BED_H_MM, BED_W_MM, area_args, autocrop_sel_mm,
                         canvas_to_mm, describe_sel, mm_to_canvas,
                         rect_to_sel_mm, to_cygpath)
from tools.mock_scanimage import from_cygpath

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


if __name__ == "__main__":
    for fn in (test_geometry, test_selection, test_area_args, test_autocrop,
               test_paths, test_labels):
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: " + ", ".join(FAILURES))
        sys.exit(1)
    print("all checks passed")
