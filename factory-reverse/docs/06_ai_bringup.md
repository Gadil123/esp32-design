# 06 · AI 启动与网络：初始化链、失败矩阵和 bring-up 清单

> 证据等级：**公共 Xiaozhi v2.2.6 源码可证 + 本 BIN 字符串/资产可证；具体现场循环原因未证明**。  
> 适用范围：`ota_0` 的 Xiaozhi 应用；factory 的 `AIChats` 只是切换器。

## 1. 启动链

公共源码 `/tmp/factory-reverse/xiaozhi-src/main/application.cc`（分析时副本）：

```text
Application::Initialize()                 line 61
  ├─ display->SetupUI()
  ├─ audio_service_.Initialize(codec)
  ├─ audio_service_.Start()
  ├─ board.StartNetwork()
  └─ display->UpdateStatusBar(true)

Application::Run()                        line 165
  └─ while (true) 事件循环                 line 184

Network connected
  -> HandleNetworkConnectedEvent()
  -> ActivationTask()                     line 323
       ├─ CheckAssetsVersion()            line 340
       ├─ CheckNewVersion()               line 398
       └─ InitializeProtocol()
```

`WifiBoard::TryWifiConnect()`（`main/boards/common/wifi_board.cc`）：

```text
有 SSID -> StartStation()
无 SSID -> StartWifiConfigMode()
连接超时 60s -> StartWifiConfigMode()
```

## 2. 从 factory 到 AI

```text
上电
  -> otadata 空 -> factory
  -> Brookesia 桌面
  -> 点击 AIChats
  -> 设置 ota_0 为启动分区
  -> 重启
  -> ota_0 Xiaozhi
  -> Wi-Fi / 激活 / OTA 检查
  -> 语音会话
```

因此“AI 初始化循环”只可能发生在 **ota_0 Xiaozhi 启动后**，或者设备已经切到 ota_0。factory 桌面的 `AIChats` 本身不做 AI 初始化。

## 3. 失败矩阵

| 现象 | 可能阶段 | 检查 | 处理 |
| --- | --- | --- | --- |
| 屏幕停在配网提示/二维码 | 无 SSID 或连接超时 | NVS 是否有 SSID；串口 `Starting WiFi connection attempt`/`WiFi connecting` | 配置 Wi-Fi；确认 2.4/5 GHz 与密码 |
| 一直显示 `CHECKING_NEW_VERSION` | OTA 检查 | 串口 `Check new version failed`；OTA URL | 查 DNS/网络/`api.tenclass.net` 可达性 |
| 反复重试 OTA | `CheckNewVersion` 重试 | `retry in %d seconds (x/10)` | 最多 10 次；修复网络或 OTA endpoint |
| 停在激活页 | 激活 | `Activation code`/`Activating...` | 查激活码/服务器；确认是否必须激活 |
| 启动后无网络日志 | board/network 初始化 | `board.StartNetwork` 是否返回；Wi-Fi 事件 | 查 board profile、Wi-Fi 驱动、NVS |
| 启动即崩溃/重启 | board/codec/内存 | 串口 panic/backtrace | 查 ES8311/I2C/PSRAM/栈 |
| 有 Wi-Fi 仍无 AI | 协议/服务端 | WebSocket/MQTT 日志；音频通道 | 查服务端地址、协议版本、证书/鉴权 |
| assets 报错 | assets 分区 | `partition_valid`、`index.json`、`srmodels.bin` | 本 BIN assets 有效；检查是否被擦除 |

## 4. 本镜像的 assets 状态

本 BIN：

- `assets` 分区存在
- 24 个文件
- `index.json` version 1
- `srmodels.bin` 存在
- `font_puhui_common_16_4.bin` 存在

`CheckAssetsVersion()` 的行为：

- 如果 `partition_valid()` 为 false，打印 warning 后返回。
- 如果 NVS `assets/download_url` 为空，不下载，直接 `Apply()`。
- `Apply()` 读取 `index.json`、`srmodels.bin`、字体和表情。

因此本镜像上把“AI 初始化循环”归因于 assets 缺失，证据不足。除非设备上的 assets 被擦除、分区表被改，或 `index.json` 无效。

## 5. 为什么公开源码不能直接复现本板

上游 `78/xiaozhi-esp32` v2.2.6 没有：

```text
main/boards/waveshare/esp32-c5-touch-lcd-2.8/
```

只有其他 C5 板型（如 1.69 寸）。本 BIN 的字符串显示它使用了：

```text
main/boards/waveshare/esp32-c5-touch-lcd-2.8/esp32-c5-touch-lcd-2.8.cc
```

因此：

- 协议/音频/UI 组件可以参考上游。
- 本板的 `CustomBoard`、显示初始化、I2C、ES8311、按键/背光配置必须自行维护。
- 不要假设上游 board 配置可以直接替换。

## 6. Bring-up 清单

### 6.1 先证明启动分区

- 串口打印 `esp_ota_get_running_partition()` 的 label。
- 切到 ota_0 后确认 label 是 `ota_0`，不是 `factory`。
- 记录 `otadata` 前后变化；不要同时刷 factory 和 ota_0 后猜当前 slot。

### 6.2 再证明网络

- Wi-Fi 连接成功日志。
- DNS 解析 OTA 域名。
- HTTP 请求有响应；不要只看“已连接 Wi-Fi”。
- 如果使用代理/私有服务器，确认设备能访问，且证书/时间正确。

### 6.3 再证明激活

- 是否需要激活码。
- `Activate()` 的返回码和错误体。
- 服务器时间是否可用（TLS 证书验证依赖时间）。

### 6.4 最后证明音频/协议

- `Es8311AudioCodec` 初始化成功。
- 录音有非零 PCM；播放有声音。
- WebSocket/MQTT 建连、音频通道打开。
- 唤醒词/按键触发路径。

## 7. 可复用设计建议

1. **把初始化状态做成显式状态机**：`starting → wifi_config → connecting → activating → idle`，每个状态有超时和错误。
2. **重试要有上限和用户可见提示**：不要静默 10 次指数退避。
3. **区分“等待用户”与“循环”**：配网/激活是等待，不是死循环；日志要写清楚。
4. **assets 版本校验要可观测**：打印 partition、index version、srmodels 是否加载。
5. **board profile 独立维护**：不要把本板配置散落在应用代码里。
6. **双 app 切换要有回退路径**：见 [双 APP 与启动链](02_dual_app_boot.md)。

## 8. 相关文档

- [固件清单](01_firmware_inventory.md)
- [双 APP 与启动链](02_dual_app_boot.md)
- [音频与 I2S](03_audio_i2s.md)
- [Brookesia 多 APP](04_brookesia_reuse.md)
