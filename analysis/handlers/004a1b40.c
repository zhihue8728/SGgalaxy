
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __thiscall FUN_004a1b40(int param_1,undefined4 param_2,undefined4 param_3)

{
  void *local_c;
  undefined1 *puStack_8;
  int local_4;
  
  puStack_8 = &LAB_0062bb86;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  FUN_005e83b0();
  local_4._0_1_ = 1;
  FUN_005e85b0(param_2,param_3);
  if (param_1 == 0) {
    param_1 = 0;
  }
  else {
    param_1 = param_1 + 4;
  }
  FUN_005e7d90(param_1);
  local_4 = (uint)local_4._1_3_ << 8;
  FUN_005e8490();
  ExceptionList = local_c;
  return;
}


