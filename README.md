# ScannerCanoScan

**Free, open-source scanning software for Windows 10/11 (64-bit) for old USB scanners that never got official 64-bit Windows drivers**: the National Semiconductor **LM9831/LM9832/LM9833** family (Canon CanoScan N670U, LiDE 20/25/30, …) and the **GT6816** family (Trust Easy Webscan 19200, Artec E+ 48U, Medion, UMAX AstraSlim, …).

One single portable executable: **`ScannerCanoScan.exe`**. No installation, no WSL, no virtual machines, no paid software.

> Canon (and other vendors) abandoned these scanners around Windows XP. The only commercial option today is paid software. This project brings them back to life on modern Windows, for free, using the open-source [SANE](http://www.sane-project.org/) driver compiled natively for Windows.

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011%20(64--bit)-blue)
![License](https://img.shields.io/badge/GUI%20license-MIT-green)
![SANE](https://img.shields.io/badge/driver-SANE%20plustek%20%2B%20artec__eplus48u-orange)

---

## ✨ Features

- **Preview** — quick 75 DPI scan of the whole flatbed, shown on screen
- **Area selection** — drag a rectangle on the preview to scan only that part
  (any shape: a photo, a receipt, a tall vertical strip). Click once to go back
  to the full bed
- **Auto-crop** — finds the document on the glass and sets the scan area to it
- **Scan** — saves to the `Scans\` folder as `scan_DATE_TIME.ext`
- Modes: Color / Grayscale / Black & white
- Resolution: LM983x models offer what the connected scanner reports (75–600
  DPI if it reports nothing), GT6816 models 50–1200 DPI. The list adapts to the
  scanner that is detected. These are USB 1.1 scanners: 600 DPI takes minutes,
  and 1200 DPI on the full bed in colour is about 430 MB of data, so select an
  area when you can
- Output formats: PNG, JPEG, PDF, TIFF
- Full A4 flatbed area by default
- 100% portable: a single `.exe`, nothing else to install

Selecting a smaller area does not just crop the image: the scanner head only
travels over that region, so the scan is also proportionally **faster**.

## 🖨️ Supported scanners

Two SANE backends are bundled. The app detects which one your scanner uses
and adapts the resolution list and the preview accordingly.

### LM9831 / LM9832 / LM9833 chips — SANE `plustek` backend

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

### GT6816 chip — SANE `artec_eplus48u` backend (needs a firmware file)

**Supported by the backend (untested on Windows so far — reports welcome!):**

| Vendor | Model | USB ID | Firmware file |
|---|---|---|---|
| Trust | **Easy Webscan 19200** | `05D8:4006` | `Artec48.usb` |
| Trust | 240H Easy Webscan Gold | `05D8:4007` | `Artec48.usb` |
| Artec | E+ 48U | `05D8:4003` | `Artec48.usb` |
| Artec | E+ Pro | `05D8:4004` | `1200.usb` |
| Medion / Tevion | MD 9693, MD 9705, MD 4394 | `05D8:4003` | `Artec48.usb` |
| Memorex | MEM 48U | `05D8:4005` | `Artec48.usb` |
| UMAX | AstraSlim SE | `05D8:4009` | `Artec48.usb` |
| UMAX | AstraSlim 1200 SE | `05D8:4010` | `1200.usb` |
| Yakumo | Scan50 | `05D8:4011` | `Artec48.usb` |

Source: [SANE artec_eplus48u backend documentation](http://www.sane-project.org/man/sane-artec_eplus48u.5.html).

These scanners have no firmware on board: the driver uploads it over USB every
time the scanner is opened. The firmware is proprietary, so **it is not included**
in this project. You need the file **once**, from the original driver:

- on the **driver CD** that came with the scanner (look for `Artec48.usb`, often
  in a `Win98` / `WinMe` / `Driver` folder), or
- in `C:\Windows\System32\drivers\Artec48.usb` on any PC where the old Windows
  driver was installed, or
- inside the driver package downloadable from the vendor's support site
  (for the Trust 19200 it is Trust item 12388; unzip the installer with 7-Zip
  and search for `*.usb`).

`Artec48.usb` is 8192 bytes (MD5 `55113258bc41f30ef5f5be748e1b01ee`).

The first time the app detects a GT6816 scanner it asks you to locate the file
and copies it next to `ScannerCanoScan.exe`; after that it is remembered. You
can also just drop the file next to the exe yourself.

Notes:
- Only the **Canon N670U** has been tested by the author so far. All other models use the same driver code paths, so they are expected to work. If you own one, please **open an issue** and report success/failure — the tables will be updated.
- The maximum scan area is A4 (215×297 mm); you can select any smaller area from the preview. Small sheetfed models (e.g. TravelScan, Strobe XP100) may not accept the full A4 geometry — open an issue if you hit an error.
- In the Zadig step below, select **your** scanner's USB ID from these tables.

## 🚀 Installation (2 minutes)

You need two files from the [Releases](../../releases) page: `ScannerCanoScan.exe` and `zadig.exe`.

1. Plug in the scanner via USB.
2. **One time only** — install the generic WinUSB driver:
   - Run `zadig.exe` ([Zadig](https://zadig.akeo.ie/) by Pete Batard)
   - Menu *Options* → *List All Devices*
   - Select your scanner (e.g. **CanoScan**, USB ID `04A9 220D`, or the Trust
     Easy Webscan 19200, USB ID `05D8 4006` — check the tables above)
   - Target driver: **WinUSB** → click *Install Driver*
3. Run `ScannerCanoScan.exe`. Done.
4. **GT6816 scanners only** (Trust Easy Webscan 19200 & co.): the app asks for
   the firmware file `Artec48.usb` the first time — see *Supported scanners*
   above for where to find it.

Notes:
- **SmartScreen** may warn you the first time (the exe is not code-signed yet): click *More info* → *Run anyway*.
- The WinUSB driver replaces any previous driver for the scanner (on modern 64-bit Windows there is no official one anyway). This is fully reversible — see *Undoing the WinUSB driver* below.

## ↩️ Undoing the WinUSB driver (going back)

Zadig does **not** install anything else on the PC: it only binds the Microsoft
WinUSB driver to your scanner's USB ID through a small generated INF file.
Removing it takes a minute and needs no extra tools.

1. Plug in the scanner, open **Device Manager** (`devmgmt.msc`).
2. Expand **Universal Serial Bus devices** and find the scanner (it has the name
   you saw in Zadig, e.g. *CanoScan*; the *Driver* tab shows provider **libwdi**).
3. Right-click → **Uninstall device**, tick **"Attempt to remove the driver for
   this device"** (on older Windows 10: *"Delete the driver software for this
   device"*) → *Uninstall*.
4. Unplug and replug the scanner. It now shows up under **Other devices** with a
   yellow mark — that is the original state on 64-bit Windows, where no vendor
   driver exists.

If instead the *Driver* tab offers **Roll Back Driver**, use that: it restores
whatever driver was there before Zadig (for example VueScan's driver).

If Windows re-installs WinUSB by itself after replugging, the Zadig INF is still
in the driver store. Remove it from an **administrator** PowerShell:

```
Get-WindowsDriver -Online | Where-Object ProviderName -eq 'libwdi' |
  Format-Table Driver, OriginalFileName, ClassName, Date
# note the oemNN.inf whose OriginalFileName matches your scanner, then:
pnputil /delete-driver oemNN.inf /uninstall /force
```

Replug the scanner afterwards. Optional cleanup: Zadig also adds a self-signed
certificate named *"USB\VID_xxxx&PID_xxxx (libwdi autogenerated)"* in
**Trusted Root Certification Authorities** and **Trusted Publishers**
(`certlm.msc`); you can delete it once the driver is gone.

After this, any other software (e.g. a commercial scanning program) can install
its own driver for the scanner as usual. Running Zadig again re-enables this app.

## 🖱️ Scanning part of the page

1. Click **Preview** — the whole flatbed is scanned at low resolution and shown.
2. **Drag** a rectangle on the preview over what you want. The selected size in
   millimetres appears under *Scan area*. Or click **Auto-crop** and let the app
   find the document by itself.
3. Choose mode, DPI and format, then click **SCAN**. Only the selected area is
   scanned, so it is also faster.

A single click on the preview (or **Reset to full area**) goes back to the whole
bed. The selection survives further previews, so you can refine it.

## 🔧 How it works

```
USB scanner → WinUSB driver (Microsoft, installed via Zadig)
           → libusb (cygusb-1.0.dll)
           → SANE backend 1.0.32 (Cygwin port for Windows):
                "plustek"        for LM9831/2/3 chips
                "artec_eplus48u" for GT6816 chips (+ Artec48.usb firmware upload)
           → scanimage.exe
           → Python/tkinter GUI (scanner_app.py)
           → PyInstaller onefile = ScannerCanoScan.exe
```

The executable bundles the open-source **SANE** scanner drivers (plustek and artec_eplus48u backends) compiled for Windows via the Cygwin port [revvv/sane-backends-cygwin](https://github.com/revvv/sane-backends-cygwin), together with the required Cygwin DLLs. The GUI (single-file Python/tkinter + Pillow) invokes `scanimage.exe`, reads which backend answered, and saves the output.

## 🛠️ Building from source

Prerequisites: Python 3.10+ with tkinter, plus `pip install pyinstaller pillow`.

```powershell
git clone https://github.com/3Visualcode/ScannerCanoScan.git
cd ScannerCanoScan
.\build.ps1
```

`build.ps1` runs the test suite, builds `dist\ScannerCanoScan.exe` from
`ScannerCanoScan.spec`, and can code-sign it (`-CertSubject`, `-PfxPath` or
`-TrustedSigningMetadata` — see `Get-Help .\build.ps1 -Full`).

Development run without building: `python scanner_app.py` (uses the
`sane-win64\` folder next to the source). You do not need a scanner to work on
the GUI — see [DEVELOPMENT.md](DEVELOPMENT.md) §9 for the simulated scanner.

## 🔍 Troubleshooting

- **"Scanner not detected"** → check the USB cable; then verify the driver: in Device Manager the scanner must appear under *USB Devices* with the WinUSB driver. If not, repeat the Zadig step.
- **Manual diagnostics** (from the project folder):
  ```
  sane-win64\bin\scanimage.exe -L
  ```
  Expected: `device 'plustek:libusb:NNN:NNN' is a Canon CanoScan N670U/N676U/LiDE20`
  or `device 'artec_eplus48u:libusb:NNN:NNN' is a Trust Easy Webscan 19200` (or your model).
- `Operation not supported` on the USB device → WinUSB driver missing → run Zadig.
- **GT6816 scanner detected but every scan fails** → the firmware is missing or
  is the wrong file. Check that `Artec48.usb` (8192 bytes) sits next to
  `ScannerCanoScan.exe`, then click *Check scanner*. For a detailed log:
  ```
  set SANE_DEBUG_ARTEC_EPLUS48U=5
  sane-win64\bin\scanimage.exe -L
  ```
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
| SANE backends (`scanimage.exe`, plustek, artec_eplus48u) | GPL v2 (with SANE exception) | [sane-project.org](http://www.sane-project.org/), [revvv/sane-backends-cygwin](https://github.com/revvv/sane-backends-cygwin) |
| GT6816 firmware (`Artec48.usb`) | proprietary — **not included**, taken from your own driver CD | Artec / Trust / your scanner vendor |
| Cygwin runtime DLLs (`cygwin1.dll`, …) | LGPL v3 | [cygwin.com](https://cygwin.com/) |
| Zadig | GPL v3 | [zadig.akeo.ie](https://zadig.akeo.ie/) |

If you redistribute the executable, keep this file with it (it tells users where to find the sources of the bundled libraries).

## 🙏 Credits

- The [SANE project](http://www.sane-project.org/) — decades of open-source scanner drivers
- [revvv](https://github.com/revvv/sane-backends-cygwin) — the native Windows port of SANE
- [Pete Batard](https://zadig.akeo.ie/) — Zadig / libwdi
- Gerhard Jäger — the SANE plustek backend for LM983x chips
- Michael Herder — the SANE artec_eplus48u backend for GT6816 chips
