# 14 · Bootloader 与分区表内存边界

> 证据等级：**已确认（BIN 逐字节解析）**。  
> 对象：官方 FactoryApp V1.1，SHA256
> `92d0f25d7b8c43900c8882e2ca9cee1ca7c8a9338504bd392567f3d1e8cdf174`。  
> 本文修正早期笔记中的两个偏移错误：bootloader 不是 32 KB，分区表在
> `0x8000`，`nvs` 才在 `0x9000`。

## 1. 结论先行

| 项目 | 正确值 | 早期错误 |
| --- | --- | --- |
| Bootloader 起始 | `0x2000` | 一致 |
| Bootloader body 结束 | `0x7a68` | 曾把整个 `0x8000` 当镜像 |
| Bootloader 校验/尾部 | `0x7a70..0x7a90` | 未记录 |
| Bootloader 镜像结束（exclusive） | `0x7a91` | 曾写 `size=0x8000` |
| Bootloader 可用窗口 | `0x2000..0x8000` | 窗口不是镜像长度 |
| 分区表起始 | `0x8000` | 曾被误写成 `0x9000` |
| 分区表结束标记 | `0x80e0` | 未记录 |
| 分区表 MD5 | `0x80f0..0x80ff` | 未记录 |
| `nvs` 起始 | `0x9000` | 与分区表混淆 |

`0x8000` 处是分区表入口 `nvs`，不是 bootloader 的尾部；bootloader 的实际
镜像在 `0x7a91` 前已经结束，`0x7a91..0x8000` 是保留/填充区。

## 2. Bootloader 镜像

### 2.1 头部

```text
offset       0x2000
magic        0xe9
segments     3
spi mode     2 (DIO)
size/freq    0x4f  (size code 4 = 16MB, freq code 15 = 80MHz)
entry        0x4084bbaa
chip id      23 (ESP32-C5)
```

### 2.2 Segment

| # | load address | length | 文件数据 | 数据结束 |
| ---: | ---: | ---: | ---: | ---: |
| 0 | `0x408556b0` | `0x1810` | `0x2020` | `0x3830` |
| 1 | `0x4084bba0` | `0x0fc4` | `0x3838` | `0x47fc` |
| 2 | `0x4084e5a0` | `0x3264` | `0x4804` | `0x7a68` |

三个 segment 的 load address 不是按文件顺序递增，这是正常的链接布局；
判断镜像边界要看文件偏移和长度，不能按虚拟地址排序。

### 2.3 尾部

```text
body end        0x7a68
padding         to 0x7a70
checksum byte   0x7a70 = 0xf1
SHA256          0x7a71..0x7a90
image end       0x7a91 (exclusive)
```

因此：

```text
bootloader file span = 0x7a91 - 0x2000 = 0x5a91 = 23185 bytes
```

`0x2000..0x8000` 是 bootloader 的分区窗口（24 KB），不是镜像实际大小。
把 `size` 写成 `0x8000` 会把窗口、填充和后面的分区表混在一起。

## 3. 分区表

分区表位于 `0x8000`，标准 32 字节 entry：

| # | label | type | subtype | offset | size | end |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | `nvs` | `0x01` data | `0x02` nvs | `0x9000` | `0x4000` | `0xd000` |
| 1 | `otadata` | `0x01` data | `0x00` ota | `0xd000` | `0x2000` | `0xf000` |
| 2 | `phy_init` | `0x01` data | `0x01` phy | `0xf000` | `0x1000` | `0x10000` |
| 3 | `factory` | `0x00` app | `0x00` factory | `0x20000` | `0x4e2000` | `0x502000` |
| 4 | `storage` | `0x01` data | `0x82` spiffs | `0x502000` | `0x400000` | `0x902000` |
| 5 | `ota_0` | `0x00` app | `0x10` ota_0 | `0x910000` | `0x300000` | `0xc10000` |
| 6 | `assets` | `0x01` data | `0x82` spiffs | `0xc10000` | `0x300000` | `0xf10000` |

尾数据：

```text
end entry     0x80e0..0x80ff  eb eb ff ...
MD5           0x80f0..0x80ff
MD5 value     cf713ae992b641a7e5a868f1f6dc81b4
MD5 covers    0x8000..0x80df (7 entries, 224 bytes)
```

`0x8100..0x8fff` 不在分区表定义内；第一个 data 分区 `nvs` 从 `0x9000`
开始。看到 `0x9000` 全 `0xFF` 是空 NVS，不是分区表缺失。

## 4. 为什么早期会写成 0x9000

常见混淆链：

```text
0x8000  分区表（7 × 32 = 224 字节 + MD5）
0x9000  nvs 起点
```

如果只按“nvs 前面有 0x1000 保留区”去推，容易把分区表挪到 `0x9000`。
但分区表 entry 0 的 `offset=0x9000` 是 **nvs 的数据偏移**，不是表自身
的偏移。表自身的地址由 bootloader 的 `CONFIG_PARTITION_TABLE_OFFSET`
决定，本镜像为 `0x8000`。

另一个混淆是 bootloader 的 `0x2000 + 0x6000 = 0x8000`：`0x6000` 是窗口
上限，不是 image header 里的 size。header 没有“镜像总长度”字段，必须
按 segment 累加后加 padding/checksum/SHA 才能得到真实结束地址。

## 5. 对文档与数据的影响

已修正：

- [固件清单](01_firmware_inventory.md)：bootloader 改为真实 body/尾部边界，
  分区表明确写在 `0x8000`。
- [逆向方法](07_reverse_method.md)：bootloader 行补 body end，分区表节补
  7 个 entry 和 MD5 范围。
- [完整静态分析](../reference/full-static-analysis.md)：2.1/2.2 同步。
- [`data/firmware-layout.json`](../data/firmware-layout.json)：删除
  `bootloader.size=0x8000`，增加 `image_size`、`body_end`、`image_end`、
  `window` 和 `partition_table`。

board draft 的分区 CSV 不受影响：它按 16 MB 布局，`nvs` 仍在 `0x9000`，
`factory` 仍在 `0x20000`。需要改的是叙述和机器数据中的 bootloader 长度。

## 6. 复现片段

```python
from pathlib import Path
import struct

b = Path("official.bin").read_bytes()
off = 0x2000
magic, segs, mode, size_freq, entry = struct.unpack_from("<BBBBI", b, off)
p = off + 24
for i in range(segs):
    addr, length = struct.unpack_from("<II", b, p)
    p += 8
    print(i, hex(addr), hex(length), hex(p), hex(p + length))
    p += length
print("body_end", hex(p))
print("checksum", hex((p + 15) & ~15), b[(p + 15) & ~15])
print("image_end", hex(((p + 15) & ~15) + 33))
```

## 7. 相关文档

- [固件清单与镜像结构](01_firmware_inventory.md)
- [Flash 容量审计](11_flash_capacity_audit.md)
- [双 APP 与启动链](02_dual_app_boot.md)
- [证据账本](../reference/evidence-ledger.md)
