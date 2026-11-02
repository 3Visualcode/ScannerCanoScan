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

Since v1.2 (2026-09-11) a second family is supported without changing the
architecture: the **GT6816** scanners (Trust Easy Webscan 19200, Artec E+ 48U
and re-badges, USB vendor `05D8`) through the SANE `artec_eplus48u` backend.
Added on request for a Trust Easy Webscan 19200 owner; not tested on hardware
by the author (see §10).

## 2. Final architecture (the active one)

```
USB scanner → WinUSB driver (Microsoft, installed with Zadig)
           → libusb (cygusb-1.0.dll)
           → SANE backend 1.0.32 (Cygwin port for Windows)
                plustek         LM9831/2/3   (Canon N670U, LiDE 20, ...)
                artec_eplus48u  GT6816       (Trust 19200, Artec E+ 48U, ...)
           → scanimage.exe
           → Python/tkinter GUI (scanner_app.py)
           → PyInstaller onefile = ScannerCanoScan.exe (~21 MB)
```

- **SANE** = open-source scanner driver framework (Linux project); the
  `plustek` backend supports the LM983x chips, i.e. exactly the N670U; the
  `artec_eplus48u` backend supports the GT6816 chip.
- **Windows port**: [revvv/sane-backends-cygwin](https://github.com/revvv/sane-backends-cygwin).
  `scanimage.exe`, `cygsane-1.dll` and the plustek DLL come from release
  **1.0.32 "plustek"** (2021-02-27, tested upstream on a LiDE 20 = same chip).
  `cygsane-artec_eplus48u-1.dll` and `artec_eplus48u.conf` come from release
  **1.0.32-all** (2021-03-04, "UNTESTED" upstream, same source tree and
  toolchain). Backend DLLs only import `cygwin1.dll` and `cygusb-1.0.dll`, so
  mixing the two releases is safe; the rest of the -all tarball (80 other
  backends, its own scanimage) is deliberately NOT used.
- **Cygwin DLLs** harvested from a silent Cygwin install (Cygwin is NOT
  present on the build system: it was installed into a temporary folder just
  for the harvest): `cygwin1.dll, cygusb-1.0.dll, cygjpeg-8.dll,
  cygpng16-16.dll, cygz.dll, cyggcc_s-seh-1.dll` — careful:
  `cyggcc_s-seh-1.dll` does NOT show up as a direct dependency; it is needed
  by `cygjpeg-8.dll` (missing → exit 0xC0000135).
- **Cygwin layout**: the root `/` = parent folder of `bin\cygwin1.dll`.
  That is why `sane-win64\` replicates `usr\local\etc\sane.d` (config) and
  `usr\local\lib\sane` (backend DLLs). Do not move files around inside the tree.
- `dll.conf` lists exactly `plustek` and `artec_eplus48u` (every extra backend
  = probing errors and slower start-up; keep it minimal).
- **Backend selection** is done by the GUI, not by configuration: it runs
  `scanimage -L`, parses the `device \`backend:...' is a ...` line
  (`parse_device_list()`), and switches the UI profile in `BACKENDS`
  (resolution list, preview DPI, firmware requirement). The plustek path is
  unchanged: same arguments, same 75 DPI preview, same DPI list as v1.1.
- **GT6816 firmware**: the artec_eplus48u backend uploads `Artec48.usb` (8192
  bytes; `1200.usb` for the E+ Pro / AstraSlim 1200 SE) on every `sane_open`.
  The conf points to `/usr/local/share/sane/artec_eplus48u/Artec48.usb`, i.e.
  `sane-win64\usr\local\share\sane\artec_eplus48u\` (Cygwin root = `sane-win64`).
  The file is proprietary and never enters the repo (`*.usb` is git-ignored):
  the user keeps it next to the exe (`FIRMWARE_HOME`), and `firmware_ready()`
  copies it into the bundle folder (`FIRMWARE_DIR`) at every start, because
  the PyInstaller temp dir is recreated on every run. Missing file → the GUI
  opens a file dialog once (`_ask_firmware`).
- **Driver**: WinUSB installed via Zadig on device `04A9:220D`
  (USBDevice class). One time per PC. Zadig is shipped in the folder.

## 3. Folder contents

| File/dir | Role |
|---|---|
| `ScannerCanoScan.exe` | Final product, self-contained |
| `zadig.exe` | WinUSB driver installer (v2.9, from zadig.akeo.ie) |
| `scanner_app.py` | GUI source (single file; stdlib + Pillow) |
| `ScannerCanoScan.spec` | PyInstaller recipe (UPX off, version resource on) |
| `version_info.txt` | Windows version resource — keep in sync with `APP_VERSION` |
| `build.ps1` | Test + build + optional code signing |
| `tools\mock_scanimage.py` | Simulated scanner, for developing without hardware |
| `tools\selftest.py` | Headless checks: geometry, auto-crop, paths |
| `tools\smoketest.py` | End-to-end GUI run against the simulated scanner |
| `sane-win64\` | Native SANE: needed for source runs and rebuilds |
| `sane-win64\usr\local\share\sane\artec_eplus48u\` | Where the GT6816 firmware is copied at run time (only a README in git) |
| `Artec48.usb` (next to the exe, optional) | Proprietary GT6816 firmware supplied by the user; git-ignored |
| `Scans\` | Output (`scan_YYYY-MM-DD_HH-MM-SS.ext`) |
| `README.md` | User manual + distribution instructions |
| `DEVELOPMENT.md` | This file |

## 4. Critical technical details (gotchas)

1. **Scan area**: by default the plustek backend scans ONLY 103×76 mm (one
   corner). Passing `-l 0 -t 0 -x 215 -y 297` is mandatory for the full A4
   flatbed. Since v1.1 the geometry is built by `area_args()` from the current
   selection; with no selection it falls back to the full bed. In SANE, `-l/-t`
   are the top-left corner and **`-x/-y` are width and height**, not the far
   corner — getting that wrong silently scans the wrong region. Sheetfed models
   (TravelScan, Strobe XP100) may have a smaller maximum area — if scanimage
   rejects the geometry, the area needs to be made model-dependent.
   **Not yet verified on hardware** (see §10): that the backend's origin is the
   top-left of the glass with no mirroring, and that it does not quantise
   arbitrary `-l/-t` values.
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
   (`--format=...`); the GUI performs no conversions. The on-screen display of
   a finished scan is still PNG only (the other formats are not re-read).
8. **Pillow** is a dependency since v1.1 (preview scaling, auto-crop). It is
   the only non-stdlib import; `tk.PhotoImage` could not do either.
9. **Preview is always the full bed**, whatever the selection — it is the
   surface you select on. Only `SCAN` honours the selection.
10. **Same-second scans overwrite each other**: the filename has one-second
    resolution. Only reachable by scripting the app, harmless in the GUI.
11. **artec_eplus48u resolutions are a fixed list**: 50/100/200/300/600/1200.
    The backend rounds anything else to the nearest entry (SANE word-list
    constraint), so 75 and 150 would silently become 50/100 and 100/200 — the
    GUI therefore has a DPI list per backend (`BACKENDS[...]["dpi"]`) and a
    50 DPI preview on that backend. The mock rejects invalid values outright
    so the tests catch a wrong list.
12. **artec_eplus48u geometry**: max area 216×297 mm, and internally the
    backend mirrors the X origin (`x0 = 216 - brx`, see `sane_start` in
    `artec_eplus48u.c`). This is transparent through `-l/-t/-x/-y`, but it is
    another reason the origin test in §10 must be run on that hardware too.
    We keep the common 215×297 mm bed for both backends (1 mm less on the
    right edge is irrelevant).
13. **Firmware upload happens on every scanimage call** (preview and scan):
    `sane_open` → `download_firmware_file`. It takes well under a second, and
    the backend comments say re-checking whether it is already loaded is not
    worth it. Nothing to cache.

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

Prerequisites: Python 3.10+ (3.14 used), `pip install pyinstaller pillow`.

```powershell
cd ScannerCanoScan
.\build.ps1              # tests + build
.\build.ps1 -SkipTests   # build only
```

Resulting exe in `dist\ScannerCanoScan.exe` → copy it to the folder root.
Development run without building: `python scanner_app.py` (uses the
`sane-win64\` folder next to the source).

### 6.1 Code signing

Unsigned, SmartScreen shows "Unknown publisher" and users need
*More info → Run anyway*. Signing replaces that with **Host Service srl**.
`build.ps1` handles it; you only have to obtain a certificate. Self-signed
certificates are useless here — SmartScreen ignores them.

| Option | Indicative cost | Notes |
|---|---|---|
| **Azure Trusted Signing** | ~10 USD/month | Best fit: needs a registered company with a verifiable history (~3 years). No hardware token, works in CI. `build.ps1 -TrustedSigningMetadata .\trusted-signing.json` |
| OV certificate | ~250–500 €/year | Hardware token/HSM mandatory since the 2023 CA/Browser rules. SmartScreen reputation builds up over downloads |
| EV certificate | ~350–700 €/year | Hardware token. Immediate SmartScreen reputation |
| SignPath Foundation | free | Open-source projects only, application + approval needed |

Prices change — verify before buying. Once a certificate is in the Windows
store (typical for token-based OV/EV), `build.ps1 -CertSubject "Host Service srl"`
is enough.

Related: UPX compression is disabled in the spec on purpose — packed
executables trigger antivirus false positives, which defeats the point of
signing.

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
- Model-dependent scan area (needed for sheetfed models, see §4.1).
- More SANE backends from the -all release (gt68xx, genesys, ...): the
  mechanism is in place — drop the DLL + conf into `sane-win64`, add the
  backend to `dll.conf` and a profile to `BACKENDS`. Only do it on request,
  with a tester who owns the hardware.
- UI language selection (currently English only).
- Rotate / straighten the auto-detected document (currently axis-aligned only).
- Display finished scans in formats other than PNG.

Done in v1.1: area selection, auto-crop, version resource, signing pipeline.
Done in v1.2: second backend (artec_eplus48u / GT6816), per-backend DPI list,
firmware handling.

## 9. Developing without a scanner

`tools\mock_scanimage.py` is a drop-in replacement for `scanimage.exe`. It
accepts the same options, simulates a flatbed with a 127×178 mm document lying
at offset (30, 45) mm — deliberately off-centre, so a mirrored or misplaced
origin is obvious — and renders exactly the region requested.

```powershell
$env:SCANNERCANOSCAN_SCANIMAGE = "$PWD\tools\mock_scanimage.py"
python scanner_app.py          # the whole GUI, no hardware
Remove-Item Env:\SCANNERCANOSCAN_SCANIMAGE
```

Every call is logged to `%TEMP%\mock_scanimage_calls.log`
(override with `SCANNERCANOSCAN_MOCK_LOG`), so you can check the geometry that
was actually requested.

`SCANNERCANOSCAN_MOCK_DEVICE=artec_eplus48u` makes the mock pretend to be a
Trust Easy Webscan 19200 (default: the Canon). In that mode it only accepts
the artec resolution list, like the real backend. To exercise the firmware
dialog from source, run the GUI with that variable and no `Artec48.usb` next
to `scanner_app.py`; any 8 KB file named `Artec48.usb` satisfies the mock
(the real backend, of course, needs the real one).

The override only accepts an `.exe` in the packaged build: inside PyInstaller
`sys.executable` is the app itself, not a Python interpreter, so a `.py` mock
would relaunch the GUI. `scanimage_cmd()` raises instead.

Two test suites, both hardware-free:

```powershell
python tools\selftest.py    # geometry, auto-crop, path conversion - no GUI
python tools\smoketest.py   # real ScannerApp driven end to end (a window flashes)
```

`selftest.py` covers the pure functions (`canvas_to_mm`, `rect_to_sel_mm`,
`area_args`, `autocrop_sel_mm`, `to_cygpath`, `parse_device_list`, the
firmware helpers). `smoketest.py` drives the actual Tk app: preview →
auto-crop → simulated mouse drag → scan, then verifies the geometry that
reached scanimage and the pixel size of every output format; then it switches
the mock to the artec device and checks the backend switch, the DPI list, the
firmware-missing state and the 50 DPI preview, and finally switches back to
the Canon. The firmware test uses temp folders, never the real `sane-win64`.

## 10. What still needs the real device

Everything above is simulated, so these assumptions remain unproven:

1. The plustek origin is the top-left of the glass, with no mirrored axis.
   Test: put a small object in one corner, select it from the preview, scan,
   check you got that corner and not another.
2. The backend accepts arbitrary `-l/-t/-x/-y` values without quantising or
   rounding them to a grid.
3. Very small areas (a few mm) do not make the backend fail or hang.
4. Scan time really does drop proportionally to the selected area.
5. Auto-crop tolerance (18/255 on the grey level) is right for a real glass
   with the lid closed. Real backgrounds are noisier than the simulated one;
   if auto-crop grabs the whole bed, raise `tolerance` in `autocrop_sel_mm()`.

Resolution list on LM983x models (`parse_dpi_choices`, from
`scanimage --help -d DEVICE`). The parser matches the format strings in the
bundled `scanimage.exe` and falls back correctly when the device cannot be
opened, but no scanner has answered it yet, so the plustek maximums in the mock
are assumptions:

- The maximum each model reports. It may exceed the optical resolution, in which
  case the top entry is interpolated. Compare detail with the step below it.
- That a real scan completes above 600 DPI over USB 1.1 and WinUSB.
- Whether `SCAN_MIN_BYTES_PER_S` (50 KB/s) leaves enough time on a full-bed scan.

GT6816 / artec_eplus48u specific (nobody has run this backend on Windows yet;
revvv marks the -all build "UNTESTED" and upstream marks the backend "ALPHA,
tested on Linux only"):

6. `scanimage -L` lists the Trust 19200 through WinUSB + libusb at all.
   If not: `set SANE_DEBUG_ARTEC_EPLUS48U=5` and `SANE_DEBUG_SANEI_USB=5`.
7. The firmware upload works over WinUSB (bulk transfers to the GT6816,
   `artec48u_download_firmware` verifies each block by reading it back — a
   "mismatch at block" message means the USB path is the problem, not the file).
8. Points 1–5 above, repeated on this scanner: origin, arbitrary geometry,
   small areas, speed, auto-crop tolerance. Point 1 matters more here because
   of the mirrored X origin inside the backend (§4.12).
9. Preview at 50 DPI is enough to select an area; if it is too coarse, change
   `preview_dpi` to 100 in `BACKENDS["artec_eplus48u"]`.
10. Default gamma/offset/exposure in `artec_eplus48u.conf` are the upstream
    ones for the Artec E+ 48U. If the Trust scans come out too dark/light,
    those are the knobs (`masterGamma`, `*Offset`, `*Exposure`).
