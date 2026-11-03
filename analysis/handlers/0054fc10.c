
void __thiscall FUN_0054fc10(int param_1,int param_2)

{
  undefined1 uVar1;
  undefined1 uVar2;
  undefined2 uVar3;
  undefined2 uVar4;
  uint uVar5;
  undefined4 uVar6;
  undefined4 uVar7;
  int iVar8;
  int local_128;
  undefined1 auStack_10c [256];
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0063552b;
  pvStack_c = ExceptionList;
  local_4 = 0;
  local_128 = 2;
  ExceptionList = &pvStack_c;
  uVar5 = FUN_005a8690(param_2);
  (**(code **)(*(int *)(param_1 + 4) + 8))();
  for (uVar5 = uVar5 & 0xffff; uVar5 != 0; uVar5 = uVar5 - 1) {
    uVar3 = FUN_005a8690(local_128 + param_2);
    uVar1 = FUN_005a8680(local_128 + 2 + param_2);
    uVar6 = FUN_005a86b0(local_128 + 3 + param_2);
    uVar7 = FUN_005a86b0(local_128 + 7 + param_2);
    FUN_005a8da0(auStack_10c,0x100,"mrkminf");
    iVar8 = local_128 + 0xc;
    uVar2 = FUN_005a8680(local_128 + 0xb + param_2);
    local_128 = local_128 + 0xe;
    uVar4 = FUN_005a8690(iVar8 + param_2);
    FUN_0054fa00(uVar3,uVar1,uVar6,uVar7,auStack_10c,uVar2,uVar4);
  }
  ExceptionList = pvStack_c;
  return;
}


