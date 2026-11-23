# T433 lite - 433 MHz LoRa APRS balloon tracker with a camera

![T433 lite v1.0 top](img/podglad_gora.png)

Sends position as a normal LoRa APRS frame on 433.775 MHz (SF12, BW 125 kHz) and photos as SSDV packets in APRS
"user-defined" frames (`{{I` + base91, the Pecan Pico format), so LoRa APRS iGates can pass them to APRS-IS.

**Status (2026-11-23): five v1.0 boards built by JLCPCB. Radio, GPS and camera work on the bench. Never flown, never tested
through a public iGate.**

## Hardware v1.0 (`pcb_lite/`)
- ESP32-S3-MINI-1U-N4R2, E22-400MM22S (SX1268, **crystal, not TCXO**), ATGM336H, OV2640 on a 24-pin FPC connector,
  ME6211C33 LDO, camera LDOs switched by a GPIO. 2 layers, everything on top, 32 x 40.6 mm, break-off PROG tab.
- Measured mass: 5.2 g without antennas, camera and solar cells.
- `kicad/` - KiCad 7 board; `jlcpcb/` - Gerbers, BOM, CPL; the Python/shell scripts are the generator used to build and route the board.
- Drawings in `img/` (Polish): USB cable on the PROG tab, where to solder antennas and cells, the FFC workaround.

### Camera connector J1 - use the corrected BOM
The original BOM (`pcb_lite/jlcpcb/BOM_t433lite.csv`) has a bottom-contact FPC connector for J1. With it the camera's pin 1 lands on
pad 24 (pin order mirrored): the camera gets hot and does not work. **Do not order with that BOM.**

**`pcb_lite/jlcpcb/BOM_t433lite_v1_0b.csv` is the corrected BOM:** J1 = AFC07-S24ECA-00 (LCSC C262643, top contact). The camera then
goes in lens down, contacts up, and pin 1 meets pin 1. Gerbers and CPL stay the same.
- The signal pads are identical; the mounting tabs land on the existing pads, which are smaller than the tabs.
- The body is about 1.5 mm longer: 0.1-0.4 mm from U7 and about 0.3 mm over the board edge. Tight, check the placement preview.
- This BOM has not been built yet. The five existing boards were made with the original BOM and are used with a workaround:
  an FFC 24-pin 0.5 mm coupler plus a **type B** ribbon, camera turned over (`img/T433_tasma_typ_B.png`).
- A corrected layout (connector moved and rotated) is planned.

Other notes: the E22 crystal drifts about 40 Hz/s during the first seconds of transmission, so the first SF12 frames after
a cold start are lost (firmware sends warm-up frames). A module with a TCXO would be better.

## Firmware (`firmware/`)
- `tracker433_lite_v0_6/` - tracker. 640x480 photo, position frame repeated during the photo, warm-up frames,
  **photo resume after a power dropout** (JPEG and progress kept in LittleFS), waiting for sun when the panel voltage sags,
  position hidden below `POZYCJA_MIN_WYS_M` (only the 4-character locator is sent near the ground).
  Warm-up and resume were confirmed on hardware with v0.4/v0.5; **v0.6 itself is compiled only.**
- `tracker433_lite_rx_v0_1/` - a second T433 board as a USB receiver (prints every frame as a `T433RX;...` line).
- `hw_tests/` - bench test sketches (frames at different power, cold start, camera connector lines).
- Build: Arduino core esp32 3.0.7, board "ESP32S3 Dev Module", PSRAM enabled, Flash 4 MB, USB CDC On Boot enabled,
  RadioLib 7.1.2, TinyGPSPlus 1.1.0:
  `arduino-cli compile --fqbn "esp32:esp32:esp32s3:PSRAM=enabled,FlashSize=4M,CDCOnBoot=cdc,PartitionScheme=default" tracker433_lite_v0_6`
- Set `ZNAK` and `SSDV_ZNAK` in `config.h` to your callsign first.
- Flashing: USB on the PROG tab (V+ through a diode); first time hold B0 to ground at power-up; then upload with arduino-cli or esptool (no prebuilt images here, they would carry a callsign).

## PC receiver (`receiver_pc/`)
`t433_usb_odbior_v0_5.py` (needs `pyserial`) reads the receiver board over USB, shows frames and assembles photos.
It needs an SSDV decoder next to it: build `ssdv_dek_windows.c` with `ssdv.c` and `rs8.c` from the tracker folder.

## Not tested at all
Position frame from a real fix above 1000 m, waiting for sun, Zener protection with 8 cells, the path through public iGates and APRS-IS.

## Callsigns
`N0CALL` in the code is a placeholder. Set your own callsign before transmitting; an amateur licence is required.

## Related
The HF FT8/WSPR tracker with a receiver from the same author: https://github.com/Anakreont/R20-tracker-Rx-Tx-KF

## Licence
`firmware/` and `receiver_pc/` are GPL-3.0 (see `LICENSE`): they include SSDV, Reed-Solomon and base91 code from Pecan Pico 9 by Philip Heron.
No licence has been chosen yet for the hardware files in `pcb_lite/` and `img/`. Design by SQ9GOL. Source comments and drawings are in Polish.
