# Changelog

## 1.1.0

Added:
- **Scan area selection** — drag a rectangle on the preview to scan only that
  part of the glass. Works for any shape, including tall vertical strips. A
  single click, or *Reset to full area*, goes back to the whole bed. Because the
  scanner head only travels over the selected region, the scan is also faster.
- **Auto-crop** — detects the document on the glass from the preview and sets
  the scan area to it. Works with the lid closed (light background) and open
  (dark background).
- **Version number** — shown in the window title, in the settings panel, and in
  the file properties of the executable (publisher: Host Service srl).
- `build.ps1` — one command for tests, build and optional code signing.
- A simulated scanner (`tools\mock_scanimage.py`) plus two hardware-free test
  suites, so the GUI can be developed and verified without a device.

Changed:
- Preview and displayed scans are now rendered through Pillow: smooth scaling
  instead of integer subsampling, so the preview is sharper and fills the window.
- UPX compression disabled in the build: packed executables are a common source
  of antivirus false positives.
- Pillow is now a build dependency (`pip install pillow`).

Not yet verified on hardware: the scan-area geometry has been tested against a
simulated scanner only. See DEVELOPMENT.md §10.

## 1.0.0

First public release. Preview, full-A4 scan, Color/Grayscale/Lineart,
75–600 DPI, PNG/JPEG/PDF/TIFF output, single portable executable bundling the
SANE plustek backend for LM983x scanners.
