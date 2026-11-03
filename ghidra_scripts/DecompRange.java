import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

// args: outDir, then items: "lo-hi" (hex range of function entries) or single address. Decompiles each function; also writes xrefs-to for each.
public class DecompRange extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs(); String out=a[0]; new File(out).mkdirs();
    DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
    Set<Function> todo = new LinkedHashSet<>();
    for (int i=1;i<a.length;i++) {
      if (a[i].contains("-")) {
        String[] r=a[i].split("-");
        for (Function f : currentProgram.getFunctionManager().getFunctions(toAddr(r[0]), true)) {
          if (f.getEntryPoint().compareTo(toAddr(r[1]))>0) break; todo.add(f);
        }
      } else { Function f=getFunctionAt(toAddr(a[i])); if(f==null) f=getFunctionContaining(toAddr(a[i])); if (f!=null) todo.add(f); }
    }
    for (Function f : todo) {
      DecompileResults res = di.decompileFunction(f, 90, monitor);
      StringBuilder sb=new StringBuilder();
      sb.append("// xrefs to ").append(f.getName()).append(": ");
      int n=0; for (Reference r : getReferencesTo(f.getEntryPoint())) { if(n++<25){ Function c=getFunctionContaining(r.getFromAddress()); sb.append(r.getFromAddress()).append("(").append(c==null?"-":c.getEntryPoint().toString()).append(") "); } }
      sb.append("\n");
      sb.append(res.decompileCompleted()? res.getDecompiledFunction().getC() : "// failed");
      try (PrintWriter w = new PrintWriter(out+"/"+f.getEntryPoint()+".c")) { w.println(sb); }
    }
  }
}
