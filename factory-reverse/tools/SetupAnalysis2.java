import ghidra.app.plugin.core.analysis.AutoAnalysisManager;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

/**
 * Split a combined ESP32 app image into two executable code ranges and the
 * rodata range after them.
 *
 * args: entry code1Start code1End code2Start code2End dataStart
 */
public class SetupAnalysis2 extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        Address entry = toAddr(Long.decode(a[0]));
        long c1s = Long.decode(a[1]);
        long c1e = Long.decode(a[2]);
        long c2s = Long.decode(a[3]);
        long c2e = Long.decode(a[4]);
        long ds = Long.decode(a[5]);

        Memory mem = currentProgram.getMemory();
        MemoryBlock root = mem.getBlock(toAddr(c1s));
        if (root == null) throw new RuntimeException("no block at " + a[1]);
        for (long b : new long[] { c1e, c2s, c2e, ds }) {
            MemoryBlock at = mem.getBlock(toAddr(b));
            if (at != null && at.getStart().getOffset() < b && at.getEnd().getOffset() >= b) {
                mem.split(at, toAddr(b));
            }
        }
        for (MemoryBlock block : mem.getBlocks()) {
            long s = block.getStart().getOffset();
            boolean code = (s >= c1s && s < c1e) || (s >= c2s && s < c2e);
            block.setName(code ? "CODE" : "DATA");
            block.setExecute(code);
            block.setRead(true);
            println("BLOCK " + block.getName() + " " + block.getStart() + "-" + block.getEnd()
                    + " execute=" + block.isExecute());
        }
        if (getFunctionAt(entry) == null) {
            disassemble(entry);
            createFunction(entry, "entry");
        }
        currentProgram.getSymbolTable().addExternalEntryPoint(entry);
        // Do not run full auto-analysis here; linear sweep is done separately.
    }
}
