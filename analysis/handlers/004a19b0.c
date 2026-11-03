
void FUN_004a19b0(int param_1)

{
  undefined2 uVar1;
  undefined2 uVar2;
  undefined2 uVar3;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bb38;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8690(param_1);
  uVar2 = FUN_005a8690(param_1 + 2);
  uVar3 = FUN_005a8690(param_1 + 4);
  FUN_004a1960(uVar1,uVar2,uVar3);
  ExceptionList = local_c;
  return;
}


