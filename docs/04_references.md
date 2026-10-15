# 04 · 研究链接与设计借鉴（非全部适配）

本页用于记录研究线索及**可复用的思路**，不意味着相应产品的 STL、BOM、PCB 能直接适配微雪 C5。

## 厂商第一手资料（优先级最高）

- [Waveshare ESP32-C5-Touch-LCD-2.8 产品资料](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/)：型号、芯片、屏幕、麦克风、功放、电池和 GPIO。
- [Waveshare 出厂固件使用说明](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/Instructions-For-Use/)：BOOT 下载方式及软件按键用例、BAT_PWR 实际行为。
- [Waveshare 硬件资料目录](https://docs.waveshare.net/ESP32-C5-Touch-LCD-2.8/Resources-And-Documents/)。
- [Waveshare 官方 GitHub 源码+结构+原理图](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8)；[dimensions](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/tree/main/dimensions)、[schematic](https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/tree/main/schematic)。

## 外观和按键结构

**FoloToy AI Passport** — [官网](https://ai-passport.folotoy.cn/) / [GitHub](https://github.com/FoloToy/ai-passport)
- 参考点：薄卡片机身、侧边实体按钮、简洁正面及对内部硬件的视觉处理。
- 它是**定制 PCB**，不能把微型侧键的机械结构原样套用到现成微雪开发板。
- 它的开关具体品牌/料号，前期讨论**尚未确证**，不能据此采购。
- 早前研究到其三颗功能键可采用 ADC 电阻分压；那是 AI Passport 电路特征，不是 C5 要采用的方案。

**Adafruit Pocket PiGRRL** — [YouTube 制作视频（用户提供）](https://www.youtube.com/watch?v=dEdVEQqoIJQ) / [官方教程](https://learn.adafruit.com/pocket-pigrrl)
- 参考点：普通轻触开关 + 洞洞板 + 打印键帽 + 3D 外壳的可制作性。
- V1 由于复用微雪原生开关，**不采用该正面按键方案**；V2 可以参照。

**用户提供的“Vibe Coding 便携开发助手”概念图**
- 外观参考：黑色工业风、分层前框、按钮明确、有秩序的 USB/麦克风/LED 装饰。
- 该图片是概念效果，不是权威 BOM / CAD。其 1.47in 显示器、旋钮、无线充电与 2.8in C5 不兼容；不能直接作为结构底图。
- V2 可能恢复两颗正面实体键，但不提前纳入 V1。

**ESP32 电子纸 / XTEINK X4 等案例（前期讨论）**
- 借鉴微型侧边键与薄型正面视觉；多数使用定制 PCB / FPC，未能证明“无需定制 PCB 的微雪 C5 外加侧键”。
- 本项目 V1 的突破口是**原生 C5 PCB 已有 BOOT、RESET、BAT_PWR**，不再找额外侧向开关或 FPC。

## 已研究、暂不采用的主控或方案

- Waveshare S3 2.8：屏幕合适，但需额外麦克风；C5 集成度更高。
- Waveshare S3 1.54：音频集成但屏幕太小。
- DFRobot 行空板 K10：含 ESP32-S3 / 双麦 / 喇叭 / 2.8in；板载电池充电配置不符合我们最终简化路线。
- T-Deck、Cardputer、Beepy、Radxa Zero 等：大小、操作形态或成本不符 V1 方向。
- 单独侧边微动开关、正面普通按键洞洞板、USB-C 延长组件：技术上可行但当前**无必要**，留作 V2/备选。

## 如何使用来源

技术事实首先引用官方产品及原始 STEP/原理图；论坛和视频只用于做法参考。缺少 SKU、电池尺寸、开关精确安装尺寸时，应写**待核实**，而不是把社区估计当成官方参数。
