# 02 · 双 APP 与启动链：AIChats 启动器模式

> 证据等级：**高置信推断**（factory BIN 中文日志 + 双 app 布局 + 公共 Xiaozhi 源码）。  
> 未反编译 `AIChats.cpp` 的完整函数体；以下“行为”是由字符串和镜像结构推得，不是逐行源码。

## 1. 现象

官方 FactoryApp 初始启动的是 `factory` 分区：

- `otadata` 两个 entry 全 `0xFF`
- `factory` app 是 Brookesia Phone 桌面
- 桌面中有一个 `AIChats` 应用
- `factory` app 内没有完整 Xiaozhi 语音栈

但用户可以在官方固件里正常使用 AI。原因不是 factory app 内藏了一套语音栈，而是它包含一个**子应用启动器**。

## 2. 直接证据

`factory` app 的字符串中，`AIChats.cpp` 附近有：

```text
E (%lu) %s: 未找到子工程分区（ota_0）
I (%lu) %s: 已从sub_app分区启动，无需修改
I (%lu) %s: 成功设置sub_app为启动分区，即将重启...
E (%lu) %s: 设置启动分区失败: %s
./components/AIChats/AIChats.cpp
```

对应关系：

- “子工程分区（ota_0）”就是分区表里的 `ota_0`
- “sub_app”是日志中的概念名，不是独立分区标签
- “设置启动分区”意味着写 ESP-IDF 的 OTA boot selection（`otadata`）
- “即将重启”意味着下一次启动由 bootloader 选择 `ota_0`

结合两套 app：

```text
factory (Brookesia 桌面)
  └─ AIChats
       ├─ 检查 ota_0
       ├─ 已从 ota_0 启动？ → 直接返回
       ├─ 否则设置 ota_0 为 boot partition
       └─ 重启 → ota_0 (Xiaozhi v2.2.6)
```

## 3. 为什么这样设计

这是一种“**UI shell + 独立语音 app**”的分层：

| 层 | 负责 | 不负责 |
| --- | --- | --- |
| factory / Brookesia | 桌面、图标、设置、相册、传感器、游戏、音乐 | 完整语音协议、唤醒词、云端会话 |
| ota_0 / Xiaozhi | Wi-Fi、激活、Opus、MQTT/WebSocket、ASR/TTS 会话、音频 | Brookesia 桌面/多 APP 管理 |

好处：

- factory 桌面不需要链接 Xiaozhi 的大量组件，减少 UI 工程的依赖和内存压力。
- 语音应用可以独立升级/替换，不动桌面。
- 两个 app 的失败面分开：桌面崩溃不等于语音协议崩溃。

代价：

- 需要管理两个 app slot 和 `otadata`。
- 需要处理“从语音 app 回到桌面”的路径。
- 首次切换会重启；用户看到的是启动过程，不是页面跳转。
- 调试时需要明确当前运行分区，否则日志/行为容易混淆。

## 4. 可复用的启动器模式

如果确实需要双 app，建议把启动器写成一个**幂等、可恢复、可观测**的小模块：

```text
launch_sub_app():
  target = find_partition("ota_0")
  if target is null:
      show_error("sub app partition missing")
      return

  running = get_running_partition()
  if running == target:
      log("already running target")
      return

  if set_boot_partition(target) != OK:
      show_error("set boot partition failed")
      return

  log("rebooting into sub app")
  restart()
```

设计要点：

1. **幂等**：已经在目标分区时不要重复写 `otadata`/重启，否则会形成“点了没反应”或重启循环。
2. **先校验分区存在**：不要只按标签查找后直接使用空指针。
3. **错误可见**：分区缺失、写入失败要显示/记录，不要静默失败。
4. **不要从 UI 任务里直接重启**：先完成日志、屏幕提示、资源释放，再由受控任务重启。
5. **保留回退路径**：至少保留 USB 重新烧录 factory 的方法；如果产品需要双向切换，语音 app 也要有明确的“返回桌面”入口。
6. **状态可观测**：启动日志打印 `running partition`、目标分区、写入结果。
7. **不要把 `otadata` 空白当永久状态**：第一次切换后它会被写入；后续启动不再默认 factory。

## 5. 对 Pocket OS 的建议

Pocket OS 当前路线是 **ESP-IDF + 微雪 BSP + Brookesia/LVGL**，不是以 Xiaozhi 主固件为长期桌面。因此：

- **优先单 app**：如果 Brookesia 内可以以组件形式复用语音链，单 app 更简单，不需要双 slot 切换。
- **双 app 只在隔离收益明确时使用**：例如语音栈依赖冲突、内存无法共存、需要独立升级语音固件。
- **不要为了“官方这样做”而复制双 app**：官方这样做的背景是 factory 桌面和 Xiaozhi 主固件本来就是两个独立工程；Pocket OS 的架构目标不同。
- 如果采用双 app，先做最小 PoC：一个空白 Brookesia app + 一个最小 ota app，验证：
  - 设置启动分区成功
  - 重启后运行目标 app
  - 能回到桌面
  - 断电/异常重启不会卡在错误 slot
  - 两个 app 的 flash/RAM 预算可接受

## 6. 未确认项

- `AIChats.cpp` 具体调用的 API 名称和错误处理路径（字符串只能证明语义）。
- 从 Xiaozhi 返回 factory 的 UI/按键是否完整可用；`ota_0` 中也有 `APP_SWITCH`/`factory` 字符串，但没有反编译确认。
- 切换后 `otadata` 的具体 sequence 和回滚策略。
- 擦除 `otadata` 是否在所有板批次上都能恢复 factory（理论上是，但未实机验证）。

## 7. 相关文档

- [固件清单](01_firmware_inventory.md)
- [AI 启动与网络](06_ai_bringup.md)
- [逆向方法](07_reverse_method.md)
