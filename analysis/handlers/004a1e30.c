
void FUN_004a1e30(int param_1)

{
  undefined1 uVar1;
  undefined2 uVar2;
  undefined2 uVar3;
  int iVar4;
  uint uVar5;
  undefined4 uVar6;
  int iVar7;
  undefined1 local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bbbb;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8680(param_1);
  iVar4 = 2;
  uVar5 = FUN_005a8680(param_1 + 1);
  FUN_005ec420();
  FUN_005eb700(uVar1);
  for (uVar5 = uVar5 & 0xff; uVar5 != 0; uVar5 = uVar5 - 1) {
    FUN_005a8da0(local_10c,0x100,"fldbwl");
    uVar6 = FUN_005a86b0(iVar4 + param_1);
    iVar7 = iVar4 + 6;
    uVar2 = FUN_005a8690(iVar4 + 4 + param_1);
    iVar4 = iVar4 + 8;
    uVar3 = FUN_005a8690(iVar7 + param_1);
    FUN_005ec900(local_10c,uVar6,uVar2,uVar3);
  }
  FUN_005450a0(0xd,0);
  ExceptionList = local_c;
  return;
}


