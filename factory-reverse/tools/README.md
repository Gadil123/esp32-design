# Tools

Ghidra 12.1.4 + JDK 21. Python headless scripts are **not** run through
PyGhidra; the `.py` files are standalone text scanners for the exported
disassembly.

## Ghidra scripts

| Script | Purpose |
| --- | --- |
| `SetupAnalysis.java` | Single code range setup (legacy, first pass) |
| `SetupAnalysis2.java` | Split raw combined image into `entry` + code1/code2 + data; used for factory/OTA |
| `LinearDisasm.java` | Linear sweep one address range and create functions |
| `BulkDisasm.java` | Disassemble multiple ranges in one pass |
| `RecursiveDisasm.java` | Follow calls from entry/seed functions |
| `DecompileAt.java` | Decompile functions containing supplied addresses; print callers |
| `DumpBytes.java` | Dump 80 bytes at each supplied address |
| `DumpDisasm.java` | Dump instructions for an address range |
| `DumpFunctions.java` | Dump function list with entry/size |
| `ListFuncs.java` | List all functions |
| `FindRefs.java` | Ghidra reference iterator; known to return 0 for many strings/data |
| `StringRefs.java` | Attempt to define/label string references |
| `PrintEntry.java` | Minimal factory entry disassembly |

Typical factory/OTA setup:

```bash
export JAVA_HOME=/tmp/factory-reverse/jdk/jdk-21.0.12.1+1
GHIDRA=/tmp/factory-reverse/ghidra/ghidra_12.1.4_PUBLIC/support/analyzeHeadless

$GHIDRA /tmp/factory-reverse/ghidra_work2 factory \
  -process factory_combined.bin -noanalysis \
  -scriptPath "$PWD" \
  -postScript SetupAnalysis2.java \
    0x408002b0 0x40800000 0x40822e70 0x42000020 0x42235a00 0x42240020
```

Then run `LinearDisasm.java` on `0x42000020-0x42235a00`, and decompile
specific addresses with `DecompileAt.java`.

## Text scanners

`scan_refs2.py` and `scan_calls.py` work on the exported `.dis` files
(`factory_code2.dis`, `ota_code2.dis`):

- `scan_refs2.py`: finds `lui`/`addi` pairs that form absolute addresses,
  because Ghidra's reference database misses many raw-address string loads.
- `scan_calls.py`: finds `auipc` + `jalr` call targets.

These are evidence aids, not source recovery. Function names in the docs are
semantic labels; addresses and constant bytes are the evidence.

## Limits

- Ghidra `FindRefs.java` still returns 0 for undefined rodata/strings.
- Linear sweep creates some false functions at data/alignment boundaries.
- Factory codec config field order is not typed; do not infer pin direction
  from four consecutive GPIO bytes alone.
- `DumpBytes.java` prints 80 bytes per argument; use Python/`xxd` for larger
  ranges.
