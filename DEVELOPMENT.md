# DEVELOPMENT — ScannerCanoScan internals

Developer handoff document: full project context, decisions taken, problems
encountered and how to pick the work back up. Originally written 2026-07-06
for the Canon CanoScan N670U on Windows 11.

---

## 1. Goal

Canon CanoScan N670U (year 2001, USB 1.1, VID:PID `04A9:220D`, National
Semiconductor **LM9833** chip): Canon never released 64-bit Windows drivers.
The only commercial solution is VueScan (paid).

Goal achieved: **free scanning software, 100% native Windows, distributable
as a single `ScannerCanoScan.exe`** (original explicit requirement: hand over
nothing but one exe).

The same applies to every other LM9831/2/3 scanner supported by the SANE
plustek backend — see the compatibility table in [README.md](README.md).

## 2. Final architecture (the active one)

```
USB scanner → WinUSB driver (Microsoft, installed with Zadig)
           → libusb (cygusb-1.0.dll)
           → SANE plustek backend 1.0.32 (Cygwin port for Windows)
           → scanimage.exe
           → Python/tkinter GUI (scanner_app.py)
           → PyInstaller onefile = ScannerCanoScan.exe (15 MB)
```

- **SANE** = open-source scanner driver framework (Linux project); the
  `plustek` backend supports the LM983x chips, i.e. exactly the N670U.
- **Windows port**: [revvv/sane-backends-cygwin](https://github.com/revvv/sane-backends-cygwin),
  release **1.0.32 "plustek"** (2021-02-27, tested upstream on a LiDE 20 =
  same chip).
- **Cygwin DLLs** harvested from a silent Cygwin install (Cygwin is NOT
  present on the build system: it was installed into a temporary folder just
  for the harvest): `cygwin1.dll, cygusb-1.0.dll, cygjpeg-8.dll,
  cygpng16-16.dll, cygz.dll, cyggcc_s-seh-1.dll` — careful:
  `cyggcc_s-seh-1.dll` does NOT show up as a direct dependency; it is needed
  by `cygjpeg-8.dll` (missing → exit 0xC0000135).
- **Cygwin layout**: the root `/` = parent folder of `bin\cygwin1.dll`.
  That is why `sane-win64\` replicates `usr\local\etc\sane.d` (config) and
  `usr\local\lib\sane` (backend DLLs). Do not move files around inside the tree.
- `dll.conf` contains only `plustek` (other backends = errors/slowness).
- **Driver**: WinUSB installed via Zadig on device `04A9:220D`
  (USBDevice class). One time per PC. Zadig is shipped in the folder.

## 3. Folder contents

| File/dir | Role |
|---|---|
| `ScannerCanoScan.exe` | Final product, self-contained |
| `zadig.exe` | WinUSB driver installer (v2.9, from zadig.akeo.ie) |
| `scanner_app.py` | GUI source (single file, stdlib only) |
| `sane-win64\` | Native SANE: needed for source runs and rebuilds |
| `Scans\` | Output (`scan_YYYY-MM-DD_HH-MM-SS.ext`) |
| `README.md` | User manual + distribution instructions |
| `DEVELOPMENT.md` | This file |

## 4. Critical technical details (gotchas)

1. **Scan area**: by default the plustek backend scans ONLY 103×76 mm (one
   corner). Passing `-l 0 -t 0 -x 215 -y 297` is mandatory for the full A4
   flatbed. Already done via `FULL_AREA` in scanner_app.py. Sheetfed models
   (TravelScan, Strobe XP100) may have a smaller maximum area — if scanimage
   rejects the geometry, the area needs to be made model-dependent.
2. **Paths for scanimage**: it is a Cygwin binary → Windows paths must be
   converted to `/cygdrive/c/...` (function `to_cygpath`).
3. **cwd**: scanimage should be launched with `cwd = sane-win64\bin` (DLLs
   are resolved from the exe's own directory, but better safe than sorry).
4. **PyInstaller onefile**: on every start it extracts `sane-win64` into
   `%TEMP%` (`sys._MEIPASS`). In the source: `BUNDLE_DIR` vs `APP_DIR`
   (scans go next to the exe, not into the temp dir).
5. **Speed**: USB 1.1 scanner → 75 DPI ~20 s, 300 DPI a few minutes,
   600 DPI many minutes. Cold lamp = first scan slower. Normal.
6. **SmartScreen**: unsigned exe → warning on first run on new PCs.
   "More info → Run anyway".
7. **Formats**: PNG/JPEG/PDF/TIFF are produced directly by scanimage
   (`--format=...`); the GUI performs no conversions. On-screen preview is
   PNG only (tk.PhotoImage reads only PNG/GIF).

## 5. Project history and dead ends (do NOT retrace them)

### Attempt 1: WSL2 + usbipd (worked, but fragile — ABANDONED)
- usbipd-win 5.3.0 forwarded the scanner to Ubuntu WSL2 with sane-utils 1.2.1.
- Cascading problems:
  a. **USBPcap** (Wireshark's USB capture filter) incompatible with usbipd:
     the connection dropped ~12 s after attach with Win32 error 31
     ("device not functioning") in the usbipd event log.
     → USBPcap **permanently uninstalled** on 2026-07-06. Do NOT
     reinstall it. Wireshark stays fine (only loses USB capture).
  b. WSL shuts the distro down when idle → USB attach constantly lost;
     required a keepalive process (`wsl sleep infinity`).
  c. `wsl.exe` invoked from Git Bash mangles `/tmp` paths (MSYS conversion)
     and produces unreadable interleaved output → use PowerShell.
- Leftovers still installed but UNUSED: usbipd-win (Windows), sane-utils
  (inside Ubuntu WSL). Removal optional, harmless.
- The usbipd bind for the scanner was removed (`usbipd unbind`).

### Why the native solution is better
No daemon, no attach, no VM: persistent WinUSB driver + SANE binaries ported
to Windows. Survives reboots and re-plugs.

## 6. How to rebuild the exe

Prerequisites: Python 3.10+ (3.14 used originally), PyInstaller 6.x
(`python -m pip install --user pyinstaller`).

```bat
cd ScannerCanoScan
python -m PyInstaller --onefile --windowed --name ScannerCanoScan ^
  --add-data "sane-win64;sane-win64" scanner_app.py
```

Resulting exe in `dist\ScannerCanoScan.exe` → copy it to the folder root.
Development run without building: `python scanner_app.py` (uses the
`sane-win64\` folder next to the source).

## 7. Quick diagnostics

```powershell
# Does the scanner have the right driver? (must report class USBDevice / WinUSB)
pnputil /enum-devices /connected | Select-String -Context 0,6 '04A9'

# Does SANE see it? (from inside the project folder)
.\sane-win64\bin\scanimage.exe -L
# expected: device 'plustek:libusb:NNN:NNN' is a Canon CanoScan N670U/N676U/LiDE20

# Test scan from the command line
.\sane-win64\bin\scanimage.exe --mode Color --resolution 75 `
  -l 0 -t 0 -x 215 -y 297 --format=png -o /cygdrive/c/Users/YOU/Desktop/test.png
```

Typical errors:
- `Operation not supported` on the USB device → WinUSB driver missing → Zadig.
- Exit `-1073741515` (0xC0000135) → Cygwin DLL missing next to scanimage.
- `no SANE devices found` with driver OK → USB cable/port, retry.

## 8. Future ideas (not requested, not started)

- Custom icon for the exe (`--icon file.ico`).
- Multi-page PDF (scanimage `--batch` + concatenation).
- Code-sign the exe to avoid SmartScreen.
- Automatic document-area cropping.
- Model-dependent scan area (needed for sheetfed models, see §4.1).
- UI language selection (currently English only).
