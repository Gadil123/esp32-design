import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
public class DumpBytes extends GhidraScript {
    public void run() throws Exception {
        for (String s : getScriptArgs()) {
            Address a = toAddr(Long.decode(s));
            byte[] b = new byte[80];
            int n = currentProgram.getMemory().getBytes(a, b);
            StringBuilder sb = new StringBuilder();
            for (int i=0;i<n;i++) sb.append(String.format("%02x ", b[i]&0xff));
            println(a + " n=" + n + " " + sb);
            println("  ascii=" + new String(b,0,Math.max(n,0)).replaceAll("[^\\x20-\\x7e]","."));
        }
    }
}
