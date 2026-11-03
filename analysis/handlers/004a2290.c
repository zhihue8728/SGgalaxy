
void FUN_004a2290(int param_1)

{
  undefined1 uVar1;
  uint uVar2;
  int iVar3;
  int local_124;
  undefined1 local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bc1b;
  local_c = ExceptionList;
  local_4 = 0;
  local_124 = 2;
  ExceptionList = &local_c;
  uVar2 = FUN_005a8690(param_1);
  for (uVar2 = uVar2 & 0xffff; uVar2 != 0; uVar2 = uVar2 - 1) {
    FUN_005a8da0(local_10c,0x100,"fldhsts");
    iVar3 = local_124 + 1;
    uVar1 = FUN_005a8680(local_124 + param_1);
    FUN_0050a270(local_10c,uVar1);
    local_124 = local_124 + 2;
    uVar1 = FUN_005a8680(iVar3 + param_1);
    FUN_0050a3b0(local_10c,uVar1);
  }
  ExceptionList = local_c;
  return;
}


