# 01 · 固件清单与镜像结构

> 证据等级：**已确认（BIN 静态解析）**。  
> 分析对象：官方 FactoryApp V1.1 BIN，SHA256 `92d0f25d7b8c43900c8882e2ca9cee1ca7c8a9338504bd392567f3d1e8cdf174`。  
> BIN 不纳入仓库；从官方 release 获取。

## 1. 基本信息

| 项目 | 值 |
| --- | --- |
| 文件大小 | `13699516` 字节（`0xd109bc`） |
| 芯片 | ESP32-C5（image chip ID `23`） |
| Bootloader | `0x2000`，32 KB，entry `0x4084bbaa` |
| Flash | 镜像/分区按 16 MB（模块物理 32 MB，见 [审计](11_flash_capacity_audit.md)），DIO，80 MHz |
| IDF | `v5.5.4` |
| 默认启动 | `factory`（`otadata` 全 `0xFF`） |
| 出厂 app | `01_factory`，version `1` |
| 备用 app | `xiaozhi`，version `2.2.6` |

Bootloader 字段：

```text
offset      0x2000
size        0x8000
magic       0xe9
segments    3
entry       0x4084bbaa
chip id     23
flash size  16 MB
mode/freq   DIO / 80 MHz
```

这里的 `flash size 16 MB` 是镜像头声明，不是模组物理容量；模组为
`ESP32-C5-WROOM-1-N32R8`（32 MB Flash / 8 MB PSRAM），但 factory 分区表
只到 `0xf10000`。详见 [Flash 容量审计](11_flash_capacity_audit.md)。

## 2. 分区表

| 分区 | 类型 | 子类型 | 偏移 | 大小 | 结束 |
|---|---|---:|---:|---:|---:|
| `nvs` | data | nvs | `0x9000` | 16 KB | `0xd000` |
| `otadata` | data | ota | `0xd000` | 8 KB | `0xf000` |
| `phy_init` | data | phy | `0xf000` | 4 KB | `0x10000` |
| `factory` | app | factory | `0x20000` | `0x4e2000`（5000 KB） | `0x502000` |
| `storage` | data | spiffs | `0x502000` | 4 MB | `0x902000` |
| `ota_0` | app | ota_0 | `0x910000` | 3 MB | `0xc10000` |
| `assets` | data | spiffs | `0xc10000` | 3 MB | `0xf10000` |

注意：

- `storage` 和 `assets` 的分区 subtype 都是 `spiffs`，但 `assets` 实际是**自定义 mmap pack**，不是普通 SPIFFS。
- 分区表结束处是 MD5/尾部数据，不是全 `0xFF`；解析器看到 `ebeb...` 不代表表损坏。
- `nvs` 全空，没有 Wi-Fi/激活数据；`otadata` 两个 entry 全 `0xFF`。

## 3. 两套 app

### factory

| 项目 | 值 |
| --- | --- |
| 偏移 | `0x20000` |
| project | `01_factory` |
| version | `1` |
| IDF | `v5.5.4` |
| 构建时间 | `15:06:55` |
| 构建日期 | `Jul 10 2026` |
| entry | `0x408002b0` |
| segments | 5 |
| image total | `0x4caed0` |
| 分区填充 | 到 `0x4e2000` |
| app header flash size code | 4（16 MB） |
| ELF SHA256 | `f3f904b5c103fe9fe67a10f7f401a10e0eb378181f11502cdb91f7f63b96b21a` |

主要 segment：

| # | load address | length | 文件偏移 |
|---|---|---:|---:|
| 0 | `0x42240020` | `0x272684` | `0x20020` |
| 1 | `0x40800000` | `0xd96c` | `0x2926ac` |
| 2 | `0x42000020` | `0x2359e0` | `0x2a0020` |
| 3 | `0x4080d96c` | `0xf128` | `0x4d5a08` |
| 4 | `0x4081cb00` | `0x6370` | `0x4e4b38` |

factory app 是 Brookesia Phone 桌面，安装：

```text
Settings
AIChats
Sensor
DrawingBoard / Drawpanel
Qmi8658Ball / GravityBall
MusicPlayer
Weather
Games / 2048
Photos
```

factory app 内**没有**完整 Xiaozhi 语音栈：字符串中没有 `xiaozhi`、`wakenet`、`AudioService`、`Es8311AudioCodec`、`MqttProtocol`、`WebsocketProtocol` 的组合。

### ota_0

| 项目 | 值 |
| --- | --- |
| 偏移 | `0x910000` |
| project | `xiaozhi` |
| version | `2.2.6` |
| IDF | `v5.5.4` |
| 构建时间 | `14:24:47` |
| 构建日期 | `Jul 10 2026` |
| entry | `0x408003a6` |
| segments | 5 |
| image total | `0x262060` |
| 分区填充 | 到 `0x300000` |
| app header flash size code | 5（32 MB） |
| ELF SHA256 | `52664f27cfc4b2ebbd1750c9137e761072a49fdf91ec8e72fbbcac038481f8cc` |

主要 segment：

| # | load address | length | 文件偏移 |
|---|---|---:|---:|
| 0 | `0x42190020` | `0xbc718` | `0x910020` |
| 1 | `0x40800000` | `0x38d8` | `0x9cc740` |
| 2 | `0x42000020` | `0x18953c` | `0x9d0020` |
| 3 | `0x408038d8` | `0x12ca0` | `0xb59564` |
| 4 | `0x40816580` | `0x5e28` | `0xb6c20c` |

ota_0 含完整 Xiaozhi 组件：

```text
Es8311AudioCodec
AudioService
MqttProtocol
WebsocketProtocol
wakenet / wake word
assets
./main/audio/codecs/es8311_audio_codec.cc
./main/boards/waveshare/esp32-c5-touch-lcd-2.8/esp32-c5-touch-lcd-2.8.cc
https://api.tenclass.net/xiaozhi/ota/
```

## 4. Assets 包

`assets` 分区是自定义 mmap pack：

| 字段 | 值 |
| --- | --- |
| 实际长度 | `0x1009bc` |
| stored_files | `24` |
| checksum | `0x67` |
| stored_len | `0x1009b0` |
| 数据起始 | `0x42c` |

文件：

| 文件 | 大小 | 用途 |
|---|---:|---|
| `font_puhui_common_16_4.bin` | `0xd2ed8` | 中文字体 |
| `srmodels.bin` | `0x1ebff` | 语音/唤醒模型 |
| `index.json` | `0x7dd` | assets 索引，version 1 |
| 21 个 PNG | 约 `0x600-0xd39` | 表情图片 |

`index.json`：

```json
{
  "version": 1,
  "srmodels": "srmodels.bin",
  "text_font": "font_puhui_common_16_4.bin",
  "emoji_collection": ["..."]
}
```

结论：本镜像的 assets 有效，`srmodels.bin` 存在。把 AI 初始化循环归因于 assets 缺失，与本镜像不符；除非设备上的 assets 被擦除或改写。

## 5. Storage

`storage` 是 SPIFFS，包含：

```text
/music/BGM_2.mp3
```

这是 factory `MusicPlayer` 的素材，不是 Xiaozhi 语音资源。

## 6. 相关文档

- [双 APP 与启动链](02_dual_app_boot.md)
- [音频与 I2S](03_audio_i2s.md)
- [AI 启动与网络](06_ai_bringup.md)
- [完整静态分析](../reference/full-static-analysis.md)
