import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.FlowType;

import java.util.HashSet;
import java.util.LinkedList;
import java.util.Queue;
import java.util.Set;

/**
 * Disassemble reachable code from an entry point without scanning the whole
 * zero-filled address space.
 *
 * args[0] entry address
 * args[1] code start
 * args[2] code end (exclusive)
 */
public class RecursiveDisasm extends GhidraScript {
    private long lo;
    private long hi;
    private final Set<Long> queued = new HashSet<>();
    private final Queue<Address> work = new LinkedList<>();

    @Override
    public void run() throws Exception {
        String[] sargs = getScriptArgs();
        long entry = Long.decode(sargs[0]);
        lo = Long.decode(sargs[1]);
        hi = Long.decode(sargs[2]);
        add(entry);

        int funcs = 0;
        while (!work.isEmpty() && funcs < 20000) {
            Address a = work.poll();
            if (!inCode(a)) {
                continue;
            }
            Function f = getFunctionAt(a);
            if (f == null) {
                DisassembleCommand dis = new DisassembleCommand(a, null, true);
                dis.applyTo(currentProgram, monitor);
                new CreateFunctionCmd(a).applyTo(currentProgram, monitor);
                f = getFunctionAt(a);
            }
            if (f == null) {
                continue;
            }
            funcs++;
            InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
            for (Instruction ins : it) {
                FlowType ft = ins.getFlowType();
                if (!ft.isCall()) {
                    continue;
                }
                for (Address target : ins.getFlows()) {
                    if (inCode(target)) {
                        add(target.getOffset());
                    }
                }
            }
        }
        println("RECURSIVE_DISASM entry=" + sargs[0] + " functions_visited=" + funcs
                + " functions_total=" + currentProgram.getFunctionManager().getFunctionCount()
                + " instructions=" + currentProgram.getListing().getNumInstructions());
    }

    private void add(long offset) {
        if (offset < lo || offset >= hi || !queued.add(offset)) {
            return;
        }
        work.add(toAddr(offset));
    }

    private boolean inCode(Address a) {
        if (a == null) {
            return false;
        }
        long v = a.getOffset();
        return v >= lo && v < hi;
    }
}
