import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

/**
 * Decompile functions containing the supplied addresses.
 */
public class DecompileAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        DecompInterface ifc = new DecompInterface();
        ifc.toggleCCode(true);
        ifc.toggleSyntaxTree(true);
        if (!ifc.openProgram(currentProgram)) {
            println("DECOMP_OPEN_FAILED");
            return;
        }
        for (String s : getScriptArgs()) {
            Address a = toAddr(Long.decode(s));
            Function f = getFunctionContaining(a);
            if (f == null) {
                if (getInstructionAt(a) == null) disassemble(a);
                createFunction(a, null);
                f = getFunctionAt(a);
            }
            if (f == null) {
                println("DECOMP_NO_FUNCTION " + s);
                continue;
            }
            println("===== DECOMP " + f.getEntryPoint() + " " + f.getName()
                    + " size=" + f.getBody().getNumAddresses() + " requested=" + s);
            for (Function caller : f.getCallingFunctions(monitor)) {
                println("CALLER " + caller.getEntryPoint() + " " + caller.getName());
            }
            DecompileResults r = ifc.decompileFunction(f, 120, monitor);
            if (r == null || !r.decompileCompleted()) {
                println("DECOMP_FAILED " + (r == null ? "null" : r.getErrorMessage()));
                continue;
            }
            println(r.getDecompiledFunction().getC());
        }
        ifc.dispose();
    }
}
