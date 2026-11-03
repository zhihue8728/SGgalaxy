import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class ExportInfo extends GhidraScript {
  String fn(Address a){ Function f=getFunctionContaining(a); return f==null? "-" : f.getName()+"@"+f.getEntryPoint(); }
  public void run() throws Exception {
    String out = getScriptArgs()[0];
    new File(out).mkdirs();
    // imports with referencing functions
    try (PrintWriter w = new PrintWriter(out+"/imports.txt")) {
      SymbolTable st = currentProgram.getSymbolTable();
      for (Symbol s : st.getExternalSymbols()) {
        Set<String> callers = new TreeSet<>();
        for (Reference r : getReferencesTo(s.getAddress())) callers.add(fn(r.getFromAddress()));
        w.println(s.getParentNamespace().getName()+"::"+s.getName()+" ["+s.getAddress()+"] callers="+callers);
      }
      // thunks / IAT entries in .idata-like data
      for (Symbol s : st.getAllSymbols(true)) {
        if (s.getSymbolType()==SymbolType.LABEL && s.getName().startsWith("PTR_") ) {}
      }
    }
    // defined strings with xrefs
    try (PrintWriter w = new PrintWriter(out+"/strings.txt")) {
      DataIterator it = currentProgram.getListing().getDefinedData(true);
      while (it.hasNext()) {
        Data d = it.next();
        if (!d.hasStringValue()) continue;
        String v = d.getDefaultValueRepresentation().replace("\n","\\n");
        Set<String> refs = new TreeSet<>();
        for (Reference r : getReferencesTo(d.getAddress())) refs.add(fn(r.getFromAddress()));
        w.println(d.getAddress()+"\t"+v+"\t"+refs);
      }
    }
    // function list
    try (PrintWriter w = new PrintWriter(out+"/functions.txt")) {
      for (Function f : currentProgram.getFunctionManager().getFunctions(true))
        w.println(f.getEntryPoint()+"\t"+f.getName()+"\t"+f.getBody().getNumAddresses()+"\t"+(f.isThunk()?"thunk":""));
    }
  }
}
