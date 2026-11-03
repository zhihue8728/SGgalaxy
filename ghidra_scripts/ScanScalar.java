import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import java.util.*;
public class ScanScalar extends GhidraScript {
  public void run() throws Exception {
    Set<Long> want = new HashSet<>();
    for (String s : getScriptArgs()) want.add(Long.decode(s));
    InstructionIterator it = currentProgram.getListing().getInstructions(true);
    while (it.hasNext()) {
      Instruction ins = it.next();
      for (int i=0;i<ins.getNumOperands();i++) {
        Object[] objs = ins.getOpObjects(i);
        for (Object o : objs) if (o instanceof Scalar && want.contains(((Scalar)o).getUnsignedValue())) {
          Function f = getFunctionContaining(ins.getAddress());
          println("HIT "+Long.toHexString(((Scalar)o).getUnsignedValue())+" "+ins.getAddress()+" "+ins+" in "+(f==null?"-":f.getEntryPoint()));
        }
      }
    }
  }
}
