import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

// args: outDir, then pairs "name=addr" (thunk entries). Lists callers; decompiles callers into outDir/<addr>.c
public class Callers extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    String out = a[0]; new File(out+"/dec").mkdirs();
    DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
    Set<Function> todo = new LinkedHashSet<>();
    try (PrintWriter w = new PrintWriter(out+"/net_callers.txt")) {
      for (int i=1;i<a.length;i++) {
        String[] p=a[i].split("=");
        Address ad = toAddr(p[1]);
        w.println("== "+p[0]+" thunk "+ad);
        for (Reference r : getReferencesTo(ad)) {
          Function f = getFunctionContaining(r.getFromAddress());
          w.println("  from "+r.getFromAddress()+" in "+(f==null?"-":f.getName()+"@"+f.getEntryPoint())+" type="+r.getReferenceType());
          if (f!=null) todo.add(f);
        }
      }
    }
    try (PrintWriter idx = new PrintWriter(out+"/dec/index.txt")) {
      for (Function f : todo) {
        DecompileResults res = di.decompileFunction(f, 60, monitor);
        String c = res.decompileCompleted()? res.getDecompiledFunction().getC() : "// decompile failed: "+res.getErrorMessage();
        try (PrintWriter w = new PrintWriter(out+"/dec/"+f.getEntryPoint()+".c")) { w.println(c); }
        idx.println(f.getEntryPoint()+"\t"+f.getName()+"\t"+c.length());
      }
    }
  }
}
