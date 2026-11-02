# Changelog

## 1.2.0

Added:
- **GT6816 scanners** (Trust Easy Webscan 19200, Trust 240H Easy Webscan Gold,
  Artec E+ 48U / E+ Pro, Medion MD 9693/9705/4394, Memorex MEM 48U, UMAX
  AstraSlim SE / 1200 SE, Yakumo Scan50): the SANE `artec_eplus48u` backend is
  now bundled next to `plustek`. The app detects which backend answers and
  adapts the resolution list (50–1200 DPI on GT6816) and the preview (50 DPI).
- **Firmware handling** for those scanners: they need the proprietary
  `Artec48.usb` from their original driver. The app asks for it once, keeps a
  copy next to the executable and installs it where the backend expects it on
  every start. The firmware is not distributed with this project.
- **Resolution list per scanner** on LM983x models: read from the backend for
  the connected scanner instead of a fixed 75–600 DPI list, so models that
  support it can go above 600 DPI (requested for the LiDE 30). If the scanner
  does not report a range the list stays 75–600 DPI. The settings panel shows
  which of the two happened.
- The scan timeout grows with resolution, mode and area (it was always 15
  minutes), and scans above 40 megapixels are saved without being loaded on
  screen.
- The detected scanner model is shown in the settings panel.
- README: step-by-step guide to remove the WinUSB driver and go back to the
  original state (Device Manager, `pnputil`, libwdi certificate).
- The simulated scanner can impersonate a Trust Easy Webscan 19200
  (`SCANNERCANOSCAN_MOCK_DEVICE=artec_eplus48u`); both test suites cover the
  backend switch and the firmware logic.

Unchanged for LM983x scanners (Canon N670U & co.): same backend build, same
scan arguments, same 75 DPI preview as 1.1.0.

Not yet verified on hardware: nobody has run the artec_eplus48u backend on
Windows so far, and the resolution range the plustek backend reports per model
has not been seen on a real scanner. See DEVELOPMENT.md §10.

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
