"""
Drop-in replacement for scanimage.exe, for developing without the scanner.

It accepts the same options ScannerCanoScan passes (-L, --mode, --resolution,
-l/-t/-x/-y, --format, -o), simulates a flatbed with a document lying on it,
and renders exactly the requested region. That makes the whole UI - preview,
area selection, auto-crop, output formats - testable on any machine.

Usage:
    set SCANNERCANOSCAN_SCANIMAGE=<repo>\\tools\\mock_scanimage.py
    python scanner_app.py

Every call is appended to %TEMP%\\mock_scanimage_calls.log (override with
SCANNERCANOSCAN_MOCK_LOG), so you can check the geometry actually requested.

SCANNERCANOSCAN_MOCK_DEVICE selects the simulated scanner: "plustek" (default,
Canon N670U), "plustek_lide30" (Canon LiDE 30), "plustek_nohelp" (a plustek
scanner whose --help fails) or "artec_eplus48u" (Trust Easy Webscan 19200). The
artec one only accepts its fixed resolution list, like the real backend.

The --resolution lines follow scanimage's format, but the plustek maximums are
assumptions: what the real backend reports per model needs the real hardware.
"""

import os
import sys
import tempfile

from PIL import Image, ImageDraw

BED_W_MM = 215.0
BED_H_MM = 297.0

# The simulated document on the glass: a 5x7" photo, not centred, so that a
# wrong coordinate origin or a mirrored axis shows up immediately.
DOC_MM = (30.0, 45.0, 127.0, 178.0)   # left, top, width, height

BG_LEVEL = 244            # empty glass, lid closed
DEVICES = {
    "plustek": ("device `plustek:libusb:001:002' is a Canon "
                "CanoScan N670U/N676U/LiDE20 flatbed scanner"),
    "artec_eplus48u": ("device `artec_eplus48u:libusb:001:003' is a Trust "
                       "Easy Webscan 19200 flatbed scanner"),
    "plustek_lide30": ("device `plustek:libusb:001:004' is a Canon "
                       "CanoScan N1240U/LiDE30 flatbed scanner"),
    "plustek_nohelp": ("device `plustek:libusb:001:005' is a Canon "
                       "CanoScan N670U/N676U/LiDE20 flatbed scanner"),
}
HELP_RESOLUTION = {
    "plustek": "--resolution 50..600dpi [50]",
    "plustek_lide30": "--resolution 50..1200dpi [50]",
    "artec_eplus48u": "--resolution 50|100|200|300|600|1200dpi [300]",
}
# The real artec_eplus48u backend has a fixed word list; plustek takes a range.
ALLOWED_DPI = {"artec_eplus48u": (50, 100, 200, 300, 600, 1200)}


def device():
    return os.environ.get("SCANNERCANOSCAN_MOCK_DEVICE", "plustek")


def log_call(argv):
    path = os.environ.get("SCANNERCANOSCAN_MOCK_LOG") or os.path.join(
        tempfile.gettempdir(), "mock_scanimage_calls.log")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(" ".join(argv) + "\n")


def from_cygpath(path):
    """/cygdrive/c/dir/file -> C:\\dir\\file"""
    if path.startswith("/cygdrive/"):
        rest = path[len("/cygdrive/"):]
        drive, _, tail = rest.partition("/")
        return f"{drive.upper()}:\\" + tail.replace("/", "\\")
    return path


def parse_args(argv):
    opts = {"mode": "Color", "resolution": 75, "format": "png", "output": None,
            "l": 0.0, "t": 0.0, "x": BED_W_MM, "y": BED_H_MM}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--format="):
            opts["format"] = a.split("=", 1)[1].lower()
        elif a == "--mode":
            opts["mode"] = argv[i + 1]; i += 1
        elif a == "--resolution":
            opts["resolution"] = int(float(argv[i + 1])); i += 1
        elif a in ("-o", "--output-file"):
            opts["output"] = from_cygpath(argv[i + 1]); i += 1
        elif a in ("-l", "-t", "-x", "-y"):
            opts[a[1:]] = float(argv[i + 1]); i += 1
        i += 1
    return opts


def render(opts):
    """Render the requested region of the simulated flatbed."""
    px_per_mm = opts["resolution"] / 25.4
    w = max(1, round(opts["x"] * px_per_mm))
    h = max(1, round(opts["y"] * px_per_mm))
    img = Image.new("RGB", (w, h), (BG_LEVEL, BG_LEVEL, BG_LEVEL))
    draw = ImageDraw.Draw(img)

    # Document position relative to the requested region.
    dl, dt, dw, dh = DOC_MM
    x0 = (dl - opts["l"]) * px_per_mm
    y0 = (dt - opts["t"]) * px_per_mm
    x1 = x0 + dw * px_per_mm
    y1 = y0 + dh * px_per_mm
    draw.rectangle([x0, y0, x1, y1], fill=(52, 96, 168), outline=(20, 30, 60), width=2)

    # A few features inside it, so a cropped scan is visually recognisable.
    step = max(4, int((y1 - y0) / 14))
    for n, yy in enumerate(range(int(y0) + step, int(y1) - step, step)):
        pad = (x1 - x0) * (0.08 + 0.05 * (n % 3))
        draw.rectangle([x0 + pad, yy, x1 - pad, yy + step * 0.35], fill=(232, 236, 245))
    draw.line([x0, y0, x1, y1], fill=(255, 128, 0), width=3)

    if opts["mode"].lower().startswith("gray"):
        img = img.convert("L")
    elif opts["mode"].lower().startswith("line"):
        img = img.convert("L").point(lambda p: 255 if p > 128 else 0).convert("1")
    return img


def main(argv):
    log_call(argv)
    if "-L" in argv or "--list-devices" in argv:
        print(DEVICES[device()])
        return 0
    if "--help" in argv:
        print("Usage: scanimage [OPTION]...\n")
        line = HELP_RESOLUTION.get(device())
        if not line:
            sys.stderr.write("scanimage: open of device failed: Error during device I/O\n")
            return 1
        print("Options specific to device:\n  Scan Mode:\n"
              "    --mode Lineart|Gray|Color [Color]\n"
              f"    {line}\n        Sets the resolution of the scanned image.")
        return 0

    opts = parse_args(argv)
    if not opts["output"]:
        sys.stderr.write("mock_scanimage: no -o output file given\n")
        return 1
    allowed = ALLOWED_DPI.get(device())
    if allowed and opts["resolution"] not in allowed:
        sys.stderr.write(f"mock_scanimage: {device()} rejects {opts['resolution']} dpi "
                         f"(allowed: {allowed})\n")
        return 1

    img = render(opts)
    fmt = {"png": "PNG", "jpeg": "JPEG", "jpg": "JPEG",
           "tiff": "TIFF", "pdf": "PDF"}.get(opts["format"], "PNG")
    if fmt in ("JPEG", "PDF") and img.mode != "RGB":
        img = img.convert("RGB")

    os.makedirs(os.path.dirname(os.path.abspath(opts["output"])), exist_ok=True)
    img.save(opts["output"], fmt)
    sys.stderr.write(
        f"mock_scanimage: {img.size[0]}x{img.size[1]} px, {opts['resolution']} dpi, "
        f"area l={opts['l']} t={opts['t']} x={opts['x']} y={opts['y']} mm\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
