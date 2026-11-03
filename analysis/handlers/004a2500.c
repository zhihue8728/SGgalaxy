
void FUN_004a2500(int param_1)

{
  uint uVar1;
  undefined4 uVar2;
  int iVar3;
  int iVar4;
  undefined4 uVar5;
  TypeDescriptor *pTVar6;
  TypeDescriptor *pTVar7;
  undefined4 uVar8;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bc58;
  local_c = ExceptionList;
  iVar4 = 1;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8680(param_1);
  for (uVar1 = uVar1 & 0xff; uVar1 != 0; uVar1 = uVar1 - 1) {
    iVar4 = iVar4 + 4;
    uVar2 = FUN_005a86b0(param_1 + -4 + iVar4);
    uVar8 = 0;
    pTVar7 = &CGMonster::RTTI_Type_Descriptor;
    pTVar6 = &CGCtrlUnit::RTTI_Type_Descriptor;
    uVar5 = 0;
    uVar2 = FUN_005ca290(uVar2);
    iVar3 = FUN_0060a1c9(uVar2,uVar5,pTVar6,pTVar7,uVar8);
    if (iVar3 != 0) {
      FUN_004c5030(1);
    }
  }
  ExceptionList = local_c;
  return;
}


