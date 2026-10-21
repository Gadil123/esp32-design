# Tools

## PrintEntry.java

Ghidra JavaScript used to disassemble the factory app entry at `0x408002b0` after importing `factory_seg1.bin` at base `0x40800000`.

Tested with Ghidra 12.1.4 + JDK 21. Python headless scripts require PyGhidra and are not used here.

Example:

```bash
export JAVA_HOME=/path/to/jdk-21
export PATH="$JAVA_HOME/bin:$PATH"

$GHIDRA/support/analyzeHeadless /tmp/factory-reverse/ghidra_proj proj \
  -import /tmp/factory-reverse/factory_seg1.bin \
  -loader BinaryLoader \
  -loader-baseAddr 0x40800000 \
  -processor RISCV:LE:32:default \
  -noanalysis \
  -scriptPath "$PWD" \
  -postScript PrintEntry.java
```

The script is an analysis aid, not a source-recovery tool.
