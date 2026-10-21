import ghidra.app.plugin.core.analysis.AutoAnalysisManager;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

/**
 * Split a combined raw image into executable code and non-executable data
 * blocks, mark the entry point, and run analysis.
 *
 * args:
 *   entry codeStart codeEnd data1Start data1End data2Start
 */
public class SetupAnalysis extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        Address entry = toAddr(Long.decode(a[0]));
        long codeStart = Long.decode(a[1]);
        long codeEnd = Long.decode(a[2]);
        long data1Start = Long.decode(a[3]);
        long data1End = Long.decode(a[4]);
        long data2Start = Long.decode(a[5]);

        Memory mem = currentProgram.getMemory();
        MemoryBlock root = mem.getBlock(toAddr(codeStart));
        if (root == null) {
            throw new RuntimeException("no block at " + a[1]);
        }
        // Split at every transition. Each split only applies if the address is
        // inside the current block.
        for (long b : new long[] { codeEnd, data1Start, data1End, data2Start }) {
            MemoryBlock at = mem.getBlock(toAddr(b));
            if (at != null && at.getStart().getOffset() < b && at.getEnd().getOffset() >= b) {
                mem.split(at, toAddr(b));
            }
        }

        for (MemoryBlock block : mem.getBlocks()) {
            long s = block.getStart().getOffset();
            boolean code = s >= codeStart && s < codeEnd;
            block.setName(code ? "CODE" : (s >= data1Start ? "DATA" : "GAP"));
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
        println("ANALYZE entry=" + entry);
        AutoAnalysisManager mgr = AutoAnalysisManager.getAnalysisManager(currentProgram);
        mgr.startAnalysis(monitor, false);
        println("ANALYSIS_DONE functions=" + currentProgram.getFunctionManager().getFunctionCount()
                + " instructions=" + currentProgram.getListing().getNumInstructions());
    }
}
