
void FUN_004a1f80(int param_1)

{
  undefined1 uVar1;
  undefined2 uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  int iVar5;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bbd8;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar3 = FUN_005a86b0(param_1);
  uVar2 = FUN_005a8690(param_1 + 4);
  uVar4 = FUN_005a86b0(param_1 + 6);
  uVar1 = FUN_005a8680(param_1 + 10);
  iVar5 = FUN_0048da80(uVar3);
  if (iVar5 != 0) {
    FUN_0048fbe0(uVar2,uVar4,uVar1);
    ExceptionList = local_c;
    return;
  }
  uVar4 = FUN_004ee140();
  FUN_0047e540(DAT_006ba7dc,"%s Mission Objective ID doesn\'t exist : %d\n",uVar4,uVar3);
  ExceptionList = local_c;
  return;
}


