import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

/**
 * Print references to addresses (typically strings or data).
 * Accepts one or more numeric addresses.
 */
public class FindRefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String s : getScriptArgs()) {
            Address target = toAddr(Long.decode(s));
            println("REFS_TO " + target);
            ReferenceIterator it = currentProgram.getReferenceManager().getReferencesTo(target);
            while (it.hasNext()) {
                Reference r = it.next();
                Address from = r.getFromAddress();
                Function f = getFunctionContaining(from);
                println("  " + from + " type=" + r.getReferenceType()
                        + " func=" + (f == null ? "-" : f.getEntryPoint() + " " + f.getName()));
            }
        }
    }
}
