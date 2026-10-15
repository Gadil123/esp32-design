# 06 · Waveshare ESP32-C5-Touch-LCD-2.8 官方资料索引与核对摘录

核对日期：**2026-10-15**。当前以微雪公开产品文档、官方 GitHub 项目及官方 PCB/尺寸图为准。此文件是经核对的**引用索引/摘要**，不能代替机电 STEP 实物校核。

## A. 官方原始资料与直达入口

| 类别 | 官方文件/页面 | V1 用途 |
| --- | --- | --- |
| 产品概览、接口表、板载资源照片 | [docs.waveshare.net / ESP32-C5-Touch-LCD-2.8](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/) | 权威硬件规格、板上元件名称 |
| 官方资源原图（PCB 背面横图） | [board-components.webp](https://docs.waveshare.net/assets/images/2.8-2-b2839d1e49b0c05c1611a558a82ca905.webp) | USB-C、麦克风、BAT_PWR/RESET/BOOT 相对位置 **以此为准** |
| 官方尺寸标注原图（屏幕正面+PCB 背面） | [board-dimensions.webp](https://docs.waveshare.net/assets/images/2.8-5-4fb313cb4149fd08061897e8112016ca.webp) | 屏幕/PCB 外形、安装孔中心距 |
| 产品资源导航 | [相关资料](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/Resources-And-Documents/) | 器件手册、原理图/结构/示例 |
| PCB 机械 STEP | [dimensions/ESP32-C5-Touch-LCD-2.8.stp](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/dimensions/ESP32-C5-Touch-LCD-2.8.stp) | 最终外壳碰撞、孔位、按键和 USB 配合；**必须用** |
| PCB 机械 DXF | [dimensions/ESP32-C5-Touch-LCD-2.8.dxf](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/dimensions/ESP32-C5-Touch-LCD-2.8.dxf) | 2D 加工基准 |
| 板卡尺寸 PDF | [dimensions/ESP32-C5-Touch-LCD-2.8.pdf](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/dimensions/ESP32-C5-Touch-LCD-2.8.pdf) | 标注尺寸与结构校核 |
| 官方电路原理图 PDF | [schematic/ESP32-C5-Touch-LCD-2.8.pdf](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/schematic/ESP32-C5-Touch-LCD-2.8.pdf) | 电源/按键/音频/IO 原理 |
| 官方固件使用手册 | [出厂固件使用说明](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/Instructions-For-Use/) | BAT_PWR / BOOT、刷机、出厂应用 |
| 厂商软件工程总览 | [官方 GitHub README_ZH](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/README_ZH.md) | 编译环境、软件组件、示例 |
| 组件硬件相容性勘误 | [兼容性说明](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/docs/compatibility_ZH.md) | ESP-IDF/Arduino 与 **音频引脚方向** |
| 实际验证边界 | [官方验证记录](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/docs/validation_ZH.md) | 官方 CI 编译 vs 实物测试边界 |
| 官方案例 | [ESP-IDF 示例目录](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/tree/main/examples/esp-idf) | BSP、屏幕、音频等功能 |
| 官方 Arduino 案例 | [Arduino 示例目录](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/tree/main/examples/arduino) | 基础外围驱动 |
| 出厂演示固件 | [Firmware](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/tree/main/Firmware) | 裸板回退至出厂应用，**不直接用于 Pocket Pi 成品** |

**资料保存策略：** 上表保存**原始官方链接、核对时间、摘要与疑点**；原版 PDF、STEP、DXF 仍由微雪维护。当前不擅自重发布厂商 CAD/图片文件。要做 CAD 时从上方官方链接取得原版。

### 官方 PCB 背面原图

![Waveshare PCB 背面横图：USB-C 左，BAT_PWR/RESET/BOOT 在上，麦克风在下](https://docs.waveshare.net/assets/images/2.8-2-b2839d1e49b0c05c1611a558a82ca905.webp)

**方向校正：上图整体顺时针旋转 90° 后，USB-C 朝上、麦克风在左、三颗按键在右。** 这是 PCB **背面**视角；翻至屏幕正面时左右镜像。另见 [方向逻辑图](../assets/orientation_diagram.svg) 与 [纯图片旋转查看器](../assets/official_board_rotated_viewer.html)。

## B. 官方元件编号（直接对应背面资源原图）

| 编号 | 组件 | V1 结构影响 |
| --- | --- | --- |
| **8** | 板载贴片麦克风 | 直接开孔、声孔方向须实测 |
| **3** | MX1.25 2Pin 扬声器接口 | 外接独立扬声器，背部固定槽 |
| **4** | ES8311 音频编解码器 | 声音采集和播放功能 |
| **5** | NS4150B 音频功放 | 喇叭驱动 |
| **11** | MX1.25 2Pin 电池接口 | 3.7V 电池、充电管理 |
| **13** | 充电指示灯 | 不是可随意控制的应用状态灯 |
| **14** | USB Type-C | V1 保留原生接口，朝上 |
| **19** | 开关机芯片 | 原生电源管理 |
| **20** | BAT_PWR 原生按键 | 电池开/关，不是第三颗应用自定义键 |
| **22** | RESET 原生按键 | 维护孔、避免误触 |
| **23** | BOOT 原生按键 | GPIO28，允许用户交互 / 语音录音键候选 |
| **24** | 2.8in 屏幕排线座 | 屏幕机械固定和走线必须避让 |
| 10 | SH1.0 2Pin RTC 电池接口 | V1 无需额外布置 |
| 17 | SH1.0 12Pin 连接座 | 如无外设不占用但仍须考虑壳体净空 |
| 18 | Micro SD 插槽 | V1 可不开放外部插拔 |
| 12、16 | UART / I2C 接口 | V1 不新增键/传感器 |
| 1、2、6、7、9 等 | 主控、扩展焊盘、传感器 | 一般不需要单独开孔 |

元件编号依据 [官方背面 PCB 图片及其图例](https://docs.waveshare.net/assets/images/2.8-2-b2839d1e49b0c05c1611a558a82ca905.webp)。

## C. 规格（官方确认）

| 条目 | 官方资料 |
| --- | --- |
| SKU | 34957（普通）、34958（-EN） |
| SoC | ESP32-C5-WROOM-1，RISC-V，最高 240MHz |
| 内存 | 8MB PSRAM；产品规格写 32MB Flash（见下方配置疑点） |
| 无线 | 2.4GHz / 5GHz Wi-Fi，Bluetooth 5 LE，IEEE 802.15.4 |
| 显示器 | 2.8in LCD，240×320，262K 彩色；官方软件工程描述 ST7789 |
| 触摸 | I2C 电容触摸；官方软件工程标注 CST3530 / 0x58 |
| 音频 | 贴片麦克风、ES8311 codec、NS4150B 功放、配套独立扬声器 |
| 电源 | USB-C，板载充电管理，3.7V MX1.25 锂电接口 |
| 其他 | QMI8658 六轴传感器、PCF85063A RTC、SHTC3 温湿度、Micro SD、CH32V003 IO 扩展器 |
| 固件开发 | ESP-IDF / Arduino，官方仓库提供例程 |

## D. 尺寸（已从微雪**公开尺寸标注图**读取）

- **显示屏组件外轮廓：宽 50.54mm × 高 73.06mm**
- **PCB：宽 49.90mm × 高 69.00mm**
- **显示有效区域：宽 43.20mm × 高 57.60mm**
- **四个安装孔：M2.5**；官方图可读到水平 41.00mm、垂直 60.00mm 孔距及侧边定位信息。
- **注意：** 上述为原始官方示意图的标注读数；最终应在 STEP/DXF 中复测螺丝孔坐标、3D 高度和所有定位，以避免将标注/基准选错。

来源：[官方尺寸图](https://docs.waveshare.net/assets/images/2.8-5-4fb313cb4149fd08061897e8112016ca.webp)。

## E. 官方引脚 / 设备连接（固件开发时可引用）

| 外设 | ESP32-C5 / CH32 连接 |
| --- | --- |
| LCD SPI | SCK GPIO6，MOSI GPIO7，DC GPIO9，CS GPIO10 |
| LCD 复位和背光 | CH32 EXIO1 / CH32 PWM |
| Touch | SDA GPIO0，SCL GPIO1，INT GPIO5，RESET CH32 EXIO0 |
| SD 卡 | SPI 共用 GPIO6/7，MISO GPIO8，CS GPIO23 |
| I2C 总线 | SDA GPIO0，SCL GPIO1 |
| IMU | GPIO4 中断，I2C GPIO0/1 |
| RTC | I2C GPIO0/1，INT CH32 EXIO2 |
| 音频 | BCLK GPIO24，LRCK GPIO25，GPIO26/GPIO27 数据线；**方向参见勘误** |
| 功放 | CH32 EXIO3 控制 |
| UART0 | TX GPIO11，RX GPIO12 |
| USB | D+ GPIO14，D− GPIO13 |
| BOOT | GPIO28 |
| 电量及背光 | CH32 的 ADC/PWM 控制 |

数据来源：[微雪官网引脚表](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/)。

## F. 官方资料之间存在的差异／未完成的验证（必须保留）

1. **Flash 容量 vs Arduino 构建配置：** 产品主页标示 **32MB Flash**，但官方 GitHub README_ZH 中 Arduino 示例要求选择 **16MB Flash** 和 16M 分区布局。尚未确认是例程兼容配置还是实物版本差异，**不能擅自将构建设置当作产品实际 Flash 容量**；等待实际 SKU 和板卡检测。
2. **I²S 音频数据方向的表述：** 官网接口表写 GPIO26 I2S_ASDOUT / GPIO27 I2S_DSDIN，容易误读为 MCU TX/RX；官方 [compatibility_ZH.md](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/docs/compatibility_ZH.md) 按**以 MCU 为准**定义 GPIO26=RX（codec ASDOUT）、GPIO27=TX（codec DSDIN），并明确指出旧 BSP 方向有误。这是固件实现关键注意项；**优先依照电路原理图和新版兼容文档核对**。
3. **官方 CI 与硬件验证不同：** 官方 2026-10-13 的 [验证记录](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/blob/main/docs/validation_ZH.md) 确认多版本编译通过，但注明硬件显示、触摸、音频等**尚未实板测试**。不据此保证 Pocket Pi 固件直接可用。
4. **实物与图片差异：** 机械外壳需核对到手硬件版本，STEP 可能不含某些零件的完整动态按压行程；不得用原理图估键帽公差。
5. **配件清单：** 文档列出喇叭、电池作为出厂例程测试时的需准备件，**不能保证淘宝单板 SKU 已附赠电池或扬声器**，以实际套餐为准。
6. **电池：** 只确定板载充电和 3.7V MX1.25 连接器；电芯容积、引线方向、保护与极性尚待客服核对。

## G. V1 与原生三键的明确边界

官网：[出厂固件使用说明](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/Instructions-For-Use/)：

- BOOT：按住并接 USB 可进入下载；小智 AI 应用中长按用于返回主界面；普通 APP 也有单击用途，因此**可做软件控制键**，但用户输入方案须处理开机时的下载状态。
- BAT_PWR：电池模式约长按 2 秒关机，关机后再按开机；**硬件管理开关**。
- RESET：硬件复位，**不是可重新绑定的通用应用键**。

V1 结构可保留这三颗实体原生开关，但“保留三颗”不代表“三颗都能作为自定义功能键”。日常操作主要交给 BOOT + 触摸屏。

## H. 声学和机械事实边界

- 麦克风的位置能从官方**背面资源原图编号 8**识别，但**声孔朝向、孔心坐标与外壳声孔设计**尚未从官方 STEP + 实物综合确认。
- 扬声器为外接独立件，位置可选在背部；直出音孔即可作为第一版目标，不做复杂转向声道。
- 三颗原生按钮按压方向、凸出高度、壳体导向公差：仍需 STEP/实物测量，不可根据板载资源俯视图推断完整机械行程。
- 关闭屏幕/睡眠、无线联网、电池续航性能均须实机测试，官方功能列表不等于量产效果保证。

## I. 以后更新本文件的规则

任何新结论在旁边附上**厂商出处与查阅日期**。改变主板版本、电池、键帽或设计方向时，先更新 [01 设计决策](01_scope_decisions.md) 和 [05 验证清单](05_validation_checklist.md)；不得直接复用旧渲染图、旧方位图或猜测孔位。
