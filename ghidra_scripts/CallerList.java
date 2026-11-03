import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;
public class CallerList extends GhidraScript {
  public void run() throws Exception {
    for (String s : getScriptArgs()) {
      TreeSet<String> fs=new TreeSet<>();
      for (Reference r : getReferencesTo(toAddr(s))) { Function f=getFunctionContaining(r.getFromAddress()); fs.add(f==null?"-":f.getEntryPoint().toString()); }
      println("CALLERS "+s+" "+fs.size()+" "+String.join(" ",fs));
    }
  }
}
