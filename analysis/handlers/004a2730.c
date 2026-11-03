
void FUN_004a2730(int param_1,int param_2)

{
  undefined4 uVar1;
  int iVar2;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bcb8;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a86b0(param_1);
  iVar2 = FUN_005ca290(uVar1);
  if (iVar2 != 0) {
    FUN_004dcb90(param_1 + 4,param_2 + -4);
  }
  ExceptionList = local_c;
  return;
}


