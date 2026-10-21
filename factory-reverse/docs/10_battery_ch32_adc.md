# 10 · 电池检测：BAT_ADC → CH32V003 → I2C

> 结论等级：**硬件路径高置信；factory 软件是否使用电池 ADC 为“高置信否证”，但受反编译边界限制。**
> 本文只记录静态证据和 bring-up 方法，不声称已经实机测过电池百分比。

## 1. 硬件路径

原理图已确认：

```text
VBAT ── R7 200K ±1% ──┬── BAT_ADC ── R52 10K ── CH32V003 PC4 / EXIO_ADC (pin 11)
                       │
                       ├── R10 100K ±1% ── GND
                       ├── C9 100nF ── GND
                       └── C10 100nF ── GND
```

- `R7` / `R10` 构成 3:1 分压；`BAT_ADC` 名义电压约为 `VBAT / 3`。
- 4.2 V 电池对应 ADC 节点约 `1.4 V`，在 CH32V003 的 3.3 V ADC 范围内。
- `R52 10K` 是到 CH32 `PC4` 的串联电阻；`C9/C10` 为滤波。
- 原理图还确认 `EXIO_PWM/PC3 → LCD_BL`、`EXIO3 → PA_CTRL`、
  `EXIO0 → TP_RST`、`EXIO1 → LCD_RST`。

**待确认：** CH32 的 ADC 参考电压/VDD 实际是 3.3 V，以及 `R52` 是否影响
校准；上电量产前应用万用表在每个电池电压点复核。

## 2. CH32 协议

ESP 侧组件 `custom_io_expander_ch32v003` 定义：

| 寄存器 | 地址 | 用途 |
| --- | ---: | --- |
| 方向 | `0x02` | `0xff` = 输入 |
| 输出 | `0x03` | 输出电平 |
| 输入 | `0x04` | 读 8 位输入 |
| PWM | `0x05` | 背光 `0..255` |
| ADC | `0x06` | 返回 2 字节，小端 |
| RTC/INT | `0x07` | 中断状态 |

公开的 CH32 component（`custom_io_expander_ch32v003` 1.0.2）已经提供
`custom_io_expander_get_adc(handle, &adc)`，内部就是读寄存器 `0x06`，文档
标称返回 `0..1023`。迁移时应优先复用该 helper，而不是自己拼 I2C 事务。

底层协议是标准 I2C `write reg 0x06, read 2 bytes`：

```c
uint8_t temp[2] = {0};
i2c_master_transmit_receive(dev, (uint8_t[]){0x06}, 1, temp, 2, 1000);
uint16_t adc = (temp[1] << 8) | temp[0];   // 组件文档标称 0..1023
```

换算假设 CH32 ADC 为 10-bit、Vref = 3.3 V：

```text
Vbat_adc = adc / 1023.0 * 3.3
Vbat     = Vbat_adc * (200K + 100K) / 100K = Vbat_adc * 3.0
```

百分比曲线不是硬件事实；factory 未给出可用映射。迁移时应先用电压点
（4.2 / 4.0 / 3.8 / 3.6 / 3.4 / 3.2 V）记录 ADC，再决定线性或分段曲线。

## 3. Factory 是否使用电池 ADC

### 3.1 CH32 驱动函数

CH32 的 7-bit I2C 地址是 `0x24`；Board Manager YAML 使用左移后的 `0x48`，
运行时由 `dev_gpio_expander` 右移回 `0x24`。

factory app 中可定位：

| 地址 | 语义 |
| --- | --- |
| `0x42046950` | `custom_io_expander_new_i2c_ch32v003` wrapper，caller `0x42023858` |
| `0x42046724` | 写方向寄存器 `0x02` |
| `0x420467a6` | 写输出寄存器 `0x03` |
| `0x4204682a` | reset：方向 `0xff`、输出 `0x00` |
| `0x420468ce` | 读输入寄存器 `0x04`，I2C 调用点 `0x420468f2` |
| `0x42046b2c` | `custom_io_expander_set_pwm`，唯一 caller `0x42024368` |
| `0x42046b9c` / `0x42046be2` | C++ 虚函数 thunk |
| `0x42046c28` | 通用输入读取，caller `0x420358ee` / `0x4203580e` |

### 3.2 没找到 ADC 路径

- factory / OTA 字符串中**没有** `Read adc reg failed`；也就是说公开
  component 的 `custom_io_expander_get_adc()` 没有被链接进来。这条单独看
  很弱：若函数未被引用，链接器可能把整个函数/字符串都丢掉。
- 公开 component 的 helper 确实存在（见第 2 节），所以“没有字符串”只说明
  **stock app 没调用**，不说明驱动不支持。
- CH32 相关代码只出现 command byte `4`（输入寄存器）；**没有 command byte 6**。
  这是比“字符串不存在”更强的证据。
- 扫描所有 `i2c_master_transmit_receive` 调用点，未发现 `0x06` 的
  `transmit_receive` 组合。
- `set_pwm` 的唯一 caller 是 `bsp_display_brightness_set`，与电池无关。

因此静态证据倾向：**factory app 没有调用 CH32 ADC**。这不等价于 CH32
固件没有 ADC 功能；只说明 ESP 侧 stock app 未使用。

### 3.3 StatusBar 电池图标

Brookesia StatusBar 中：

| 地址 | 语义 |
| --- | --- |
| `0x4206cc28` | `setBatteryPercent`，唯一 caller `0x4206ea62` |
| `0x4206ea62` | `beginBattery`，初始化时调用 `setBatteryPercent(..., 0, 100)` |
| `0x4206c53e` | `updateBatteryByNewData`，读取既有数据字段 `+0x60` / `+0x63` |
| `0x4206eed2` | `beginBattery` 的 caller |

`updateBatteryByNewData` 只更新 UI/充电状态，没有硬件 ADC 调用。反编译在
`0x4206ea62` 附近有控制流恢复失败，不能排除未识别分支；但结合“无 ADC
字符串、无 command byte 6、无 transmit_receive 调用点”，结论仍然很强。

## 4. Brookesia 0.7 的限制

`brookesia_hal_adaptor/src/power/battery_adc_impl.cpp` 只支持：

```text
CONFIG_BROOKESIA_HAL_ADAPTOR_POWER_BATTERY_IMPL_ADC
CONFIG_ESP_BOARD_PERIPH_ADC_SUPPORT
```

它通过 board manager 查找名为 `adc_battery_voltage` /
`adc_battery_charge` 的 ESP32 ADC 外设；**不能直接读取 CH32 的 I2C ADC**。
因此本板不能只打开 `CONFIG_BROOKESIA_HAL_ADAPTOR_ENABLE_POWER_DEVICE=y`
就得到电池百分比。

迁移需要二选一：

1. 自定义 `PowerBatteryIface`：持有 CH32 expander handle，调用
   `custom_io_expander_get_adc()`（内部读 `0x06`），换算电压/百分比；这是
   最小改动。
2. 在 HAL adaptor 中新增 CH32 ADC backend，并让 `battery_adc_impl` 按
   board 选择后端；改动更大，但可复用。

接口实现时应处理：

- CH32 未初始化/总线失败 → 返回未知，不要让 UI 显示 0%。
- ADC 抖动 → 多次采样取中位数/滑动平均。
- 充电状态：本板没有确认的 CHG 引脚；不要伪造 `is_charging`。
- 低电关机阈值必须实测定标。

## 5. Bring-up 顺序

1. I2C 探测 `0x24`，读方向/输出寄存器确认 CH32 在线。
2. 读 `0x06` 原始值；用万用表同时测 `VBAT` 和 `BAT_ADC`。
3. 至少在 3 个电压点验证 `Vbat = adc/1023*3.3*3`。
4. 加入中值滤波，再决定百分比曲线。
5. 最后才接 `PowerBatteryIface`，并保留“未知/不显示”兜底。

## 6. 证据边界

- 原理图确认了硬件路径，但没有实机 ADC 读数。
- factory 未使用 ADC 是静态否证；不能证明 CH32 固件无 ADC。
- 电池百分比曲线、充电检测、低电阈值均未恢复。
- 不要在没有万用表对照的情况下把某个 ADC 值当成“满电”。

## 7. 相关文档

- [原理图交叉核对](12_schematic_crosscheck.md)
- [Brookesia 0.7 板级适配](08_brookesia07_board_adaptation.md)
- [完整静态分析](../reference/full-static-analysis.md)
