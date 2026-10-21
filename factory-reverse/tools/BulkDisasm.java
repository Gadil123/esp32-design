import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.FlowType;

/**
 * Bulk-disassemble a code range and seed functions from direct calls, code
 * pointers in data, and common RISC-V stack-frame prologues.
 *
 * args[0] = code start, args[1] = code end (exclusive)
 */
public class BulkDisasm extends GhidraScript {
    private long lo, hi;

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        lo = Long.decode(a[0]);
        hi = Long.decode(a[1]);
        Address start = toAddr(lo);
        Address end = toAddr(hi - 1);

        println("BULK_DISASM " + start + "-" + end);
        DisassembleCommand d = new DisassembleCommand(start, new AddressSet(start, end), true);
        d.applyTo(currentProgram, monitor);

        int direct = 0;
        InstructionIterator ii = currentProgram.getListing().getInstructions(
                new AddressSet(start, end), true);
        for (Instruction ins : ii) {
            FlowType ft = ins.getFlowType();
            if (!ft.isCall()) {
                continue;
            }
            for (Address t : ins.getFlows()) {
                if (inCode(t) && makeFunction(t)) {
                    direct++;
                }
            }
        }
        println("DIRECT_CALL_FUNCS " + direct);

        int ptr = 0;
        Memory mem = currentProgram.getMemory();
        for (MemoryBlock block : mem.getBlocks()) {
            if (block.isExecute()) {
                continue;
            }
            long s = block.getStart().getOffset();
            long e = block.getEnd().getOffset();
            for (long p = s; p + 4 <= e; p += 4) {
                try {
                    int v = mem.getInt(toAddr(p));
                    long u = v & 0xffffffffL;
                    if (u >= lo && u < hi && makeFunction(toAddr(u))) {
                        ptr++;
                    }
                }
                catch (Exception ex) {
                    // unreadable or crossing a block; skip
                }
            }
        }
        println("DATA_POINTER_FUNCS " + ptr);

        int pro = 0;
        ii = currentProgram.getListing().getInstructions(new AddressSet(start, end), true);
        for (Instruction ins : ii) {
            Address at = ins.getAddress();
            if (getFunctionContaining(at) != null) {
                continue;
            }
            String m = ins.getMnemonicString();
            String ops = ins.toString();
            boolean stack = (m.equals("addi") || m.equals("c.addi16sp") || m.equals("c.addi"))
                    && ops.contains("sp,sp,");
            if (stack && makeFunction(at)) {
                pro++;
            }
        }
        println("PROLOGUE_FUNCS " + pro);
        println("TOTAL_FUNCS " + currentProgram.getFunctionManager().getFunctionCount()
                + " INSTRUCTIONS " + currentProgram.getListing().getNumInstructions());
    }

    private boolean makeFunction(Address a) {
        if (!inCode(a) || getFunctionAt(a) != null) {
            return false;
        }
        if (getInstructionAt(a) == null) {
            disassemble(a);
        }
        new CreateFunctionCmd(a).applyTo(currentProgram, monitor);
        return getFunctionAt(a) != null;
    }

    private boolean inCode(Address a) {
        return a != null && a.getOffset() >= lo && a.getOffset() < hi;
    }
}
