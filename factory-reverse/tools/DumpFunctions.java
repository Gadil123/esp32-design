import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;

/**
 * Dump functions, their size/first instructions, and callers/callees.
 * args[0] optional low address, args[1] optional high address.
 */
public class DumpFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        long lo = a.length > 0 ? Long.decode(a[0]) : 0;
        long hi = a.length > 1 ? Long.decode(a[1]) : Long.MAX_VALUE;
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int count = 0;
        while (it.hasNext()) {
            Function f = it.next();
            long v = f.getEntryPoint().getOffset();
            if (v < lo || v >= hi) continue;
            count++;
            println(String.format("FUNC %s %s size=%d", f.getEntryPoint(),
                    f.getName(), f.getBody().getNumAddresses()));
            int n = 0;
            for (Instruction ins : currentProgram.getListing().getInstructions(f.getBody(), true)) {
                println("  I " + ins.getAddress() + " " + ins);
                if (++n >= 8) break;
            }
            for (Function caller : f.getCallingFunctions(monitor)) {
                println("  CALLER " + caller.getEntryPoint() + " " + caller.getName());
            }
        }
        println("DUMP_TOTAL " + count + " / " +
                currentProgram.getFunctionManager().getFunctionCount());
    }
}
