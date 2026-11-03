
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void FUN_004a23b0(int param_1)

{
  undefined1 uVar1;
  undefined1 uVar2;
  uint uVar3;
  undefined4 uVar4;
  int iVar5;
  void *pvStack_c;
  undefined1 *puStack_8;
  int local_4;
  
  puStack_8 = &LAB_0062bc46;
  pvStack_c = ExceptionList;
  iVar5 = 1;
  local_4 = 0;
  ExceptionList = &pvStack_c;
  uVar3 = FUN_005a8680(param_1);
  FUN_004d5930();
  local_4._0_1_ = 1;
  for (uVar3 = uVar3 & 0xff; uVar3 != 0; uVar3 = uVar3 - 1) {
    uVar4 = FUN_005a86b0(param_1 + iVar5);
    uVar1 = FUN_005a8680(param_1 + iVar5 + 4);
    iVar5 = iVar5 + 6;
    uVar2 = FUN_005a8680(param_1 + -1 + iVar5);
    FUN_004d3050(uVar4,uVar4,uVar1,uVar2,1,0);
  }
  uVar4 = FUN_005a86b0(iVar5 + param_1);
  uVar1 = FUN_005a8680(iVar5 + 4 + param_1);
  FUN_004999a0(uVar4,uVar1,0);
  local_4 = (uint)local_4._1_3_ << 8;
  FUN_004d5520();
  ExceptionList = pvStack_c;
  return;
}


