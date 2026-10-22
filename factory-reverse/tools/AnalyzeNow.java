import ghidra.app.plugin.core.analysis.AutoAnalysisManager;
import ghidra.app.script.GhidraScript;

public class AnalyzeNow extends GhidraScript {
    @Override
    public void run() throws Exception {
        println("ANALYZE_NOW_START");
        AutoAnalysisManager mgr = AutoAnalysisManager.getAnalysisManager(currentProgram);
        mgr.startAnalysis(monitor, false);
        println("ANALYZE_NOW_DONE functions=" + currentProgram.getFunctionManager().getFunctionCount()
            + " instructions=" + currentProgram.getListing().getNumInstructions());
    }
}
