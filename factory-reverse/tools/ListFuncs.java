import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
public class ListFuncs extends GhidraScript {
    public void run() throws Exception {
        long lo=Long.decode(getScriptArgs()[0]), hi=Long.decode(getScriptArgs()[1]);
        FunctionIterator it=currentProgram.getFunctionManager().getFunctions(toAddr(lo), true);
        while(it.hasNext()) {
            Function f=it.next();
            long a=f.getEntryPoint().getOffset();
            if(a>hi) break;
            if(a>=lo) println(f.getEntryPoint()+" size="+f.getBody().getNumAddresses()+" "+f.getName());
        }
    }
}
