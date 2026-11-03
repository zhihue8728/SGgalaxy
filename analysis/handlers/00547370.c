
undefined4 __thiscall FUN_00547370(int param_1,undefined4 param_2)

{
  uint uVar1;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_006347e8;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8680(param_2);
  *(uint *)(param_1 + 0x1c58) = uVar1 & 0xff;
  ExceptionList = local_c;
  return 1;
}


