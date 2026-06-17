# Matrix Scroll — Hardware Reference Design (v0.1)

Single source of truth for the CAD and EE teams. This document describes the two
shipping SKUs — **Scroll Key** and **Scroll Token** — at block-schematic fidelity:
net maps, bills of material, form factors, and the integration notes that bite
later. Treat dimensions and pin choices as a validated starting geometry, not
frozen tolerances; confirm against final datasheets before fab.

The software emulator is **not** an offered product. Hardware ownership is the only
way to activate the MCP server and sign releases.

**Locked decisions (this revision):**

| Decision | Choice | Rationale |
|---|---|---|
| Key MCU | STM32L432KC | Native USB-FS (crystal-less CRS), on-chip touch (TSC) + crypto/RNG — lowest part count |
| Token MCU | **RP2350** | Dual-core + PIO drives a 1-bit face smoothly; lime/1-bit aesthetic |
| Token display | **Sharp LS013B7DH03** (1.28", 128×128, 1-bit) | Reflective, ultra-low-power, truest to the Digital Rain look |
| Root of trust | NXP SE050 (both SKUs) | CC EAL6+, on-die Ed25519 keygen, non-extractable |
| Accent | Lime `#e8ff9c` | Coherent with the storefront palette |

---

## SKU 1 — Scroll Key (simple USB-C, encrypted MCP activation)

The entire job: **the MCP server will not run unless this is plugged in**, and every
release/manifest is signed by a key that physically cannot leave the device.

**Form factor:** 56 × 18 × 8 mm male USB-C stick · CNC aluminum shell · single lime
status LED · one cap-touch zone on the top face.

### Net map (key nets)

| Net | From → To | Notes |
|---|---|---|
| VBUS 5V | USB-C A4/B4/A9/B9 → LDO IN | 1µF + 10µF bulk |
| 3V3 | AP2112K OUT → STM32 VDD, SE050 VDD | 1µF/rail + 100nF decoupling |
| CC1/CC2 | USB-C A5/B5 → 5.1k Rd to GND | UFP advertises "device" |
| D+/D− | USB-C → USBLC6 → STM32 PA12/PA11 | native USB-FS, no crystal (CRS) |
| I²C | STM32 PB6/PB7 → SE050 SCL/SDA | 4.7k pullups to 3V3 |
| ENA | STM32 GPIO → SE050 ENA | power-gate the SE |
| TSC | STM32 PA0 → cap pad | touch-to-sign presence |
| LED | STM32 3× PWM → RGB LED | idle / signing / fault |

### BOM (core)

| # | Part | Function | Package |
|---|---|---|---|
| 1 | STM32L432KC | USB-FS bridge + TSC + crypto-accel | UFQFPN-32 |
| 2 | NXP SE050C2 | Ed25519 root of trust | HX2QFN-20 |
| 3 | AP2112K-3.3 | 5V→3V3 LDO | SOT-23-5 |
| 4 | USBLC6-2SC6 | USB ESD | SOT-23-6 |
| 5 | RGB LED | status | 0606 |
| 6 | Passives | 5.1k CC, 4.7k I²C, decoupling | 0402 |

### Activation flow (the "encrypted" part)

1. Host MCP server issues a challenge → Key.
2. STM32 forwards the digest to SE050 over I²C; **private key never leaves the SE**.
3. Cap-touch confirms physical presence; SE050 returns an Ed25519 signature.
4. Host verifies against the device public key → MCP unlocks. No Key, no server.

**Features:** MCP unlock gate · release/manifest signing · touch-to-sign presence ·
tamper-evident (optional epoxy pot) · driverless (USB-HID/CDC) cross-platform.

---

## SKU 2 — Scroll Token (premium desk companion, avatar LCD)

Everything the Key does, **plus** a battery-powered desk object with the mascot face,
an on-screen attestation log, and sound/haptics.

**Form factor:** ~70 × 70 × 14 mm squircle · CNC aluminum · USB-C receptacle on the
bottom edge · 1.28" Sharp Memory LCD facing the user · 4 tactile buttons.

### Net map (subsystem highlights)

| Subsystem | Nets | Notes |
|---|---|---|
| Charge | VBUS → MCP73831 → BAT | 500mA program resistor, STAT → RP2350 GPIO |
| Battery | BAT → DW01+FS8205 → TPS63020 | protection + buck-boost to stable 3V3 |
| Fuel gauge | BAT → MAX17048 → I²C | % + voltage to the UI |
| Compute | RP2350 ↔ W25Q128 (QSPI) | dual-core; PIO streams the display |
| Secure | RP2350 ↔ SE050 (I²C + ENA) | same trust boundary as the Key |
| Display | SPI: SCLK/SI/SCS + DISP + EXTCOMIN | 1-bit Sharp; **no backlight** (reflective) |
| Audio | I²S: BCLK/LRCLK/DIN → MAX98357A → 8Ω | confirmation chirps, personality |
| Motion | LSM6DS3 → I²C | wake-on-lift, tap gestures |
| Haptics | DRV2605L → LRA | "signed" tactile pulse |
| Buttons | 4× GPIO | nav + soft power |

### BOM (delta over the Key)

| # | Part | Function | Package |
|---|---|---|---|
| 1 | RP2350A | dual-core MCU + PIO (smooth face) | QFN-60 |
| 2 | W25Q128JV | QSPI firmware/assets | USON-8 |
| 3 | TPS63020 | buck-boost 3V3 (battery range) | QFN-10 |
| 4 | MCP73831 | LiPo charger | SOT-23-5 |
| 5 | MAX17048 | fuel gauge | µDFN-8 |
| 6 | MAX98357A | I²S class-D amp | QFN-16 |
| 7 | LSM6DS3 | IMU wake-on-lift | LGA-14 |
| 8 | DRV2605L | haptic driver | DSBGA-9 |
| 9 | LiPo 500–1000 mAh | power | pouch |
| 10 | Sharp LS013B7DH03 | 1-bit avatar face | module + FPC |
| — | SE050, USBLC6, 12 MHz XOSC, rails | carried/added | — |

**Features:** animated mascot face (idle blinks, "signing…", alert-on-fail, standalone
on battery) · on-screen attestation log (device_id + last N signings, ISO-8601) ·
tap-to-sign with haptic + audio confirmation · **dual personality** (expressive
Companion mode default, sober Attestation mode for the CISO context) · wake-on-lift.

---

## Shared security boundary (both SKUs)

The SE050 sits on its own copper pour, reachable only over I²C, and only ever receives
a digest and returns a signature. The Ed25519 key pair is generated on-die and is
non-extractable — the MCU and USB never touch the private key. Keep the I²C lines short,
guard them, and power-gate via ENA. **That single sentence is the entire product.**

---

## Sharp Memory LCD integration notes (LS013B7DH03)

The Sharp Memory LCD looks like SPI but has three quirks that catch teams every time —
bake these into the schematic and firmware up front:

- **Chip select is ACTIVE-HIGH.** `SCS` asserts high (opposite of normal SPI). Do not tie
  it to a standard `CS#` net or auto-CS peripheral expecting active-low.
- **Write-only, 3-wire.** There is no MISO. Drive `SCLK` + `SI` only; the panel is never
  read back. RP2350 SPI TX (or a PIO program) handles this cleanly.
- **VCOM must invert continuously** to prevent DC bias burn-in. Two options:
  - **External (recommended):** tie `EXTMODE` high and drive `EXTCOMIN` with a
    1–60 Hz PWM from an RP2350 GPIO/PWM slice.
  - **Software:** tie `EXTMODE` low and toggle the COM bit in the write command frame.
- **`DISP` pin** is a hard display on/off (blanks to white when low) — wire to a GPIO for
  instant sleep without losing the framebuffer.
- **No backlight.** It is reflective/transflective; there is **no** backlight boost net.
  This deletes the backlight-PWM line shown in the earlier block diagram. Add a front
  light only if a dark-room demo requirement appears.
- **Power:** VDD 3.0–5.0 V (run at 3V3); hold power is ~µW. Decouple VDD with 1µF + 100nF.

| LCD pin | RP2350 net | Note |
|---|---|---|
| SCLK | SPI SCK | ≤ 2 MHz is plenty for 128×128 1-bit |
| SI | SPI MOSI | data in only |
| SCS | GPIO (active-HIGH) | manual CS, not auto-CS |
| EXTCOMIN | PWM GPIO | 1–60 Hz VCOM toggle |
| EXTMODE | 3V3 | selects external VCOM |
| DISP | GPIO | display on/off |
| VDD/VSS | 3V3 / GND | 1µF + 100nF decoupling |

**Module geometry:** outline ≈ 27.5 × 28.8 × 0.95 mm; active area 23.04 × 23.04 mm;
FPC tail exits one edge — leave ≥ 4 mm bend-radius room to the onboard FPC connector
(e.g., Hirose FH34, 0.5 mm pitch). Mount with 3M VHB to the inside of the top shell.

---

## RP2350 support circuitry (Token)

- **QSPI flash:** W25Q128JV on the dedicated QSPI bus (firmware + face/animation assets).
- **Crystal:** 12 MHz XOSC with 2× load caps (per RP2350 datasheet) — required, unlike the
  crystal-less STM32 in the Key.
- **Core power:** RP2350 has an internal core regulator; decouple the 1.1 V core rail and
  all IOVDD/DVDD pins per the hardware design guide. Add the BOOTSEL tact for flashing.
- **USB:** D+/D− via USBLC6 to the RP2350 USB pins; USB-C CC pulldowns (5.1k) for UFP.

---

## CAD callouts (the stuff that bites later)

- **USB-C keepout:** mid-mount receptacle needs a board-edge notch ≈ 9.0 × 3.5 mm; model
  the mating connector keepout (≥ 6.5 mm insertion + finger clearance).
- **Cap-touch through metal (Key + Token):** anodized aluminum **blocks** capacitive
  sensing. Put a polycarbonate insert over any cap pad, or switch to a low-profile tact
  dome. This is the most common redesign on metal-bodied touch devices — decide early.
- **Datums:** primary datum on the USB-C connector face (the hard mechanical interface);
  secondary on the display window.
- **Display stack height (Token):** glass (0.95) + VHB (0.2) + air gap (0.3) + shell →
  budget ~1.6 mm under the top face.
- **Finish:** matte black anodize with a lime `#e8ff9c` accent ring or laser-etched mark.

---

## Open items to confirm before fab

- SE050 variant/provisioning flow (pre-provisioned at factory vs. first-boot keygen).
- Token enclosure: 70 mm squircle vs. a compact 40 mm token (display window unchanged).
- Tamper response policy (epoxy pot on the Key; enclosure switch on the Token?).
- Regulatory: USB-IF, CE/FCC, and for the LiPo Token, UN38.3 / IEC 62133 transport.

> **Status:** v0.1 reference design. Component packages and net maps are grounded in real
> datasheets but must be validated against final part revisions before layout and fab.

---

*Hardware questions: operations@matrixscroll.com · Digital Rain · Matrix Scroll*
