import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;
// args: outDir addr...  -> per function: decompiled C, plus summary line with strings referenced and callees count
public class Handlers extends GhidraScript {
  public void run() throws Exception {
    String[] a=getScriptArgs(); String out=a[0]; new File(out).mkdirs();
    DecompInterface di=new DecompInterface(); di.openProgram(currentProgram);
    try (PrintWriter sum=new PrintWriter(out+"/summary.tsv")) {
      for (int i=1;i<a.length;i++) {
        Function f=getFunctionAt(toAddr(a[i])); if(f==null) {sum.println(a[i]+"\tNOFUNC"); continue;}
        TreeSet<String> strs=new TreeSet<>();
        TreeSet<String> callees=new TreeSet<>();
        for (Address ad : f.getBody().getAddresses(true)) {
          for (Reference r : getReferencesFrom(ad)) {
            Data d=getDataAt(r.getToAddress());
            if (d!=null && d.hasStringValue()) { String v=d.getDefaultValueRepresentation(); if(v.length()>90) v=v.substring(0,90); strs.add(v.replace("\t"," ")); }
            if (r.getReferenceType().isCall()) callees.add(r.getToAddress().toString());
          }
        }
        DecompileResults res=di.decompileFunction(f,90,monitor);
        String c=res.decompileCompleted()?res.getDecompiledFunction().getC():"// failed";
        try (PrintWriter w=new PrintWriter(out+"/"+f.getEntryPoint()+".c")) { w.println(c); }
        sum.println(f.getEntryPoint()+"\t"+f.getBody().getNumAddresses()+"\t"+c.split("\n").length+"\t"+strs+"\t"+callees.size());
      }
    }
  }
}
