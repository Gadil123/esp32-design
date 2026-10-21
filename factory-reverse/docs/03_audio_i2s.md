# 03 · 音频与 I2S：本板 ES8311 引脚结论

> 结论等级：**高置信**（factory BSP + OTA Xiaozhi codec ctor + V5 实测）；仍应在新板批次上复核。
> 这是本子项目最重要的可复用硬件结论。

## 1. 推荐引脚

对本板，录音 bring-up 先使用：

| 信号 | GPIO |
| --- | ---: |
| MCLK | `GPIO_NUM_NC` |
| BCLK / SCLK | `24` |
| WS / LCLK | `25` |
| MCU → codec（TX/DOUT） | `26` |
| codec → MCU（RX/DIN） | `27` |

即：

```c
#define BSP_I2S_MCLK GPIO_NUM_NC
#define BSP_I2S_SCLK GPIO_NUM_24   // BCLK
#define BSP_I2S_LCLK GPIO_NUM_25   // WS
#define BSP_I2S_DOUT GPIO_NUM_26   // MCU TX
#define BSP_I2S_DSIN GPIO_NUM_27   // MCU RX
```

对应的 `i2s_std_gpio_config_t`：

```c
.gpio_cfg = {
    .mclk = GPIO_NUM_NC,
    .bclk = BSP_I2S_SCLK,
    .ws   = BSP_I2S_LCLK,
    .dout = BSP_I2S_DOUT,
    .din  = BSP_I2S_DSIN,
    .invert_flags = {
        .mclk_inv = false,
        .bclk_inv = false,
        .ws_inv   = false,
    },
}
```

## 2. factory BIN 证据

factory app 的 segment 0 中：

| 项目 | 值 |
| --- | --- |
| 虚拟地址 | `0x423c1a54` |
| 文件偏移 | `0x1a1a54` |
| 采样率字段 | `22050`（`0x5622`，位于 `0x423c1a24`） |
| 字节 | `FF FF FF FF 18 00 00 00 19 00 00 00 1A 00 00 00 1B 00 00 00` |

解释：

```text
mclk = -1 / NC
bclk = 0x18 = 24
ws   = 0x19 = 25
dout = 0x1A = 26
din  = 0x1B = 27
```

这是 factory BSP 的 `i2s_std_config_t` 字段，不是 Xiaozhi `Es8311AudioCodec` 的构造参数。它证明官方 factory BSP 使用 **TX26/RX27**。

### 2.1 OTA Xiaozhi 的独立交叉验证

`ota_0` 的 `GetAudioCodec()`（`0x42021876`）直接调用
`Es8311AudioCodec` 构造函数（`0x4200c072`），参数为：

```text
i2c port 0, in/out 24000 Hz,
mclk=-1, bclk=0x18(24), ws=0x19(25),
dout=0x1a(26), din=0x1b(27),
pa=-1, es8311=0x30, use_mclk=0, pa_inverted=0
```

这与 Xiaozhi v2.2.6 的
`main/audio/codecs/es8311_audio_codec.cc` 构造签名逐项一致。两个官方 app
（factory BSP 与 OTA Xiaozhi）都给出 **TX26/RX27**，因此这不是单一镜像的
偶然常量。

## 3. 公共 BSP 的不一致

公共 BSP 头文件：

```c
#define BSP_I2S_DOUT (GPIO_NUM_26)
#define BSP_I2S_DSIN (GPIO_NUM_27)
```

公共 BSP 当前源码：

```c
.dout = BSP_I2S_DSIN,  /* 27, 注释称 MCU TX -> codec DSDIN */
.din  = BSP_I2S_DOUT,  /* 26, 注释称 MCU RX <- codec ASDOUT */
```

这与 factory BIN 相反。

结合本项目之前的实测：

| 尝试 | 配置 | 结果 |
| --- | --- | --- |
| V4 | RX26 | 音频数据全 0，PCNT 0 edge |
| V5 | RX27（`.din=27`） | 录音正常 |

结论：

- **本板应使用 RX27/TX26。**
- 公共 BSP 的“schematic 修正”很可能把数据脚方向理解反了。
- schematic 网络名 `ASDOUT/DSDIN` 容易误导；以 factory BSP 和实板录音为准。
- 不要在未验证的情况下把 `.dout` 和 `.din` 再互换一次。

> 说明：官方 factory app 的 `AIChats` 只是启动器；真正使用 `Es8311AudioCodec` 的是 `ota_0` 的 Xiaozhi。因此 factory BSP 的引脚配置是硬件事实，但“factory app 是否完整启用麦克风”不是本结论的依据。

## 4. 采样率不要盲目复制

factory BSP 的默认采样率是 **22050 Hz**，OTA Xiaozhi 的 duplex codec 是 **24000 Hz**：

- 它们分别对应两套 app 的默认配置，不应互相覆盖。
- Brookesia 0.7 草案选 16000 Hz，是为了对齐 recorder/player 的默认值；这是迁移选择，不是官方原值。
- 复用引脚时，采样率按语音组件和 ES8311 的实际配置设置，不要只改引脚后照抄 22050/24000。

## 5. 麦克风初始化边界

公共 BSP：

- `bsp_audio_init()` 创建 TX/RX 两个 I2S channel，并创建 ES8311 设备。
- `bsp_audio_codec_speaker_init()` 有实现。
- `bsp_audio_codec_microphone_init()` **只有声明，没有实现**。

这意味着：

1. 只改 I2S 引脚宏不一定能得到可用麦克风。
2. 需要补一个输入方向的 `esp_codec_dev` 初始化（`ESP_CODEC_DEV_TYPE_IN`），或在 duplex codec 配置中同时打开输入。
3. 初始化顺序要保证 I2C、I2S、ES8311 都成功；不要在 I2C 失败后继续读音频。
4. 录音读取应使用 `esp_codec_dev_read()` 或对应 I2S RX 通道；不要用 speaker 句柄读。

可复用的实现思路（不是已验证代码）：

```text
bsp_audio_init()                 // 创建 I2S TX/RX
bsp_i2c_init()                   // ES8311 控制总线
es8311_codec_new(...)            // codec driver
esp_codec_dev_new(dev_type=IN)   // 输入设备
esp_codec_dev_open(fs=...)
esp_codec_dev_read(...)          // 读取 PCM
```

在补实现前，先确认：

- ES8311 的 I2C 地址和 `pa_pin`/功放使能是否与扬声器路径共用。
- 输入增益、麦克风模式（模拟/数字）和采样率。
- 是否需要 CH32V003 扩展 IO 参与功放/通道切换。
- 读到的 PCM 是 16-bit mono 还是其他格式。

## 6. 验证方法

录音问题不要只看“编译通过”或“没有报错”。建议按顺序：

1. **I2C 探测**：确认 ES8311 地址可读，读 ID/寄存器不失败。
2. **I2S 时钟**：确认 BCLK/WS 有波形；MCLK 为 NC 时确认 codec 工作在 slave 模式。
3. **RX 数据**：读 `i2s_channel_read` 返回值，统计缓冲区非零比例和 RMS；不要只打印前几个字节。
4. **已知信号**：播放/输入 1 kHz 测试音，检查频谱或过零率，而不是只看 PCM 是否全 0。
5. **双通道/单通道**：确认 slot mode 与 ES8311 配置一致；单声道时避免把空闲 slot 当有效数据。
6. **资源冲突**：确认 speaker 和 mic 没有同时以不兼容的采样率/通道模式打开。

## 7. 相关文档

- [固件清单](01_firmware_inventory.md)
- [AI 启动与网络](06_ai_bringup.md)
- [完整静态分析](../reference/full-static-analysis.md)
