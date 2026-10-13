// Dump disassembly of an address range: DumpAsm.java <out> <start hex> <end hex>
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;

public class DumpAsm extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        Address s = toAddr(Long.parseLong(a[1], 16)), e = toAddr(Long.parseLong(a[2], 16));
        try (PrintWriter w = new PrintWriter(new FileWriter(a[0]))) {
            InstructionIterator it = currentProgram.getListing().getInstructions(new AddressSet(s, e), true);
            while (it.hasNext()) {
                Instruction i = it.next();
                w.println(i.getAddress() + "  " + i.toString());
            }
        }
    }
}
