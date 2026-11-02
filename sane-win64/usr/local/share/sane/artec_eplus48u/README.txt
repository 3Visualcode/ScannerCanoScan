Firmware folder for the SANE artec_eplus48u backend (GT6816 scanners:
Trust Easy Webscan 19200, Artec E+ 48U, Medion MD9693/MD9705, UMAX AstraSlim,
Memorex MEM48U, Yakumo Scan50, ...).

artec_eplus48u.conf points here: /usr/local/share/sane/artec_eplus48u/Artec48.usb
(Cygwin root "/" = the sane-win64 folder).

The firmware (Artec48.usb, 8192 bytes; 1200.usb for the E+ Pro / AstraSlim
1200 SE) is proprietary and NOT shipped with this project. ScannerCanoScan
copies it here at start-up from the folder of the executable, where the user
drops it the first time (the app asks for it when such a scanner is detected).
