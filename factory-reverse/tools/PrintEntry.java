import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.Address;

/**
 * Minimal headless Ghidra script for a raw RISC-V segment.
 *
 * Usage (after importing factory_seg1.bin at base 0x40800000):
 *   analyzeHeadless <project_dir> <project_name> \
 *     -process factory_seg1.bin -noanalysis \
 *     -scriptPath <this_dir> -postScript PrintEntry.java
 */
public class PrintEntry extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address addr = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(0x408002b0L);
        println("PROGRAM " + currentProgram.getName()
                + " LANG " + currentProgram.getLanguage().getLanguageID());
        DisassembleCommand cmd = new DisassembleCommand(addr, null, true);
        cmd.applyTo(currentProgram, monitor);
        for (long i = 0; i < 0x100; i += 2) {
            Address a = addr.add(i);
            var ins = getInstructionAt(a);
            if (ins != null) {
                println(a + "  " + ins);
            }
        }
    }
}
