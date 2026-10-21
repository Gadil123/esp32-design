import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataUtilities;
import ghidra.program.model.data.StringDataType;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

/**
 * Define null-terminated strings at the given addresses, then print all
 * references to those addresses and to any pointer-sized words that contain
 * the address.
 *
 * args: one or more addresses
 */
public class StringRefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String s : getScriptArgs()) {
            Address target = toAddr(Long.decode(s));
            println("STRING_AT " + target);
            try {
                Data d = currentProgram.getListing().createData(target, new StringDataType());
                if (d != null) {
                    println("  defined " + d.getValue());
                }
            }
            catch (Exception e) {
                println("  define failed: " + e);
            }
            printRefs(target);
        }
    }

    private void printRefs(Address target) {
        ReferenceIterator it = currentProgram.getReferenceManager().getReferencesTo(target);
        int n = 0;
        while (it.hasNext()) {
            Reference r = it.next();
            Address from = r.getFromAddress();
            Function f = getFunctionContaining(from);
            println("  REF " + from + " type=" + r.getReferenceType()
                    + " func=" + (f == null ? "-" : f.getEntryPoint() + " " + f.getName()));
            n++;
        }
        println("  refs=" + n);
    }
}
