# 04 · Brookesia 多 APP：可复用的结构与取舍

> 证据等级：**官方公开源码可证 + factory BIN 字符串可证**；未获得 factory 自定义 app 源码。  
> 目标不是复刻官方桌面，而是提取对 Pocket OS 有用的结构和边界。

## 1. 公开基线

微雪公开示例 `examples/esp-idf/08_bookesia`：

- `main/main.cpp:56`：`Display ESP-Brookesia phone demo`
- `main/main.cpp:61`：`LvLock::registerCallbacks`
- `main/main.cpp:90`：`phone->initAppFromRegistry(inited_apps)`
- `main/main.cpp:91`：`phone->installAppFromRegistry(inited_apps)`

Brookesia core：

- `systems/base/esp_brookesia_base_app.cpp`
  - `startRecordResource`（line 64）
  - `endRecordResource`（line 102）
  - `processInstall`（line 342）
  - `processUninstall`（line 371）
  - `processRun`（line 405）
- `systems/base/esp_brookesia_base_manager.cpp`
  - `initAppFromRegistry`（line 142）
  - `installAppFromRegistry`（line 164）

factory BIN 也包含同一套 core 的字符串：

```text
./components/brookesia_core/systems/base/esp_brookesia_base_app.cpp
./components/brookesia_core/systems/base/esp_brookesia_base_manager.cpp
./components/brookesia_core/systems/phone/esp_brookesia_phone.cpp
./components/brookesia_core/systems/phone/esp_brookesia_phone_manager.cpp
./components/brookesia_core/systems/phone/widgets/recents_screen/...
./components/brookesia_core/gui/lvgl/esp_brookesia_lv_lock.cpp
```

说明 factory 桌面与公开 `08_bookesia` 同源，但 factory 增加了自定义 app 和 `AIChats` 启动器。

## 2. factory 的 APP 清单

| APP | 类型 | 可复用点 |
| --- | --- | --- |
| `Settings` | 系统设置 | Wi-Fi/亮度/音量等系统页结构 |
| `AIChats` | 启动器 | 双 app 切换模式，不是 AI 本体 |
| `Sensor` | 传感器 | QMI8658/PCF85063/SHTC3 展示 |
| `DrawingBoard` | 画板 | 触摸绘图、LVGL 画布 |
| `Qmi8658Ball` | 体感球 | 校准任务/进度 UI |
| `MusicPlayer` | 音乐 | SPIFFS/SD 音频播放、播放状态 |
| `Weather` | 天气 | HTTP/JSON/缓存 |
| `Games` | 2048 | 轻量离线游戏 |
| `Photos` | 相册 | 图片浏览/缩略图/缓存 |

这些 app 的**类名和日志**在 factory BIN 中可见，但源码不在公开仓库。可以参考交互和模块划分，不能把类名当作已有可编译代码。

## 3. 值得复用的设计

### 3.1 App registry

不要在 `main.cpp` 里硬编码创建所有页面。用 registry 描述：

```text
app name
icon / display name
init
run
install
uninstall
resource requirements
```

好处：

- 桌面只依赖抽象 app，不依赖每个业务模块。
- 新 app 可以独立增删。
- app 的 install/uninstall 可以统一处理内存、LVGL 对象和文件句柄。

### 3.2 App 生命周期

可复用的阶段：

```text
init      -> 创建对象/注册资源，不启动重任务
install   -> 创建 UI、绑定事件
run       -> 激活页面、恢复状态、启动必要的定时器
close     -> 停止任务、释放 LVGL/缓冲区
uninstall -> 彻底释放
```

关键边界：

- `init` 不要做网络/音频等阻塞操作。
- `run` 不要重复创建 UI。
- `close` 必须停止 app 自己的任务，否则切换后后台任务会抢 CPU/锁。
- `uninstall` 要可重复调用，避免二次释放。

### 3.3 LVGL 锁

factory 和公开示例都使用 `LvLock`。复用原则：

- 所有非 LVGL 任务改 UI 必须拿锁。
- 不要在持锁时做网络/文件/音频阻塞操作。
- app 的关闭流程要避免“等锁 + 持锁回调”互相等待。
- 进度更新可以合并/节流，避免高频抢锁。

### 3.4 资源记录与最近任务

factory 有 recents screen/snapshot、record resource、clean resource 字符串。可复用的思路：

- 每个 app 记录自己占用的 LVGL 对象/图片/文件/任务。
- 切后台时保存必要状态，释放可重建资源。
- 最近任务截图只作 UI，不作为业务状态唯一来源。
- 自动清理要有上限和失败日志，不能静默丢用户数据。

### 3.5 统一服务层

多 APP 下不要让每个 app 各自初始化 Wi-Fi/音频/传感器。建议：

```text
Board services
├─ display / touch / LVGL
├─ audio (speaker + mic)
├─ Wi-Fi / time / HTTP
├─ storage (SPIFFS/SD)
├─ sensors
└─ power / battery
```

APP 通过服务层访问硬件；服务层负责互斥、引用计数和错误恢复。否则多个 app 同时打开 ES8311/I2S 会发生采样率/通道冲突。

## 4. 不建议的做法

1. **为了录音问题整体迁移 Brookesia**  
   录音引脚/麦克风初始化与桌面框架无关。迁移只会增加变量。

2. **直接把 factory 的 9 个 app 全部复刻**  
   源码不可得，且其中很多是演示级实现；Pocket OS 只需要 Pocket Chat、相册、日语等目标 app。

3. **假设公开 `08_bookesia` 就是完整 FactoryApp**  
   公开示例只有 Phone + DrawingBoard 等少量 app，不含 factory 的 AIChats/相册/天气/游戏完整实现。

4. **假设 Brookesia 0.8 可直接替换 0.6**  
   动态 `.bpk`、HAL、内存和 C5 适配需要单独 PoC；本项目仍以公开 0.6 示例为可复现基线。

## 5. 对 Pocket OS 的落地建议

最稳妥的路线：

1. 以公开 `08_bookesia` 为基线，先跑通 Phone/触摸/屏幕。
2. 抽出一个最小的 `PocketChat` app，只做按键录音/状态显示，不先接完整 ASR。
3. 把音频服务抽成共享层，解决 speaker/mic 的引脚、采样率和互斥。
4. 再增加相册/日语等 app，验证 registry、后台任务和资源释放。
5. 最后再评估是否需要 Brookesia 0.8 的动态 app；不要在音频未稳定前迁移。

## 6. 相关文档

- [双 APP 与启动链](02_dual_app_boot.md)
- [音频与 I2S](03_audio_i2s.md)
- [AI 启动与网络](06_ai_bringup.md)
- 仓库软件路线：[08 · Pocket OS 软件架构](../../docs/08_software_architecture_and_app_roadmap.md)
