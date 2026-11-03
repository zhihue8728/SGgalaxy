import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;
public class RefsTo extends GhidraScript {
  public void run() throws Exception {
    for (String s : getScriptArgs()) {
      Address ad = toAddr(s);
      println("## "+s);
      for (Reference r : getReferencesTo(ad)) {
        Function f=getFunctionContaining(r.getFromAddress());
        println("  "+r.getReferenceType()+" "+r.getFromAddress()+" in "+(f==null?"-":f.getEntryPoint()));
      }
    }
  }
}
