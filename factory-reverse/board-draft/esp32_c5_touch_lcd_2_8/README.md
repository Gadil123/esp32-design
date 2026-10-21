# ESP32-C5-Touch-LCD-2.8 · Brookesia 0.7 board draft

> Status: **draft / not build-tested / not flashed**.
> Target: ESP-Brookesia `release/v0.7` (`brookesia_hal_boards` v0.7.5).
> Source of truth: FactoryApp V1.1 decompilation + public Waveshare BSP.

This directory turns the recovered board constants into a Brookesia 0.7 board
package. It is meant to be dropped into
`hal/brookesia_hal_boards/boards/waveshare/esp32_c5_touch_lcd_2_8/` for the
first display/touch/audio bring-up.

## Pin and device map

| Function | Value | Evidence |
| --- | --- | --- |
| I2C port / SDA / SCL | `0` / `0` / `1` | factory `bsp_i2c_init` |
| LCD SPI host | `SPI2_HOST` | public BSP |
| LCD SCLK / MOSI / MISO / CS / DC | `6` / `7` / `8` / `10` / `9` | factory `bsp_display_new` |
| LCD pixel clock | `40 MHz`, SPI mode `0` | ota_0 `CustomBoard` (`0x42021a4e`); factory/public BSP use `80 MHz` |
| LCD panel | ST7789, 240x320, RGB565, invert on | factory + public BSP |
| Touch | CST3530 at `0x58`, 400 kHz, INT `5` | factory `bsp_touch_new`; ota_0 has no touch init |
| Touch reset | CH32V003 pin `0` | factory masks |
| LCD reset | CH32V003 pin `1` | factory masks |
| Power amplifier enable | CH32V003 pin `3` | factory masks |
| Backlight | CH32V003 PWM register `0x05` | factory `bsp_display_brightness_set` |
| IO expander | CH32V003 at `0x24` | factory `bsp_io_expander_init` |
| I2S BCLK / WS / TX / RX | `24` / `25` / `26` / `27` | factory struct + OTA ctor |
| I2S MCLK | not connected (`-1`) | factory struct + OTA ctor |
| ES8311 | `0x30`, 400 kHz, duplex | factory + OTA `GetAudioCodec()` |
| Battery | CH32 `PC4/EXIO_ADC`; `BAT_ADC` 经 200K/100K 分压 | schematic; factory does not read it |
| Flash / PSRAM | module 32 MB / 8 MB; factory partition table uses 16 MB | module marking + image header |
| microSD | SPI: SCLK `6`, MOSI `7`, MISO `8`, CS `23` | public BSP |

## What is included

- `board_info.yaml`
- `board_devices.yaml` — expander, ES8311 DAC/ADC, ST7789, CST3530
- `board_peripherals.yaml` — I2C, I2S in/out, shared SPI bus
- `setup_device.c` — CH32 factory hook, LCD/touch reset, temporary backlight on
- `sdkconfig.defaults.board` — C5 + Brookesia 0.7 HAL switches

## Required files before building

The board package references two local components, matching the RYMCU board
pattern:

```text
esp32_c5_touch_lcd_2_8/
├── components/
│   ├── custom_io_expander_ch32v003/   # waveshare/custom_io_expander_ch32v003 1.0.2
│   └── esp_lcd_touch_cst3530/         # from Waveshare public BSP
├── board_info.yaml
├── board_devices.yaml
├── board_peripherals.yaml
├── setup_device.c
└── sdkconfig.defaults.board
```

Copy them from:

- `ESP32-C5-Touch-LCD-2.8/examples/esp-idf/components/waveshare__esp_lcd_touch_cst3530`
- `waveshare/custom_io_expander_ch32v003` component (or the public Waveshare
  component bundle)

Also copy `partitions_16m.csv` from the Brookesia example project, or point
`CONFIG_PARTITION_TABLE_CUSTOM_FILENAME` at the project's own 16 MB table.

## Known gaps

1. **Runtime brightness is not implemented.** `lcd_brightness`/`ledc_ctrl`
   cannot drive the CH32V003 PWM register. This draft sets PWM to `255` once in
   `lcd_panel_factory_entry_t`. A custom `DisplayBacklightIface` implementation
   must call `custom_io_expander_set_pwm()` for `set_brightness()`.
2. **microSD is not in the board YAML.** Brookesia 0.7 `fs_fat` examples use
   SDMMC; this board wires the card to the shared SPI bus. Use a custom
   `fs_fat`/`sdspi` device or mount it in application code.
3. **Battery is disabled.** The hardware path is confirmed as `BAT_ADC` →
   CH32V003 `PC4/EXIO_ADC`, with a 200K/100K divider. Factory does not appear
   to read the CH32 ADC, and Brookesia 0.7 `battery_adc_impl` only supports
   ESP32 ADC via board manager. A custom `PowerBatteryIface` reading CH32
   register `0x06` is required before enabling power. See
   [battery notes](../../docs/10_battery_ch32_adc.md).
4. **Sensors are not board devices.** Brookesia 0.7 HAL has no IMU/RTC/
   temperature interface. QMI8658 (`0x6A/0x6B`), PCF85063A (`0x51`) and SHTC3
   (`0x70`) must be application-level components.
5. **Audio sample rate is a bring-up choice.** This draft uses 16 kHz stereo
   I2S to match the Brookesia recorder/player defaults. Factory BSP used
   22.05 kHz mono; OTA Xiaozhi used 24 kHz duplex. Tune after loopback tests.
6. **YAML/field names are unverified against the exact 0.7.5 parser.** In
   particular `io_i2c_config` for CST3530 and `adc_channel_labels: ["M"]`.
7. **The module is 32 MB Flash, but this draft stays at 16 MB.** Factory
   partitions end at `0xf10000`; a 32 MB layout needs its own partition CSV
   and OTA validation. See [flash audit](../../docs/11_flash_capacity_audit.md).

## Bring-up order

1. Build with storage/power disabled, confirm board package YAML parses.
2. Probe I2C: `0x24` (CH32), `0x30` (ES8311), `0x58` (CST3530), `0x51`
   (PCF85063A), `0x6A` (QMI8658), `0x70` (SHTC3).
3. Confirm LCD reset pulse and ST7789 init; then fix orientation with
   `swap_xy`/`mirror_*`.
4. Confirm CST3530 points with INT `5`; fall back to polling if the interrupt
   line is not populated.
5. Test speaker with a 1 kHz tone; then microphone loopback. If RX is all zero,
   verify `din=27` (do not copy the public BSP `.dout/.din` swap).
6. Read CH32 ADC register `0x06` and compare with a multimeter before adding a
   custom power interface.
7. Only then enable storage and add the custom backlight interface.

## Non-goals

- This is not a complete Pocket OS port.
- It does not reproduce the factory desktop or its nine apps.
- It does not claim the board package compiles or runs.
