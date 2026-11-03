
void FUN_005460c0(int param_1)

{
  undefined2 uVar1;
  undefined2 uVar2;
  uint uVar3;
  undefined4 uVar4;
  int iVar5;
  int iVar6;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_006346f8;
  local_c = ExceptionList;
  iVar6 = 1;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar3 = FUN_005a8680(param_1);
  for (uVar3 = uVar3 & 0xff; uVar3 != 0; uVar3 = uVar3 - 1) {
    uVar4 = FUN_005a86b0(param_1 + iVar6);
    uVar1 = FUN_005a8690(param_1 + iVar6 + 4);
    iVar6 = iVar6 + 8;
    uVar2 = FUN_005a8690(param_1 + -2 + iVar6);
    iVar5 = FUN_004ee2c0(uVar4);
    if (iVar5 != 0) {
      FUN_005c52b0(uVar1,uVar2);
    }
  }
  ExceptionList = local_c;
  return;
}


