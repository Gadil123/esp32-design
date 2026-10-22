import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.FlowType;

/**
 * Linear-sweep a RISC-V code range, then seed function starts from prologues,
 * direct call targets, and even code pointers in data.
 *
 * args[0] code start, args[1] code end (exclusive)
 */
public class LinearDisasm extends GhidraScript {
    private long lo, hi;

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        lo = Long.decode(a[0]);
        hi = Long.decode(a[1]);
        long pc = lo;
        int decoded = 0, failed = 0;
        while (pc < hi) {
            Address at = toAddr(pc);
            Instruction ins = getInstructionAt(at);
            if (ins == null) {
                disassemble(at);
                ins = getInstructionAt(at);
            }
            if (ins == null) {
                pc += 2;
                failed++;
            }
            else {
                pc += ins.getLength();
                decoded++;
            }
        }
        println("LINEAR decoded=" + decoded + " failed_slots=" + failed);

        int calls = 0;
        InstructionIterator it = currentProgram.getListing().getInstructions(
                toAddr(lo), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            if (ins.getAddress().getOffset() >= hi) break;
            FlowType ft = ins.getFlowType();
            if (!ft.isCall()) continue;
            for (Address t : ins.getFlows()) {
                if (inCode(t) && getFunctionAt(t) == null) {
                    new CreateFunctionCmd(t).applyTo(currentProgram, monitor);
                    if (getFunctionAt(t) != null) calls++;
                }
            }
        }
        println("CALL_FUNCS " + calls);

        int pro = 0;
        it = currentProgram.getListing().getInstructions(toAddr(lo), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            Address at = ins.getAddress();
            if (at.getOffset() >= hi) break;
            if (getFunctionAt(at) != null) continue;
            String m = ins.getMnemonicString();
            String ops = ins.toString();
            boolean stack = (m.equals("addi") || m.equals("c.addi16sp") || m.equals("c.addi"))
                    && ops.contains("sp,sp,");
            if (stack) {
                new CreateFunctionCmd(at).applyTo(currentProgram, monitor);
                if (getFunctionAt(at) != null) pro++;
            }
        }
        println("PROLOGUE_FUNCS " + pro);

        int ptr = 0, ptrSeen = 0;
        Memory mem = currentProgram.getMemory();
        for (MemoryBlock block : mem.getBlocks()) {
            if (block.isExecute()) continue;
            long s = block.getStart().getOffset();
            long e = block.getEnd().getOffset();
            for (long p = (s + 3) & ~3L; p + 4 <= e; p += 4) {
                try {
                    long u = mem.getInt(toAddr(p)) & 0xffffffffL;
                    if (u < lo || u >= hi || (u & 1) != 0) continue;
                    ptrSeen++;
                    Address at = toAddr(u);
                    if (getFunctionContaining(at) != null) continue;
                    if (getInstructionAt(at) == null) continue;
                    new CreateFunctionCmd(at).applyTo(currentProgram, monitor);
                    if (getFunctionAt(at) != null) ptr++;
                }
                catch (Exception ex) {
                    // skip unreadable slots
                }
            }
        }
        println("PTR_CANDIDATES " + ptrSeen + " PTR_FUNCS " + ptr);
        println("TOTAL functions=" + currentProgram.getFunctionManager().getFunctionCount()
                + " instructions=" + currentProgram.getListing().getNumInstructions());
    }

    private boolean inCode(Address a) {
        return a != null && a.getOffset() >= lo && a.getOffset() < hi;
    }
}
