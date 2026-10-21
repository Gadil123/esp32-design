# 11 · Flash / PSRAM 容量审计

> 结论等级：**模块型号与镜像头为已确认；factory 的实际可用分区布局为 16 MB。**
> 本文把“物理容量”“镜像头声明”“分区表实际使用”分开记录，避免再把
> 16 MB 当成硬件全部容量。

## 1. 模块型号

原理图标注：

```text
ESP32-C5-WROOM-1-N32R8
```

按 Espressif 命名：

| 字段 | 含义 |
| --- | --- |
| `N32` | 32 MB SPI Flash |
| `R8` | 8 MB PSRAM |

因此本板**物理上**是 32 MB Flash + 8 MB PSRAM。此前文档里的
“Flash 16 MB”应理解为镜像/分区配置，不是模块容量。

## 2. 镜像头声明

ESP32 app image header 的第 4 个字节高半字节是 flash size code：

| 镜像 | 头部字节 | size code | 声明容量 |
| --- | --- | ---: | --- |
| factory app | `e9 05 02 4f ...` | `4` | 16 MB |
| ota_0 app | `e9 05 02 5f ...` | `5` | 32 MB |

两个 app 的构建配置不一致：

- factory 按 16 MB 构建。
- ota_0 按 32 MB 构建。

这不是“硬件有两个版本”的证据；更可能是两个工程使用了不同的
`sdkconfig`/board 配置。

## 3. 分区表实际布局

factory 自带分区表：

| 分区 | offset | size | 结束 |
| --- | ---: | ---: | ---: |
| `nvs` | `0x9000` | `0x4000` | `0xd000` |
| `otadata` | `0xd000` | `0x2000` | `0xf000` |
| `phy_init` | `0xf000` | `0x1000` | `0x10000` |
| `factory` | `0x20000` | `0x4e2000` | `0x502000` |
| `storage` | `0x502000` | `0x400000` | `0x902000` |
| `ota_0` | `0x910000` | `0x300000` | `0xc10000` |
| `assets` | `0xc10000` | `0x300000` | `0xf10000` |

分区表在 `0xf10000` 结束，即 **16 MB 边界内**。物理 32 MB 中大约上半
16 MB 没有被这套分区表使用。

`ota_0` 的 32 MB 头并不会自动扩大分区；它只影响 bootloader/烧录工具对
flash 容量的假设。真正可访问范围仍由分区表决定。

## 4. 公共 BSP 与 board draft

公共 C5 示例的 `sdkconfig.defaults` 使用：

```text
CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions_16m.csv"
```

board draft 也保持 16 MB：

```text
CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions_16m.csv"
```

这是**有意选择**：

1. 与 factory 分区表一致，便于对照和回退。
2. Brookesia 示例的 `partitions_16m.csv` 可直接复用。
3. 32 MB 需要新的分区 CSV、`CONFIG_ESPTOOLPY_FLASHSIZE_32MB`，并验证
   bootloader/OTA/资产分区，不应只改一个宏。

## 5. PSRAM

模块为 8 MB PSRAM。公共 C5 示例配置：

```text
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_QUAD=y
CONFIG_SPIRAM_FETCH_INSTRUCTIONS=y
CONFIG_SPIRAM_RODATA=y
CONFIG_SPIRAM_XIP_FROM_PSRAM=y
CONFIG_SPIRAM_SPEED_80M=y
CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL=0
CONFIG_SPIRAM_TRY_ALLOCATE_WIFI_LWIP=y
```

factory 二进制中出现 PSRAM 初始化、XIP、堆分配相关字符串，能证明 PSRAM
被启用；但精确的 factory `sdkconfig` 未恢复，不能把公共示例的每个选项都
当成 factory 原值。

## 6. 风险与建议

- **不要把 `CONFIG_ESPTOOLPY_FLASHSIZE_16MB` 当成“硬件只有 16 MB”。**
- **不要直接把 board draft 改成 32 MB。** 先决定是否真的需要上半 16 MB。
- 若要用满 32 MB：新增 32 MB 分区表，确认 `factory`/`ota_0`/`assets`
  偏移和大小，验证 OTA 回退与烧录工具。
- 若只做 Pocket OS bring-up：保持 16 MB 布局，减少变量。
- PSRAM 的 8 MB 是模块事实；实际可用堆取决于 `CONFIG_SPIRAM_*` 和
  LVGL/音频缓冲分配。

## 7. 相关文档

- [固件清单](01_firmware_inventory.md)
- [原理图交叉核对](12_schematic_crosscheck.md)
- [Brookesia 0.7 板级适配](08_brookesia07_board_adaptation.md)
