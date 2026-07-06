# ScannerCanoScan

**Free, open-source scanning software for Windows 10/11 (64-bit) for old USB scanners based on the National Semiconductor LM9831/LM9832/LM9833 chips** — such as the Canon CanoScan N670U — that never got official 64-bit Windows drivers.

One single portable executable: **`ScannerCanoScan.exe`**. No installation, no WSL, no virtual machines, no paid software.

> Canon (and other vendors) abandoned these scanners around Windows XP. The only commercial option today is paid software. This project brings them back to life on modern Windows, for free, using the open-source [SANE](http://www.sane-project.org/) driver compiled natively for Windows.

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011%20(64--bit)-blue)
![License](https://img.shields.io/badge/GUI%20license-MIT-green)
![SANE](https://img.shields.io/badge/driver-SANE%20plustek-orange)

---

## ✨ Features

- **Preview** — quick 75 DPI scan shown on screen
- **Scan** — saves to the `Scans\` folder as `scan_DATE_TIME.ext`
- Modes: Color / Grayscale / Black & white
- Resolution: 75–600 DPI (these are USB 1.1 scanners — 600 DPI takes minutes)
- Output formats: PNG, JPEG, PDF, TIFF
- Full A4 flatbed area
- 100% portable: a single `.exe`, nothing else to install

## 🖨️ Supported scanners

The bundled driver is the SANE **plustek** backend, which supports all USB scanners built on the **LM9831 / LM9832 / LM9833** chips.

**Tested and confirmed working:**

| Scanner | USB ID (Vendor:Product) | Chip |
|---|---|---|
| Canon CanoScan **N670U / N676U** | `04A9:220D` | LM9833 |

**Supported by the same backend (should work — reports welcome!):**

| Vendor | Model | USB ID | Chip |
|---|---|---|---|
| Canon | CanoScan LiDE 20 | `04A9:220D` | LM9833 |
| Canon | CanoScan LiDE 25 | `04A9:2220` | LM9833 |
| Canon | CanoScan LiDE 30 | `04A9:220E` | LM9833 |
| Canon | CanoScan N1240U | `04A9:220E` | LM9833 |
| Canon | CanoScan N650U / N656U | `04A9:2206` | LM9832 |
| Canon | CanoScan N1220U | `04A9:2207` | LM9832 |
| Canon | CanoScan D660U | `04A9:2208` | LM9832 |
| Plustek | OpticPro U12 | `07B3:0010` | LM9831 |
| Plustek | OpticPro U24 | `07B3:0011` / `07B3:0015` | LM9831/2 |
| Plustek | OpticPro UT12 | `07B3:0013` / `07B3:0017` | LM9831/2 |
| Plustek | OpticPro UT16 / UT24 | `07B3:0017` | LM9832 |
| Epson | Perfection 1250 | `04B8:010F` | LM9832 |
| Epson | Perfection 1260 | `04B8:011D` | LM9832 |
| Hewlett-Packard | ScanJet 2100C | `03F0:0505` | LM9831 |
| Hewlett-Packard | ScanJet 2200C | `03F0:0605` | LM9832 |
| Mustek | BearPaw 1200 | `0400:1000` / `0400:1001` | LM9831/2 |
| Mustek | BearPaw 2400 | `0400:1001` | LM9832 |
| UMAX | 3400 / 3450 | `1606:0050` / `1606:0060` | LM9832 |
| UMAX | 5400 | `1606:0160` | LM9832 |
| Compaq | S4-100 | `049F:001A` | LM9832 |
| KYE / Genius | ColorPage HR6 V2 | `0458:2007` / `0458:2008` | LM9832 |
| KYE / Genius | ColorPage HR6A | `0458:2009` | LM9832 |
| KYE / Genius | ColorPage HR6X | `0458:2016` | LM9832 |
| KYE / Genius | ColorPage HR7 | `0458:2013` | LM9832 |
| KYE / Genius | ColorPage HR7LE | `0458:2015` | LM9832 |
| Syscan | TravelScan 662 | `0A82:6620` | LM9833 |
| Syscan | TravelScan 464 | `0A82:4600` | LM9833 |
| Visioneer | Strobe XP100 | `04A7:0427` | LM9833 |
| Portable Peripheral Co. | Q-Scan USB001 | `0A53:1000` | LM9832 |
| Portable Peripheral Co. | Q-Scan USB201 | `0A53:2000` | LM9832 |

Source: [SANE plustek backend documentation](http://www.sane-project.org/man/sane-plustek.5.html).

Notes:
- Only the **Canon N670U** has been tested by the author so far. All other models use the exact same driver code path, so they are expected to work. If you own one, please **open an issue** and report success/failure — the table will be updated.
- The scan area is currently fixed to A4 (215×297 mm). Small sheetfed models (e.g. TravelScan, Strobe XP100) may need a smaller area — open an issue if you hit an error.
- In the Zadig step below, select **your** scanner's USB ID from this table.

## 🚀 Installation (2 minutes)

You need two files from the [Releases](../../releases) page: `ScannerCanoScan.exe` and `zadig.exe`.

1. Plug in the scanner via USB.
2. **One time only** — install the generic WinUSB driver:
   - Run `zadig.exe` ([Zadig](https://zadig.akeo.ie/) by Pete Batard)
   - Menu *Options* → *List All Devices*
   - Select your scanner (e.g. **CanoScan**, USB ID `04A9 220D` — check the table above)
   - Target driver: **WinUSB** → click *Install Driver*
3. Run `ScannerCanoScan.exe`. Done.

Notes:
- **SmartScreen** may warn you the first time (the exe is not code-signed): click *More info* → *Run anyway*.
- The WinUSB driver replaces any previous driver for the scanner (on modern 64-bit Windows there is no official one anyway). This is fully reversible from Device Manager.

## 🔧 How it works

```
USB scanner → WinUSB driver (Microsoft, installed via Zadig)
           → libusb (cygusb-1.0.dll)
           → SANE "plustek" backend 1.0.32 (Cygwin port for Windows)
           → scanimage.exe
           → Python/tkinter GUI (scanner_app.py)
           → PyInstaller onefile = ScannerCanoScan.exe
```

The executable bundles the open-source **SANE** scanner driver (plustek backend, for LM983x chips) compiled for Windows via the Cygwin port [revvv/sane-backends-cygwin](https://github.com/revvv/sane-backends-cygwin), together with the required Cygwin DLLs. The GUI (single-file Python/tkinter, standard library only) invokes `scanimage.exe` and saves the output.

## 🛠️ Building from source

Prerequisites: Python 3.10+ with tkinter, PyInstaller (`pip install pyinstaller`).

```bat
git clone https://github.com/3Visualcode/ScannerCanoScan.git
cd ScannerCanoScan
python -m PyInstaller --onefile --windowed --name ScannerCanoScan ^
  --add-data "sane-win64;sane-win64" scanner_app.py
```

The executable is produced in `dist\ScannerCanoScan.exe`.
Development run without building: `python scanner_app.py` (uses the `sane-win64\` folder next to the source).

## 🔍 Troubleshooting

- **"Scanner not detected"** → check the USB cable; then verify the driver: in Device Manager the scanner must appear under *USB Devices* with the WinUSB driver. If not, repeat the Zadig step.
- **Manual diagnostics** (from the project folder):
  ```
  sane-win64\bin\scanimage.exe -L
  ```
  Expected: `device 'plustek:libusb:NNN:NNN' is a Canon CanoScan N670U/N676U/LiDE20` (or your model).
- `Operation not supported` on the USB device → WinUSB driver missing → run Zadig.
- Exit code `-1073741515` (0xC0000135) → a Cygwin DLL is missing next to `scanimage.exe`.
- `no SANE devices found` with the driver OK → try another USB cable/port.
- First scan slower than usual → cold lamp warm-up. Normal for these scanners.

## ❤️ Support this project

This software is free and always will be. If it brought your old scanner back from the dead and saved you from buying a new one, consider a small donation — it keeps the project (and more dusty hardware) alive:

- 💸 **[Donate via PayPal](https://www.paypal.com/donate/?business=cirillomarco05%40gmail.com&currency_code=EUR)** (or send directly to `cirillomarco05@gmail.com`)
- 💖 **[GitHub Sponsors](https://github.com/sponsors/3Visualcode)**

Even just a ⭐ star on the repository or a compatibility report for your scanner model helps a lot!

## 📄 Licenses

| Component | License | Source |
|---|---|---|
| GUI (`scanner_app.py`) | MIT | this repository ([LICENSE](LICENSE)) |
| SANE backends (`scanimage.exe`, plustek) | GPL v2 (with SANE exception) | [sane-project.org](http://www.sane-project.org/), [revvv/sane-backends-cygwin](https://github.com/revvv/sane-backends-cygwin) |
| Cygwin runtime DLLs (`cygwin1.dll`, …) | LGPL v3 | [cygwin.com](https://cygwin.com/) |
| Zadig | GPL v3 | [zadig.akeo.ie](https://zadig.akeo.ie/) |

If you redistribute the executable, keep this file with it (it tells users where to find the sources of the bundled libraries).

## 🙏 Credits

- The [SANE project](http://www.sane-project.org/) — decades of open-source scanner drivers
- [revvv](https://github.com/revvv/sane-backends-cygwin) — the native Windows port of SANE
- [Pete Batard](https://zadig.akeo.ie/) — Zadig / libwdi
- Gerhard Jäger — the SANE plustek backend for LM983x chips
