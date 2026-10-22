import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.io.PrintWriter;

public class DumpDisasm extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        long lo = Long.decode(a[0]);
        long hi = Long.decode(a[1]);
        String path = a[2];
        PrintWriter w = new PrintWriter(path);
        InstructionIterator it = currentProgram.getListing().getInstructions(toAddr(lo), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            if (ins.getAddress().getOffset() >= hi) break;
            w.println(ins.getAddress() + "\t" + ins);
        }
        w.close();
        println("DUMP_DISASM " + path);
    }
}
