
undefined4 FUN_00547bb0(int param_1)

{
  char cVar1;
  undefined1 uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  uint uVar5;
  uint uVar6;
  int iVar7;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00634908;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  cVar1 = FUN_005a8680(param_1);
  if (cVar1 == '\0') {
    FUN_005520d0();
    iVar7 = 2;
    uVar5 = FUN_005a8680(param_1 + 1);
    for (uVar5 = uVar5 & 0xff; uVar5 != 0; uVar5 = uVar5 - 1) {
      uVar3 = FUN_005a86b0(param_1 + iVar7);
      iVar7 = iVar7 + 5;
      uVar6 = FUN_005a8680(param_1 + -1 + iVar7);
      for (uVar6 = uVar6 & 0xff; uVar6 != 0; uVar6 = uVar6 - 1) {
        uVar4 = FUN_005a86b0(param_1 + iVar7);
        iVar7 = iVar7 + 5;
        uVar2 = FUN_005a8680(param_1 + -1 + iVar7);
        FUN_00552f80(uVar3,uVar4,uVar2);
      }
    }
  }
  else if (cVar1 == '\x01') {
    uVar3 = FUN_005a86b0(param_1 + 1);
    uVar4 = FUN_005a86b0(param_1 + 5);
    uVar2 = FUN_005a8680(param_1 + 9);
    FUN_00552f80(uVar3,uVar4,uVar2);
  }
  FUN_005521d0();
  ExceptionList = local_c;
  return 1;
}


