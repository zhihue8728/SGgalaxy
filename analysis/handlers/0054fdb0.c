
void FUN_0054fdb0(int param_1)

{
  undefined1 uVar1;
  undefined1 uVar2;
  undefined2 uVar3;
  undefined2 uVar4;
  uint uVar5;
  int iVar6;
  undefined4 uVar7;
  undefined4 uVar8;
  int iVar9;
  int local_128;
  undefined1 local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0063554b;
  local_c = ExceptionList;
  local_4 = 0;
  local_128 = 2;
  ExceptionList = &local_c;
  uVar5 = FUN_005a8690(param_1);
  for (uVar5 = uVar5 & 0xffff; uVar5 != 0; uVar5 = uVar5 - 1) {
    uVar3 = FUN_005a8690(local_128 + param_1);
    FUN_0054f520(uVar3);
    local_128 = local_128 + 2;
  }
  iVar6 = local_128 + 2;
  uVar5 = FUN_005a8690(local_128 + param_1);
  for (uVar5 = uVar5 & 0xffff; uVar5 != 0; uVar5 = uVar5 - 1) {
    uVar3 = FUN_005a8690(iVar6 + param_1);
    uVar1 = FUN_005a8680(iVar6 + 2 + param_1);
    uVar7 = FUN_005a86b0(iVar6 + 3 + param_1);
    uVar8 = FUN_005a86b0(iVar6 + 7 + param_1);
    FUN_005a8da0(local_10c,0x100,"mrkmiu");
    iVar9 = iVar6 + 0xc;
    uVar2 = FUN_005a8680(iVar6 + 0xb + param_1);
    iVar6 = iVar6 + 0xe;
    uVar4 = FUN_005a8690(iVar9 + param_1);
    FUN_0054fa00(uVar3,uVar1,uVar7,uVar8,local_10c,uVar2,uVar4);
  }
  ExceptionList = local_c;
  return;
}


