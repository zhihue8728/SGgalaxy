import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class SendCatalog extends GhidraScript {
  static final Map<String,String> W = new HashMap<>();
  static { W.put("005a8fc0","u8");W.put("005a9020","u16");W.put("005a9070","u32");W.put("005a90c0","u64");
           W.put("005a9110","s8");W.put("005a9180","s16");W.put("005a91f0","raw"); }
  public void run() throws Exception {
    String out=getScriptArgs()[0];
    Set<Function> fs=new TreeSet<>((x,y)->x.getEntryPoint().compareTo(y.getEntryPoint()));
    for (String s : new String[]{"005a8f10","005a8f80"})
      for (Reference r : getReferencesTo(toAddr(s))) { Function f=getFunctionContaining(r.getFromAddress()); if(f!=null) fs.add(f); }
    try (PrintWriter w=new PrintWriter(out)) {
      for (Function f : fs) {
        String cur=null; List<String> toks=new ArrayList<>();
        Integer lastPush=null;
        InstructionIterator it=currentProgram.getListing().getInstructions(f.getBody(),true);
        while (it.hasNext()) {
          Instruction ins=it.next();
          String mn=ins.getMnemonicString();
          if (mn.equals("PUSH") && ins.getOpObjects(0).length>0 && ins.getOpObjects(0)[0] instanceof Scalar)
            lastPush=(int)((Scalar)ins.getOpObjects(0)[0]).getUnsignedValue();
          else if (mn.equals("PUSH")) lastPush=null;
          if (mn.equals("CALL")) {
            Address t=null; for (Reference r: ins.getReferencesFrom()) if (r.getReferenceType().isCall()) t=r.getToAddress();
            if (t==null) continue;
            String ts=t.toString();
            if (ts.equals("005a8f10")||ts.equals("005a8f80")) {
              if (cur!=null) w.println(f.getEntryPoint()+"\t"+cur+"\tNOSEND\t"+toks);
              cur=lastPush==null?"?":String.format("0x%02x",lastPush); toks=new ArrayList<>();
            } else if (W.containsKey(ts)) { if(cur!=null) toks.add(W.get(ts)); }
            else if (ts.equals("005aa1e0")) { if(cur!=null) w.println(f.getEntryPoint()+"\t"+cur+"\tSEND\t"+toks); cur=null; toks=new ArrayList<>(); }
          }
        }
        if (cur!=null) w.println(f.getEntryPoint()+"\t"+cur+"\tOPEN\t"+toks);
      }
    }
  }
}
