# 07 · 逆向方法：从官方 BIN 到可复核证据

> 目的：让后续分析可以复现，而不是只留下结论。  
> 边界：不修改/刷写设备；不把反汇编片段当作完整源码；不重新分发官方固件。

## 1. 获取与校验

从官方 release 获取 FactoryApp BIN：

<https://github.com/waveshareteam/ESP32-C5-Touch-LCD-2.8/releases/tag/v1.1.0>

本分析使用的文件：

```text
ESP32-C5-Touch-LCD-2.8-FactoryAppV1.1.bin
size   13699516
sha256 92d0f25d7b8c43900c8882e2ca9cee1ca7c8a9338504bd392567f3d1e8cdf174
```

建议：

```bash
sha256sum ESP32-C5-Touch-LCD-2.8-FactoryAppV1.1.bin
```

BIN 不纳入 Git；本子项目只保存结构、地址、字符串和结论。

## 2. 基础解析

### 2.1 Bootloader / app header

ESP-IDF image header 字段：

```text
byte 0       magic 0xe9
byte 1       segment count
byte 2       SPI mode
byte 3       low nibble = flash frequency code
             high nibble = flash size code
bytes 4..7   entry address
bytes 12..13 chip ID
```

本 BIN：

```text
bootloader @ 0x2000: entry 0x4084bbaa, chip 23, 16MB, DIO 80MHz
factory    @ 0x20000: entry 0x408002b0, 5 segments
ota_0      @ 0x910000: entry 0x408003a6, 5 segments
```

### 2.2 分区表

偏移 `0x8000`，每条 32 字节：

```text
magic 0xAA50 (bytes aa 50)
type, subtype
offset, size
label[16]
flags
```

注意：分区表尾部可能是 MD5/尾数据，不一定全 `0xFF`。不要因为看到 `ebeb...` 就判定表损坏。

### 2.3 App descriptor

`esp_app_desc_t` 位于 **第一个 segment 的数据开头**，即 image offset `0x20`：

```text
0x00  magic 0xabcd5432
0x04  secure_version
0x08  reserved[2]
0x10  version[32]
0x30  project_name[32]
0x50  time[16]
0x60  date[16]
0x70  idf_ver[32]
0x90  app_elf_sha256[32]
```

常见错误是把 `version` 当成 project、把 project 当成 time；写 parser 时按上面的偏移校验。

## 3. 提取 segment

以 factory app 为例：

```text
image @ 0x20000
header 24 bytes
每个 segment: 8 字节 (load address, length) + data
```

本分析提取：

```text
factory_seg0.bin  base 0x42240020  len 0x272684
factory_seg1.bin  base 0x40800000  len 0xd96c
factory_seg2.bin  base 0x42000020  len 0x2359e0
```

映射公式：

```text
vaddr = load_address + (file_offset - segment_data_file_offset)
```

例：

```text
factory BSP 配置 file offset 0x1a1a54
segment 0 data starts at 0x20020, load 0x42240020
vaddr = 0x42240020 + (0x1a1a54 - 0x20020) = 0x423c1a54
```

## 4. Ghidra

### 4.1 环境

本分析使用：

```text
Ghidra 12.1.4
Temurin JDK 21
language RISCV:LE:32:default
loader   BinaryLoader
```

### 4.2 导入 raw segment

```bash
export JAVA_HOME=/path/to/jdk-21
export PATH="$JAVA_HOME/bin:$PATH"

$GHIDRA/support/analyzeHeadless \
  /tmp/factory-reverse/ghidra_proj proj \
  -import /tmp/factory-reverse/factory_seg1.bin \
  -loader BinaryLoader \
  -loader-baseAddr 0x40800000 \
  -processor RISCV:LE:32:default \
  -noanalysis \
  -scriptPath /path/to/tools \
  -postScript PrintEntry.java
```

### 4.3 Python 脚本限制

Ghidra 12 的 headless 默认不是 PyGhidra。直接跑 `.py` 可能报：

```text
Ghidra was not started with PyGhidra. Python is not available
```

可改用 Java GhidraScript（本子项目提供 [PrintEntry.java](../tools/PrintEntry.java)），或显式启用 PyGhidra 环境。不要因为脚本失败就认为导入失败；先看 import 日志。

### 4.4 反汇编入口

本分析成功输出：

```text
408002b0  c.addi sp,-0x20
408002b2  c.li a5,0x1
408002b4  c.swsp ra,0x1c(sp)
408002ba  jal ra,0x4081a608
```

说明 raw binary + RISC-V + headless 路径可用。

## 5. objdump 替代路径

如果不需要 Ghidra 的交互/伪代码，可以直接用 RISC-V objdump：

```bash
riscv32-esp-elf-objdump -D -b binary -m riscv:rv32 \
  --adjust-vma=0x40800000 factory_seg1.bin > factory_seg1.dis
```

注意：

- `--adjust-vma` 必须与 segment load address 一致。
- rodata 也可能被 objdump 当成指令；不要把 `.dis` 中所有行都当代码。
- 没有符号/重定位，函数边界和字符串引用需要人工判断。

## 6. 证据标准

本子项目按以下等级记录：

| 等级 | 含义 | 例 |
| --- | --- | --- |
| 已确认 | 可直接从 BIN/官方源码验证 | 分区表、app descriptor、BSP 字段 |
| 高置信推断 | 多源交叉，但没有逐行反编译 | AIChats 启动器行为 |
| 待实机验证 | 需要板卡/串口/仪器 | 引脚、录音、95%、AI 循环 |
| 设计建议 | 本项目建议，不是官方保证 | 单 app vs 双 app、校准状态机 |

禁止把“字符串存在”直接写成“函数已执行”；禁止把“反汇编到某地址”写成“恢复源码”。

## 7. 工具限制

- raw binary 没有符号表、段名、重定位、C++ RTTI 完整信息。
- Ghidra 自动分析可能把数据当代码；需要手动建立 address block/function。
- C++ 虚表/模板/异常表会增加恢复难度。
- `REA` 在本环境未验证；不要把它写成已验证工具。
- 反编译结果只能作为设计参考，不能直接生成可编译源码。

## 8. 相关文档

- [固件清单](01_firmware_inventory.md)
- [双 APP 与启动链](02_dual_app_boot.md)
- [音频与 I2S](03_audio_i2s.md)
- [完整静态分析](../reference/full-static-analysis.md)
