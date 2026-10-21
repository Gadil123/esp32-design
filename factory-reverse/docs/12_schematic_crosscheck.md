# 12 · 原理图与固件交叉核对

> 结论等级：**网表/型号为高置信；I2S 方向是三方冲突，暂不静默裁决。**
> 原则：可复现的实板观察优先于网名，但在拿到示波器/逻辑分析仪数据前，
> 不把任何一方当成绝对事实。

## 1. 已确认的网表事实

原理图提取自：

```text
schematic/ESP32-C5-Touch-LCD-2.8.pdf
```

关键连接：

| 信号 | 连接 |
| --- | --- |
| `BAT_ADC` | `VBAT` 经 `R7 200K` / `R10 100K` 分压，经 `R52 10K` 到 CH32 `PC4/EXIO_ADC` |
| `EXIO_PWM` | CH32 `PC3` → `LCD_BL` |
| `EXIO3` | CH32 → `PA_CTRL` |
| `EXIO0` | CH32 → `TP_RST` |
| `EXIO1` | CH32 → `LCD_RST` |
| `GPIO24` | `I2S_SCLK` |
| `GPIO25` | `I2S_LRCK` |
| `GPIO26` | `I2S_ASDOUT` |
| `GPIO27` | `I2S_DSDIN` |
| 模块 | `ESP32-C5-WROOM-1-N32R8`（32 MB Flash / 8 MB PSRAM） |

ES8311 数据手册定义：

- pin 7 `ASDOUT`：ADC serial data **output**（codec → MCU）。
- pin 9 `DSDIN`：DAC serial data **input**（MCU → codec）。

如果按网名直译，`GPIO26` 应是 MCU RX，`GPIO27` 应是 MCU TX。

## 2. I2S 三方冲突

| 来源 | GPIO26 | GPIO27 | 说明 |
| --- | --- | --- | --- |
| 原理图网名 | `ASDOUT`（codec out） | `DSDIN`（codec in） | 指向 RX26 / TX27 |
| 公共 BSP + `HARDWARE.md` | RX | TX | `.dout=27` / `.din=26` |
| OTA Xiaozhi ctor | TX / `dout` | RX / `din` | `0x42021876` 传 `0x1a,0x1b` |
| factory 结构体 | 26 / 27（字段序待定） | 27 / 26（字段序待定） | 不能仅凭字节序断言方向 |
| **V5 实板观察** | RX26 全 0 | **RX27 有数据** | 当前最强的工作证据 |

V5 的观察来自早期麦克风 bring-up：`.din=26` 时 PCM 全 0、PCNT 0 edge；
`.din=27` 时录音正常。因此**在这块实板上，至少 RX 是 GPIO27**，与
原理图网名和公共 BSP 相反。

OTA 的编译结果可以确定：

```text
GetAudioCodec() @ 0x42021876
  → Es8311AudioCodec ctor @ 0x4200c072
  → dout=26, din=27
```

`CreateDuplexChannels` 反汇编也把第 4 个参数写入 `.dout`、第 5 个写入
`.din`，没有内部交换。故 OTA 确实是 TX26/RX27。

factory 的结构体在 `0x423c1a24` 含 `24, 25, 26, 27`，但字段顺序依赖
它使用的 BSP 版本；在没有类型信息前，不能把它当成第二个独立方向证据。

## 3. 当前可执行结论

在这块板子上：

```text
I2S RX = GPIO27   （V5 实测）
I2S TX = GPIO26   （与 OTA 配置一致，待扬声器 A/B 复核）
```

board draft 暂按 **TX26 / RX27**，理由：

1. V5 已经证明 RX27 能收到数据。
2. OTA 的 duplex 配置明确使用 TX26/RX27。
3. 改成 TX27/RX26 会同时与这两项冲突，风险更大。

但必须保留警告：

- 原理图网名与公共 BSP 注释都指向相反方向。
- 可能是原理图网名沿用了 codec 侧命名，而 PCB/模组实际走线不同；
  也可能是该批次/版本与公共 BSP 不一致。
- **不要在没有 A/B 测试的情况下“修正”board draft 的 `.dout/.din`。**

## 4. 建议的硬件裁决

按成本从低到高：

1. **麦克风 A/B**（已做过 V4/V5）：分别用 RX26、RX27 录音，比较非零
   RMS 和 1 kHz 峰值。当前结果支持 RX27。
2. **扬声器 A/B**：保持 RX27，分别把 TX 设为 26 和 27，播放 1 kHz，
   记录哪个能出声。不要同时改两个方向。
3. **逻辑分析仪**：在 factory 播放/录音时同时抓 GPIO26/27、BCLK、WS，
   看 codec `ASDOUT` 是否真的在 26 上输出。
4. **断电阻抗/通断**：确认模组 pin 与 ES8311 pin 7/9 的实际连接；这能
   直接判断是网名错误还是模组定义错误。

在完成 2 或 3 之前，I2S 方向仍标记为“工作假设”，不是最终硬件事实。

## 5. Flash/PSRAM 与电池

原理图还解决了两个长期歧义：

- 模块是 `N32R8`，物理 **32 MB Flash + 8 MB PSRAM**；factory 镜像头是
  16 MB、ota_0 是 32 MB，分区表实际只用到 `0xf10000`。详见
  [Flash 容量审计](11_flash_capacity_audit.md)。
- 电池不是 ESP32 ADC 引脚，而是 CH32 `PC4/EXIO_ADC`；factory 未发现
  ADC 读取路径。详见 [电池检测](10_battery_ch32_adc.md)。

## 6. 相关文档

- [音频与 I2S](03_audio_i2s.md)
- [电池检测](10_battery_ch32_adc.md)
- [Flash 容量审计](11_flash_capacity_audit.md)
- [Brookesia 0.7 板级适配](08_brookesia07_board_adaptation.md)
