
void __thiscall FUN_004a1da0(int param_1,int param_2,int param_3)

{
  undefined4 uVar1;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bb98;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a86b0(param_2);
  FUN_005c3140(uVar1,param_2 + 4,param_3 + -4);
  *(undefined4 *)(param_1 + 0x29be4) = uVar1;
  ExceptionList = local_c;
  return;
}


