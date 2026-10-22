# 05 · 重力球校准：95% 卡住的排查与可复用设计

> 证据等级：**现象/字符串可证；根因未证明**。  
> factory `Qmi8658Ball` 是自定义 app，源码不在公开仓库；本文只给出可复用设计和排查顺序。

## 1. 现象

factory 的 `GravityBall`（`Qmi8658Ball`）在启动校准阶段可能停在约 **95%**，不进入可玩的球体界面。

这是现场观察，必须先通过串口日志确认最后的校准状态；仅凭 UI 百分比不能判断任务是否仍在运行。

## 2. factory BIN 中的校准流程

factory app 字符串：

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

可以还原出大致状态：

```text
init QMI8658
  -> calibration_task
       -> perform_level_calibration
            -> 采样
            -> 稳定？ 是 -> 保存 bias -> complete
            -> 否 -> "Calibration unstable" -> retry/recalib
       -> 更新进度 0..100%
  -> ball_update
```

`Press BOOT button to recalibrate` 说明 BOOT 是重新校准入口；`calibration_retry` / `calibration_recalib` 说明存在重试路径。

## 3. 95% 的候选原因

按排查优先级：

### 3.1 采样不稳定，校准一直重试

可能表现：

```text
Calibration unstable (X: ..., Y: ...)
Calibration failed! Retrying...
```

原因可能是：

- 设备没有放稳，桌面振动/手扶。
- 加速度计量程/ODR/单位与阈值不匹配。
- 校准窗口内样本数不足，或姿态变化超过阈值。
- QMI8658 初始化成功但数据未更新（I2C 读失败/时序问题）。

### 3.2 重试无上限

`calibration_retry` 可能没有最大次数/超时，导致永远停在接近完成的状态。UI 的 95% 可能只是最后一次进度更新。

### 3.3 进度未刷新

校准任务已完成，但：

- 进度只在采样循环里更新，完成分支没有发最终 UI 事件。
- LVGL 锁被占用，UI 任务没有处理最后一条进度。
- app 已切后台/关闭，进度对象失效。

### 3.4 任务阻塞/优先级

- `calibration_task` 等待队列/信号量，但发送方没有运行。
- 校准任务与 LVGL/音频任务优先级不匹配，UI 不再刷新。
- 看门狗未触发，但任务实际卡住。

### 3.5 传感器配置/硬件

- QMI8658 地址/总线错误，读到恒定值。
- 量程/ODR 配置与校准算法假设不一致。
- 传感器焊接/供电问题。

## 4. 建议的校准状态机

无论使用 factory 逻辑还是自研，建议明确状态和退出条件：

```text
IDLE
  -> COLLECTING (N 个样本)
  -> CHECK_STABILITY
       -> stable: COMPLETE
       -> unstable && retry < MAX: RETRY
       -> unstable && retry >= MAX: FAILED
  -> COMPLETE / FAILED
```

要求：

| 项 | 建议 |
| --- | --- |
| 超时 | 每次校准有总超时，例如 10-15 秒 |
| 重试 | 明确最大次数，失败后给用户选项 |
| 进度 | 进度由状态机统一发出，完成/失败都发最终事件 |
| 样本 | 记录样本数、均值、方差/最大偏差 |
| 日志 | 每次重试打印原因和阈值 |
| UI | 显示“请放稳”“校准失败，按 BOOT 重试”，不要只显示百分比 |
| 持久化 | 成功后保存 bias；启动时可先加载旧 bias，再后台校准 |
| 失败降级 | 校准失败时允许进入“未校准”模式，或明确阻止进入球体 |

## 5. 串口排查清单

按顺序执行：

1. 确认最后一条日志：
   - `Calibration unstable`
   - `Calibration complete. Bias ...`
   - `Calibration failed! Retrying...`
   - 没有任何日志（任务卡住/未启动）
2. 把设备放在稳定水平面，按 BOOT 重新校准；不要手扶。
3. 打印原始加速度 X/Y/Z 和样本数；检查是否恒定/跳变。
4. 检查 QMI8658 初始化返回值、I2C 地址、量程、ODR、单位。
5. 检查 `calibration_task` 的栈余量、优先级、是否被删除/阻塞。
6. 检查 UI 进度更新是否在 LVGL 锁内，完成分支是否发送最终状态。
7. 对比公开 `07_Ball_qmi` 的校准阈值和 `ball_update` 逻辑；不要假定 factory 自定义版完全相同。

## 6. 可复用结论

- 校准是一个**有超时、有上限、有最终状态**的状态机，不是无限循环。
- 进度 UI 和校准任务要解耦；任务完成/失败都必须发事件。
- 失败要可恢复：BOOT 重试、加载旧 bias、或进入明确的未校准模式。
- 不要用“95%”作为根因；它只是最后一个 UI 值。

## 7. 相关文档

- [Brookesia 多 APP](04_brookesia_reuse.md)
- [完整静态分析](../reference/full-static-analysis.md)
