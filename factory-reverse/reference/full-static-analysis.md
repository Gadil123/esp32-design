> 证据附录：这是原始静态分析全文，保留地址、字符串、分区和 Ghidra 记录。  
> 规范性摘要和面向 Pocket OS 的复用建议见上级 [README](../README.md) 与 `docs/`。  
> 本文中的“推断/高置信”不因放在参考目录而升级为已实机验证。

# ESP32-C5-Touch-LCD-2.8 Factory 固件静态逆向分析

分析日期：2026-10-21

分析对象：

- `/home/gadil/esp32-project/ESP32-C5-Touch-LCD-2.8-FactoryAppV1.1.bin`
- SHA256：`92d0f25d7b8c43900c8882e2ca9cee1ca7c8a9338504bd392567f3d1e8cdf174`
- 大小：`13699516` 字节（`0xd109bc`）
- 与官方 release v1.1.0 的下载副本 `/tmp/factory-reverse/official.bin` 完全一致，`cmp` 返回 0。

分析产物目录：`/tmp/factory-reverse`

---

## 1. 结论摘要

### 1.1 完整官方源码：NO-GO

无法从该 BIN 恢复完整可编译源码。可以恢复镜像结构、分区、板级常量、字符串、应用清单和部分函数逻辑，但以下内容未公开：

- factory app 的完整 `main.cpp` 和 `AIChats.cpp`
- `Qmi8658Ball`、`MusicPlayer`、`Weather`、`Games`、`Photos` 等 factory 自定义 app
- Xiaozhi v2.2.6 中本板的完整 board profile
- 官方 factory 构建配置、sdkconfig、组件版本锁定和私有源码

公开仓库只有示例和二进制；上游 Xiaozhi v2.2.6 没有 `esp32-c5-touch-lcd-2.8` 这个 board。

### 1.2 官方 AI 为什么“能用”：factory app 只是启动器

官方镜像包含两套 app：

- `factory` 分区：Brookesia Phone 桌面/demo
- `ota_0` 分区：完整 Xiaozhi v2.2.6 语音应用

factory 的 `AIChats` 不是完整 AI 应用，而是**子应用启动器**。其二进制字符串明确包含：

```text
未找到子工程分区（ota_0）
已从sub_app分区启动，无需修改
成功设置sub_app为启动分区，即将重启...
设置启动分区失败: %s
./components/AIChats/AIChats.cpp
```

推断其行为：点击 `AIChats` 后，检查 `ota_0` 分区，写入启动分区并重启；重启后由 `ota_0` 的 Xiaozhi 提供完整语音 AI。这与镜像里同时存在 `01_factory` 和 `xiaozhi` 两套 app 完全吻合。

因此：

- factory app 内未见 Xiaozhi/MQTT/WebSocket/wakenet/Es8311AudioCodec 语音栈。
- 完整语音栈在 `ota_0`。
- 官方“factory 固件可用 AI”很可能是指通过 `AIChats` 切换到 `ota_0` 后的 Xiaozhi，而不是 factory app 自身完成了 AI。
- 初始 `otadata` 全 `0xFF`，所以首次启动仍是 factory；切换后 `otadata` 才会指向 `ota_0`。

### 1.3 音频引脚：本板应为 RX=27、TX=26

factory BIN 内的 BSP `i2s_std_config_t` 证据：

- 虚拟地址：`0x423c1a54`
- 文件偏移：`0x1a1a54`
- 采样率：`22050`（`0x5622`，位于 `0x423c1a24`）
- gpio 配置字节：

```text
FF FF FF FF  18 00 00 00  19 00 00 00  1A 00 00 00  1B 00 00 00
mclk=NC      bclk=24      ws=25        dout=26      din=27
```

即 factory BSP 使用 **DOUT/TX=26、DIN/RX=27**。

当前公共 BSP 头文件仍是：

```c
#define BSP_I2S_DOUT (GPIO_NUM_26)
#define BSP_I2S_DSIN (GPIO_NUM_27)
```

但公共 BSP 源码把数据脚改成了：

```c
.dout = BSP_I2S_DSIN,  /* 27 */
.din  = BSP_I2S_DOUT,  /* 26 */
```

这与 factory 二进制相反。结合 V4 使用 RX26 失败、V5 使用 `.din=27` 成功，结论是：

- **本板录音应使用 RX=27、TX=26。**
- 公共 BSP 的“schematic 修正”很可能把数据脚方向改反了。
- schematic 上的 `ASDOUT/DSDIN` 网络名容易误导，应以 factory BSP 配置和实测为准。

注意：factory app 的 `bsp_audio_init` 确实创建了 duplex I2S 并初始化 ES8311，但 factory app 的字符串里只明确出现 `bsp_audio_codec_speaker_init`，没有公开 BSP 中缺失的 microphone init 实现。因此“factory app 是否完整启用了麦克风路径”不能仅凭这一点断言；引脚配置本身是强证据。

### 1.4 重力球卡 95%：尚未证明根因

factory 的 `Qmi8658Ball` 字符串包含完整的校准流程：

```text
GravityBall
Calibrating... 0%
Press BOOT button to recalibrate
calibration_task
qmi8658_init(_qmi8658_dev, _i2c_bus, QMI8658_ADDRESS_HIGH)
perform_level_calibration
Starting level calibration...
Calibration unstable (X: %.4f, Y: %.4f)
Calibration complete. Bias X: %.4f, Y: %.4f
Calibrating... %d%%
Calibration complete!
ball_update
Calibration failed! Retrying...
calibration_retry
calibration_recalib
```

95% 卡住不是已证明的结论，较可能的方向：

1. `calibration_task` 一直等待稳定采样，`Calibration unstable` 反复触发。
2. 校准成功/失败后没有正确更新进度，LVGL 进度停留在 95%。
3. `calibration_retry`/`calibration_recalib` 形成重试循环，但没有超时或错误提示。
4. 进度更新与 LVGL 锁/任务优先级冲突，UI 不再刷新，但任务可能仍在运行。

需要串口日志确认最后一条是 `Calibration unstable`、`Calibration complete` 还是 `Calibration failed! Retrying...`。仅凭静态字符串不能把 95% 定因到某个函数。

### 1.5 AI 初始化循环：优先查 Wi-Fi/激活，不是 assets

Xiaozhi 的初始化链：

```text
Application::Initialize()
  -> board.StartNetwork()
  -> WifiBoard::TryWifiConnect()
  -> 无 SSID: StartWifiConfigMode()
  -> 有 SSID: 连接 Wi-Fi
  -> 网络连接事件
  -> HandleNetworkConnectedEvent()
  -> ActivationTask()
       -> CheckAssetsVersion()
       -> CheckNewVersion()
       -> InitializeProtocol()
```

本镜像的 `assets` 包是完整的，`index.json` 版本为 1，`srmodels.bin` 存在，因此“assets 缺失导致循环”的可能性较低。

更像循环的来源：

1. NVS 为空，没有 Wi-Fi SSID，进入配网模式，等待用户配置。
2. 有 SSID 但网络不通，`CheckNewVersion()` 对 OTA 地址重试 10 次，退避时间从 10 秒开始翻倍，表现像长时间循环。
3. 需要激活时，`CheckNewVersion()` 等待激活码/激活结果，最多 10 次尝试。
4. 公共源码没有本板 board profile；如果自定义固件替换了板级文件，`GetAudioCodec()`/网络初始化失败也可能让流程停在 starting。

结论：如果看到的是“AI 初始化一直循环”，优先看串口日志和屏幕是否停在 Wi-Fi 配网/激活页；不能直接归因于音频或重力球代码。

### 1.6 Ghidra/REA

- Ghidra 12.1.4 + Temurin JDK 21 已安装。
- 用 `BinaryLoader` 导入 `factory_seg1.bin`，基址 `0x40800000`，语言 `RISCV:LE:32:default`，导入成功。
- Python Ghidra 脚本报错：`Ghidra was not started with PyGhidra. Python is not available`。
- 改用 Java GhidraScript 成功反汇编入口 `0x408002b0`，示例指令：

```text
408002b0  c.addi sp,-0x20
408002b2  c.li a5,0x1
408002b4  c.swsp ra,0x1c(sp)
408002ba  jal ra,0x4081a608
```

- 指令级反汇编可行；无符号完整反编译需要导入全部 segment、建立地址块、定义函数和交叉引用，工作量大，不能等同于恢复源码。
- `REA` 在当前环境未找到/未验证，不能声称其与 Ghidra 结果等价。

### 1.7 总体建议

| 目标 | 结论 |
|---|---|
| 恢复完整官方源码 | NO-GO |
| 提取板级/音频引脚配置 | CONDITIONAL GO |
| 复刻 Brookesia 多 APP 架构 | CONDITIONAL GO，参考价值大于直接迁移 |
| 用 Ghidra 做定向函数分析 | CONDITIONAL GO |
| 仅凭静态分析定位重力球 95% | 不足，需要串口/实机日志 |
| 仅凭静态分析定位 AI 初始化循环 | 不足，优先查 Wi-Fi/激活/OTA |

---

## 2. 镜像结构与分区

### 2.1 Bootloader

- 偏移：`0x2000`
- 大小：`0x8000`（32 KB）
- 芯片：ESP32-C5，chip ID `23`
- 入口：`0x4084bbaa`
- Flash：16 MB
- 模式/频率：DIO，80 MHz
- IDF 版本字符串：`v5.5.4`

### 2.2 分区表

| 分区 | 类型 | 子类型 | 偏移 | 大小 | 结束 |
|---|---|---:|---:|---:|---:|
| `nvs` | data | nvs | `0x9000` | 16 KB | `0xd000` |
| `otadata` | data | ota | `0xd000` | 8 KB | `0xf000` |
| `phy_init` | data | phy | `0xf000` | 4 KB | `0x10000` |
| `factory` | app | factory | `0x20000` | `0x4e2000`（5000 KB） | `0x502000` |
| `storage` | data | spiffs | `0x502000` | 4 MB | `0x902000` |
| `ota_0` | app | ota_0 | `0x910000` | 3 MB | `0xc10000` |
| `assets` | data | spiffs | `0xc10000` | 3 MB | `0xf10000` |

补充：

- 分区表结束处是 MD5/尾数据，不是全 `0xFF`；解析器在偏移 `224` 看到 `ebeb...` 属于正常尾数据。
- `otadata` 两个 entry 全 `0xFF`。
- `nvs` 全空，没有 Wi-Fi/激活信息。
- 因此首次启动选择 `factory`，不是 `ota_0`。

### 2.3 两套 app

| 项目 | factory | ota_0 |
|---|---|---|
| 偏移 | `0x20000` | `0x910000` |
| project | `01_factory` | `xiaozhi` |
| version | `1` | `2.2.6` |
| IDF | `v5.5.4` | `v5.5.4` |
| 构建日期 | `Jul 10 2026` | `Jul 10 2026` |
| 构建时间 | `15:06:55` | `14:24:47` |
| entry | `0x408002b0` | `0x408003a6` |
| segments | 5 | 5 |
| image total | `0x4caed0` | `0x262060` |
| 分区填充 | 到 `0x4e2000` | 到 `0x300000` |
| app header flash size code | 4（16 MB） | 5（32 MB） |
| ELF SHA256 | `f3f904b5c103fe9fe67a10f7f401a10e0eb378181f11502cdb91f7f63b96b21a` | `52664f27cfc4b2ebbd1750c9137e761072a49fdf91ec8e72fbbcac038481f8cc` |

factory app 的主要 segment：

| # | load address | length | 文件偏移 |
|---|---|---:|---:|
| 0 | `0x42240020` | `0x272684` | `0x20020` |
| 1 | `0x40800000` | `0xd96c` | `0x2926ac` |
| 2 | `0x42000020` | `0x2359e0` | `0x2a0020` |
| 3 | `0x4080d96c` | `0xf128` | `0x4d5a08` |
| 4 | `0x4081cb00` | `0x6370` | `0x4e4b38` |

ota_0 app 的主要 segment：

| # | load address | length | 文件偏移 |
|---|---|---:|---:|
| 0 | `0x42190020` | `0xbc718` | `0x910020` |
| 1 | `0x40800000` | `0x38d8` | `0x9cc740` |
| 2 | `0x42000020` | `0x18953c` | `0x9d0020` |
| 3 | `0x408038d8` | `0x12ca0` | `0xb59564` |
| 4 | `0x40816580` | `0x5e28` | `0xb6c20c` |

---

## 3. 启动链与双 app 切换

### 3.1 首次启动

`otadata` 全 `0xFF`，ESP-IDF 选择 `factory` 分区。factory app 启动 Brookesia Phone 桌面。

factory app 字符串中的安装项：

```text
Install Settings failed
Install AIChats failed
Install Sensor failed
Install Drawpanel failed
Install Qmiball failed
Install MusicPlayer failed
Install Weather failed
Install Games failed
Install Photos failed
```

对应 9 个 app：`Settings`、`AIChats`、`Sensor`、`DrawingBoard`、`Qmi8658Ball/GravityBall`、`MusicPlayer`、`Weather`、`Games/2048`、`Photos`。

### 3.2 AIChats 是启动器

`AIChats.cpp` 附近的字符串足以确认其用途：

```text
E (%lu) %s: 未找到子工程分区（ota_0）
I (%lu) %s: 已从sub_app分区启动，无需修改
I (%lu) %s: 成功设置sub_app为启动分区，即将重启...
E (%lu) %s: 设置启动分区失败: %s
./components/AIChats/AIChats.cpp
```

行为推断：

1. 查找 `ota_0` 分区。
2. 如果当前已经从 `sub_app`/`ota_0` 启动，直接返回。
3. 否则把 `ota_0` 设置为下一次启动分区，并重启。
4. 重启后运行 `xiaozhi` v2.2.6，由它完成 Wi-Fi、激活、协议、音频和 AI。
5. 失败时打印“设置启动分区失败”。

这是一个自定义的双 app 方案，不是 factory app 内嵌 Xiaozhi，也不是标准 OTA 升级流程。第一次点击 AIChats 会写 `otadata`；之后默认启动 `ota_0`。

### 3.3 OTA 侧的返回路径

`ota_0` 的字符串中也有：

```text
APP_SWITCH
 factory 
I (%lu) %s: Running firmware is factory
I (%lu) %s: Running from factory partition, skipping
```

这暗示 Xiaozhi 侧可能存在切回 factory 的入口/按钮，但本次没有反编译确认。若需要恢复 factory，最直接的方法是擦除 `otadata` 或重新刷 factory BIN；不要仅凭字符串假设 UI 一定有返回按钮。

---

## 4. 音频与 ES8311 引脚

### 4.1 factory BIN 中的 BSP 配置

在 factory segment 0 中，`0x423c1a54` 处是 `i2s_std_gpio_config_t` 对应的字段：

```text
mclk = -1 / GPIO_NUM_NC
bclk = 24
ws   = 25
dout = 26
din  = 27
```

前面的 `0x423c1a24` 是采样率 `22050`。这与公共 BSP 的默认 `BSP_I2S_DUPLEX_MONO_CFG(22050)` 一致，但数据脚方向与公共源码当前修正版相反。

### 4.2 公共 BSP 的不一致

头文件：

```c
#define BSP_I2S_DOUT (GPIO_NUM_26)
#define BSP_I2S_DSIN (GPIO_NUM_27)
```

源码：

```c
.dout = BSP_I2S_DSIN,  /* 27, 注释称 MCU TX -> codec DSDIN */
.din  = BSP_I2S_DOUT,  /* 26, 注释称 MCU RX <- codec ASDOUT */
```

factory BIN：

```text
dout = 26
din  = 27
```

实测：

- V4：RX26，数据全 0，PCNT 0 edge。
- V5：`.din=27`，录音正常。

因此当前共享 BSP 的修正版很可能把 `DOUT/DIN` 与 `DSDIN/ASDOUT` 的命名关系理解反了。对于本板，建议使用：

```c
.dout = 26,  // MCU -> codec
.din  = 27,  // codec -> MCU
```

并保留 `bclk=24`、`ws=25`、`mclk=NC`。

### 4.3 麦克风初始化缺失

公共 BSP：

- 头文件声明 `bsp_audio_codec_microphone_init()`。
- `.c` 中只有 `bsp_audio_codec_speaker_init()` 的实现。
- `bsp_audio_init()` 会创建 TX/RX 两个 I2S channel，并创建 ES8311 设备。

factory app：

- 有 `bsp_audio_init`、`bsp_audio_codec_speaker_init`、`i2s_new_channel`、`es8311_dev` 等字符串。
- 没有明显的 `esp_codec_dev_read` 麦克风读取字符串。
- 但 factory 的 `AIChats` 只是启动器，真正的录音由 `ota_0` 的 Xiaozhi `Es8311AudioCodec` 完成。

结论：引脚配置可以确定；factory app 本身是否执行麦克风采集不是本报告的关键，真正的语音路径在 `ota_0`。自定义 Xiaozhi 需要自己实现/补齐 microphone init，不能只改引脚宏。

---

## 5. Brookesia 多 APP 架构

### 5.1 公共源码可参考的部分

`examples/esp-idf/08_bookesia/main/main.cpp`：

- line 56：`Display ESP-Brookesia phone demo`
- line 61：`LvLock::registerCallbacks`
- line 90：`phone->initAppFromRegistry(inited_apps)`
- line 91：`phone->installAppFromRegistry(inited_apps)`

`components/brookesia_core/systems/base/esp_brookesia_base_app.cpp`：

- line 64：`startRecordResource`
- line 102：`endRecordResource`
- line 342：`processInstall`
- line 371：`processUninstall`
- line 405：`processRun`

`components/brookesia_core/systems/base/esp_brookesia_base_manager.cpp`：

- line 142：`initAppFromRegistry`
- line 164：`installAppFromRegistry`

### 5.2 factory app 的架构证据

factory app 字符串包含：

```text
./components/brookesia_core/systems/base/esp_brookesia_base_app.cpp
./components/brookesia_core/systems/base/esp_brookesia_base_manager.cpp
./components/brookesia_core/systems/phone/esp_brookesia_phone.cpp
./components/brookesia_core/systems/phone/esp_brookesia_phone_manager.cpp
./components/brookesia_core/systems/phone/widgets/recents_screen/...
./components/brookesia_core/gui/lvgl/esp_brookesia_lv_lock.cpp
```

以及各 app 的类名：

```text
esp_brookesia::apps::AIChats
esp_brookesia::apps::Qmi8658Ball
esp_brookesia::apps::MusicPlayer
esp_brookesia::apps::DrawingBoard
esp_brookesia::apps::Games
esp_brookesia::apps::Settings
esp_brookesia::apps::Photos
esp_brookesia::apps::Weather
esp_brookesia::apps::Sensor
```

这说明 factory app 与公共 `08_bookesia` 使用同一套 Brookesia core，但增加了自定义 app 和 `AIChats` 启动器。

### 5.3 是否值得迁移

不建议为了当前录音问题整体迁移 Brookesia。它是完整的手机式多 APP 框架，涉及：

- LVGL 锁和 UI 任务
- app registry/install/uninstall
- 最近任务截图和资源回收
- 多 app 生命周期
- 音频资源在 app 间的占用/释放

对“录音引脚/麦克风初始化”问题，迁移框架不会解决根因，反而增加变量。适合作为架构参考，不适合作为修复手段。

---

## 6. 重力球 95% 卡住

### 6.1 证据

factory app 的 `Qmi8658Ball` 包含：

```text
GravityBall
Calibrating... 0%
Press BOOT button to recalibrate
calibration_task
qmi8658_init(_qmi8658_dev, _i2c_bus, QMI8658_ADDRESS_HIGH)
perform_level_calibration
Starting level calibration...
Calibration unstable (X: %.4f, Y: %.4f)
Calibration complete. Bias X: %.4f, Y: %.4f
Calibrating... %d%%
Calibration complete!
ball_update
Calibration failed! Retrying...
calibration_retry
calibration_recalib
```

公共 `07_Ball_qmi` 可参考 `qmi8658_init`、`perform_level_calibration`、`ball_update` 的实现，但 factory 的 `Qmi8658Ball.cpp` 是自定义版本，不能假定完全相同。

### 6.2 可能原因

按可能性排序：

1. **采样不稳定导致反复校准**：`Calibration unstable` 触发重试，进度停在接近完成的位置。
2. **校准失败重试无上限**：`calibration_retry`/`calibration_recalib` 循环，没有超时提示。
3. **进度未刷新**：校准任务完成了，但 LVGL 进度只更新到 95%，UI 没有收到最终状态。
4. **任务阻塞**：`calibration_task` 等待队列/信号量，或与 LVGL 锁互相等待。
5. **传感器配置问题**：量程/ODR/单位与校准阈值不匹配，导致始终判定不稳定。

### 6.3 需要的验证

- 串口日志：确认最后是 `Calibration unstable`、`Calibration complete` 还是 `Calibration failed! Retrying...`。
- 把设备放在稳定水平面，按 BOOT 重新校准，观察是否仍停在 95%。
- 检查 `calibration_task` 的栈、优先级、是否有超时。
- 对比公共 `07_Ball_qmi` 的校准阈值和 `ball_update` 逻辑。
- 如果 UI 停住但串口继续打印，优先查 LVGL 锁/进度刷新，而不是传感器。

在没有这些证据前，不应把 95% 归因于 QMI8658 硬件故障。

---

## 7. AI 初始化循环

### 7.1 Xiaozhi 初始化链

公共 v2.2.6 源码 `/tmp/factory-reverse/xiaozhi-src/main/application.cc`：

- line 61：`Application::Initialize`
- line 165：`Application::Run`
- line 184：主事件循环
- line 323：`ActivationTask`
- line 340：`CheckAssetsVersion`
- line 398：`CheckNewVersion`

`Initialize` 的关键顺序：

```text
display->SetupUI()
audio_service_.Initialize(codec)
audio_service_.Start()
board.StartNetwork()
```

`ActivationTask`：

```text
CheckAssetsVersion()
CheckNewVersion()
InitializeProtocol()
MAIN_EVENT_ACTIVATION_DONE
```

### 7.2 循环候选

1. **没有 Wi-Fi SSID**
   - `WifiBoard::TryWifiConnect()` 检测 `SsidManager`。
   - 没有 SSID 时进入 `StartWifiConfigMode()`。
   - 屏幕应显示配网提示；这不是死循环，但会一直等配网。

2. **Wi-Fi 连接失败**
   - 60 秒超时后进入 config mode。
   - 如果反复重连，会表现为循环。

3. **OTA 检查失败**
   - `CheckNewVersion()` 最多重试 10 次。
   - `retry_delay` 从 10 秒开始翻倍，可能持续很久。
   - 串口会打印 `Check new version failed, retry in ...`。

4. **需要激活**
   - `CheckNewVersion()` 检测 `HasActivationCode()`/`HasActivationChallenge()`。
   - 等待用户输入或激活接口返回，最多 10 次 `Activate()` 尝试。

5. **assets 问题**
   - 本镜像的 assets 包有效：24 个文件，`index.json` version 1，`srmodels.bin` 存在。
   - `CheckAssetsVersion()` 在没有 `download_url` 时直接 `Apply()`。
   - 因此本镜像不太可能因 assets 缺失进入循环。

6. **board profile/codec 初始化失败**
   - 公共源码没有本板 board profile。
   - 如果自定义固件的 `GetAudioCodec()` 或网络初始化失败，可能停在 starting。
   - 需要串口日志确认。

### 7.3 建议

先看串口和屏幕状态：

- 停在 Wi-Fi 配网：查 SSID/密码/路由器。
- 停在 `CHECKING_NEW_VERSION`：查 OTA URL 和网络。
- 停在激活页：查激活码/服务器。
- 停在 starting 且没有网络日志：查 board profile、codec、I2C/ES8311 初始化。
- 不要先改重力球或 Brookesia；它们与 AI 初始化链没有直接关系。

---

## 8. Assets 与 Storage

### 8.1 Assets 包

`assets` 分区不是普通 SPIFFS，而是自定义 mmap pack：

- 偏移：`0xc10000`
- 实际长度：`0x1009bc`
- 头部：`stored_files=24`、checksum `0x67`、stored_len `0x1009b0`
- 表项：32 字节名称 + size + offset + reserved
- 数据起始：`0x42c`

文件：

| 文件 | 大小 | 说明 |
|---|---:|---|
| `font_puhui_common_16_4.bin` | `0xd2ed8` | 中文字体 |
| `srmodels.bin` | `0x1ebff` | 唤醒词/语音模型 |
| `index.json` | `0x7dd` | 版本 1、字体、表情、皮肤配置 |
| 21 个 PNG | 约 `0x600-0xd39` | 表情图片 |

`index.json` 关键内容：

```json
{
  "version": 1,
  "srmodels": "srmodels.bin",
  "text_font": "font_puhui_common_16_4.bin",
  "emoji_collection": [...]
}
```

### 8.2 Storage

`storage` 是 SPIFFS，包含：

```text
/music/BGM_2.mp3
```

factory 的 `MusicPlayer` 可能使用该文件；与 AI 初始化无关。

---

## 9. Ghidra 与反汇编

### 9.1 已完成

- 安装 Ghidra 12.1.4 到 `/tmp/factory-reverse/ghidra/ghidra_12.1.4_PUBLIC`
- 安装 Temurin JDK 21 到 `/tmp/factory-reverse/jdk/jdk-21.0.12.1+1`
- 提取 factory segment：
  - `factory_seg0.bin`：base `0x42240020`，len `0x272684`
  - `factory_seg1.bin`：base `0x40800000`，len `0xd96c`
  - `factory_seg2.bin`：base `0x42000020`，len `0x2359e0`
- 用 `riscv32-esp-elf-objdump` 生成：
  - `factory_seg0.dis`
  - `factory_seg1.dis`
  - `factory_seg2.dis`

### 9.2 Ghidra headless 结果

导入命令：

```bash
export JAVA_HOME=/tmp/factory-reverse/jdk/jdk-21.0.12.1+1
export PATH="$JAVA_HOME/bin:$PATH"
/tmp/factory-reverse/ghidra/ghidra_12.1.4_PUBLIC/support/analyzeHeadless \
  /tmp/factory-reverse/ghidra_proj proj \
  -import /tmp/factory-reverse/factory_seg1.bin \
  -loader BinaryLoader \
  -loader-baseAddr 0x40800000 \
  -processor RISCV:LE:32:default \
  -noanalysis \
  -scriptPath /tmp/factory-reverse \
  -postScript PrintEntry.java
```

结果：

- 导入成功，语言识别为 `RISCV:LE:32:default:gcc`。
- 入口 `0x408002b0` 反汇编成功。
- Python 脚本失败，因为 Ghidra 未以 PyGhidra 启动。
- Java 脚本成功，证明 headless + raw binary + RISC-V 可行。

### 9.2.1 第二轮修正：必须同时反汇编两个 code range

第一轮只把 IRAM `0x40800000-0x40822e70` 作为代码，漏掉了 IROM
`0x42000020-0x42235a00`，因此字符串 XREF 全部为 0。第二轮使用
`SetupAnalysis2.java` 同时建立：

```text
entry
code1 0x40800000..0x40822e70
code2 0x42000020..0x42235a00
data  0x42240020
```

`factory_code2.dis` 得到 805365 条指令、9295 个函数；`ota_code2.dis` 得到
567197 条指令、9010 个函数。关键 BSP 函数图和 OTA ES8311 ctor 证据见
[09 · Ghidra 发现](../docs/09_ghidra_findings.md)。

### 9.3 局限

- raw binary 没有符号表、段名、重定位信息。
- Ghidra 需要手动建立地址块/函数/交叉引用。
- 反汇编入口只能看到局部指令，不能直接得到完整 C++ 类结构。
- 字符串交叉引用可以帮助定位 `AIChats`、`Qmi8658Ball`、BSP 配置，但完整反编译成本高。
- `REA` 未验证，不应在报告中把它当作已验证工具。

---

## 10. 最终建议

### 10.1 对当前录音问题

1. 以 factory BIN 的 BSP 配置为准，使用 **RX=27、TX=26**。
2. 保留 `BCLK=24`、`WS=25`、`MCLK=NC`。
3. 不要直接照搬公共 BSP 当前的 `.dout=DSIN(27)/.din=DOUT(26)`。
4. 补上 microphone init，不要只改宏。
5. 用 V5 的实测结果作为回归基线。

### 10.2 对官方 AI

- 不要再试图从 factory app 里找 Xiaozhi 源码；它只是启动器。
- 要研究完整 AI，应分析 `ota_0` 的 Xiaozhi v2.2.6。
- 公开上游没有本板 board profile；需要自己维护板级文件或从 OTA 二进制反向提取常量。

### 10.3 对重力球/AI 循环

- 先拿串口日志，不要仅靠静态字符串定因。
- 重力球优先验证校准稳定性和重试上限。
- AI 循环优先验证 Wi-Fi、OTA endpoint、激活状态，再查 board/audio 初始化。

### 10.4 对逆向投入

- 若目标只是引脚和启动链：现有证据已足够，可以停止。
- 若目标是恢复 factory 自定义 app 的行为：需要继续 Ghidra 定向分析 `AIChats.cpp`、`Qmi8658Ball.cpp`、`MusicPlayer.cpp` 等，但仍不能恢复原始源码。
- 若目标是完整复刻官方 factory：NO-GO，成本高于基于公开 Brookesia/Xiaozhi 重建。

---

## 11. 复现命令与产物

### 11.1 分区/app 解析

```bash
cd /tmp/factory-reverse
python3 parse_parts.py
```

### 11.2 Ghidra

```bash
export JAVA_HOME=/tmp/factory-reverse/jdk/jdk-21.0.12.1+1
export PATH="$JAVA_HOME/bin:$PATH"
/tmp/factory-reverse/ghidra/ghidra_12.1.4_PUBLIC/support/analyzeHeadless \
  /tmp/factory-reverse/ghidra_proj proj \
  -process factory_seg1.bin \
  -noanalysis \
  -scriptPath /tmp/factory-reverse \
  -postScript PrintEntry.java
```

### 11.3 关键产物

- `/tmp/factory-reverse/official.bin`
- `/tmp/factory-reverse/bootloader.bin`
- `/tmp/factory-reverse/partition-table.bin`
- `/tmp/factory-reverse/factory-app.bin`
- `/tmp/factory-reverse/ota-app.bin`
- `/tmp/factory-reverse/assets.bin`
- `/tmp/factory-reverse/storage.bin`
- `/tmp/factory-reverse/nvs.bin`
- `/tmp/factory-reverse/otadata.bin`
- `/tmp/factory-reverse/factory-app.strings.txt`
- `/tmp/factory-reverse/ota-app.strings.txt`
- `/tmp/factory-reverse/factory_seg0.bin`
- `/tmp/factory-reverse/factory_seg1.bin`
- `/tmp/factory-reverse/factory_seg2.bin`
- `/tmp/factory-reverse/factory_seg0.dis`
- `/tmp/factory-reverse/factory_seg1.dis`
- `/tmp/factory-reverse/factory_seg2.dis`
- `/tmp/factory-reverse/PrintEntry.java`
- `/tmp/factory-reverse/ghidra_entry_java.log`

---

## 12. 证据等级说明

| 结论 | 等级 | 依据 |
|---|---|---|
| 官方 BIN 与 release 相同 | 已确认 | SHA256/cmp |
| 首次启动 factory | 已确认 | otadata 全 FF + 分区表 |
| AIChats 是 ota_0 启动器 | 高置信 | factory 中文字符串 + 双 app 结构 |
| factory 无 Xiaozhi 语音栈 | 高置信 | 字符串计数为 0，完整栈在 ota_0 |
| factory BSP RX27/TX26 | 高置信 | 二进制 gpio_cfg + V5 实测 |
| 公共 BSP 修正可能反了 | 中高置信 | 源码与 factory/实测冲突 |
| 重力球 95% 根因 | 未证明 | 只有字符串和公共代码参考 |
| AI 初始化循环根因 | 未证明 | 公共源码 + 镜像状态推断 |
| Ghidra 可导入/反汇编 | 已确认 | headless Java 脚本成功 |
| REA 可用 | 未验证 | 本环境未找到/未测试 |
