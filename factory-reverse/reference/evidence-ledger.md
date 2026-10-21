# Evidence ledger

One row per major claim. "Static" means derived from the BIN/source/schematic;
"empirical" means observed on the board. A claim is only promoted to
"confirmed" when both agree or when the observation is directly reproducible.

| Claim | Evidence | Confidence | Status |
| --- | --- | --- | --- |
| Module is `ESP32-C5-WROOM-1-N32R8` | schematic marking | high | confirmed |
| Physical Flash/PSRAM is 32 MB / 8 MB | module part number | high | confirmed |
| factory app header is 16 MB | bytes `e9 05 02 4f`, size code 4 | high | confirmed |
| ota_0 header is 32 MB | bytes `e9 05 02 5f`, size code 5 | high | confirmed |
| factory partition table ends at `0xf10000` | partition table | high | confirmed |
| Boot defaults to factory | `otadata` all `0xFF` | high | confirmed |
| factory `AIChats` switches to ota_0 | factory strings/BSP flow | medium-high | static, needs boot log |
| OTA audio ctor uses `dout=26, din=27` | `GetAudioCodec` `0x42021876`, ctor `0x4200c072` | high | static |
| Factory I2S struct contains `24,25,26,27` | data @ `0x423c1a24` | high | static |
| Factory I2S field order is `mclk,bclk,ws,dout,din` | assumed from public BSP; not typed | medium | **unresolved** |
| Board RX is GPIO27 | V5: RX26 all zero, RX27 records | high | empirical only |
| Board TX is GPIO26 | OTA ctor + V5 RX result; no speaker A/B | medium-high | **working baseline** |
| Public BSP `.dout=27/.din=26` | BSP source | high | conflicts with OTA/V5 |
| Schematic net `GPIO26=ASDOUT`, `GPIO27=DSDIN` | schematic | high | conflicts with OTA/V5 |
| Battery runs through 200K/100K divider to CH32 `PC4` | schematic | high | confirmed |
| CH32 ADC uses register `0x06` | component source | high | confirmed |
| factory does not read CH32 ADC | no command byte 6 and no matching `transmit_receive` site; string absence is secondary (linker may GC it) | high | static negative |
| StatusBar battery is initialized, not periodically updated | `0x4206cc28`, `0x4206ea62`, `0x4206c53e` | medium-high | static, CFG gap |
| Brookesia 0.7 stock battery ADC cannot read CH32 | `battery_adc_impl.cpp` | high | confirmed |
| CH32 PWM controls backlight | `0x42046b2c`, only caller brightness | high | static |
| Backlight has no standard 0.7 device | 0.7 HAL interfaces | high | confirmed |
| microSD is on shared SPI, not SDMMC | schematic/BSP | high | confirmed |
| Gravity ball 95% root cause | strings only | low | **not proven** |
| AI init loop root cause | strings/source candidates only | low | **not proven** |
| Board draft YAML parses/builds | not compiled | low | **unverified** |

## Rules

- Do not turn "static negative" into "hardware absent". Factory not calling
  CH32 ADC does not prove CH32 firmware lacks ADC.
- Do not turn a working baseline into a schematic fact. I2S remains a
  three-way conflict until speaker A/B or logic analyzer data exists.
- Do not turn a module part number into a partition layout. 32 MB Flash does
  not mean the factory partition table uses 32 MB.
- Function names in the dossier are semantic labels. Addresses + bytes are
  the reproducible evidence.
