
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __thiscall FUN_0049ece0(int param_1,undefined4 param_2,undefined4 param_3)

{
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062b92b;
  pvStack_c = ExceptionList;
  ExceptionList = &pvStack_c;
  FUN_0055e8f0();
  local_4 = 0;
  FUN_0055e7c0(param_2,param_3);
  if (param_1 == 0) {
    param_1 = 0;
  }
  else {
    param_1 = param_1 + 4;
  }
  FUN_0055e180(param_1,0,0);
  local_4 = 0xffffffff;
  FUN_0055e350();
  ExceptionList = pvStack_c;
  return;
}


