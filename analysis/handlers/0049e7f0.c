
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

undefined4 __thiscall FUN_0049e7f0(int param_1,undefined4 param_2,undefined4 param_3)

{
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062b84b;
  local_c = ExceptionList;
  if (*(char *)(param_1 + 0x29c87) != '\0') {
    return 0;
  }
  ExceptionList = &local_c;
  *(undefined1 *)(param_1 + 0x29c87) = 1;
  FUN_004f9290();
  local_4 = 0;
  FUN_004f8820(param_2,param_3);
  FUN_004f3c30(param_1 + 4);
  *(undefined1 *)(param_1 + 0x29c87) = 0;
  *(undefined1 *)(param_1 + 0x29c86) = 0;
  local_4 = 0xffffffff;
  FUN_004f9040();
  ExceptionList = local_c;
  return 1;
}


