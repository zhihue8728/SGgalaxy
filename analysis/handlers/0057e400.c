
void __thiscall FUN_0057e400(int param_1,byte *param_2,undefined4 param_3)

{
  byte *pbVar1;
  int iVar2;
  undefined1 uVar3;
  undefined2 uVar4;
  undefined2 uVar5;
  uint uVar6;
  undefined4 uVar7;
  int local_54;
  undefined4 local_50;
  uint local_4c;
  byte *local_48;
  undefined1 auStack_44 [4];
  void *local_40;
  undefined4 local_30;
  uint local_2c;
  undefined1 local_28 [4];
  void *local_24;
  undefined4 local_14;
  uint local_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_006388e8;
  pvStack_c = ExceptionList;
  local_10 = 0xf;
  local_14 = 0;
  local_24 = (void *)((uint)local_24 & 0xffffff00);
  local_2c = 0xf;
  local_30 = 0;
  local_40 = (void *)((uint)local_40 & 0xffffff00);
  local_4._0_1_ = 1;
  local_4._1_3_ = 0;
  ExceptionList = &pvStack_c;
  FUN_0057d950(*(undefined4 *)(*(int *)(param_1 + 0xc) + 4));
  *(int *)(*(int *)(param_1 + 0xc) + 4) = *(int *)(param_1 + 0xc);
  *(undefined4 *)(param_1 + 0x10) = 0;
  *(undefined4 *)*(undefined4 *)(param_1 + 0xc) = *(undefined4 *)(param_1 + 0xc);
  *(int *)(*(int *)(param_1 + 0xc) + 8) = *(int *)(param_1 + 0xc);
  local_48 = param_2;
  local_4c = (uint)*param_2;
  local_50 = param_3;
  local_4 = CONCAT31(local_4._1_3_,2);
  local_54 = 2;
  uVar6 = FUN_005a8690(param_2);
  iVar2 = local_54;
  for (uVar6 = uVar6 & 0xffff; uVar6 != 0; uVar6 = uVar6 - 1) {
    local_54 = iVar2 + 4;
    uVar7 = FUN_005a86b0(local_48 + iVar2);
    pbVar1 = local_48 + local_54;
    local_54 = local_54 + 2;
    uVar4 = FUN_005a8690(pbVar1);
    pbVar1 = local_48 + local_54;
    local_54 = local_54 + 1;
    uVar3 = FUN_005a8680(pbVar1);
    FUN_005a9ff0(local_28,local_48,&local_54);
    pbVar1 = local_48 + local_54;
    local_54 = local_54 + 2;
    uVar5 = FUN_005a8690(pbVar1);
    FUN_005a9ff0(auStack_44,local_48,&local_54);
    FUN_0057e380(uVar7,uVar4,uVar3,local_28,uVar5,auStack_44);
    iVar2 = local_54;
  }
  local_54 = iVar2;
  if (0xf < local_2c) {
                    /* WARNING: Subroutine does not return */
    _free(local_40);
  }
  local_30 = 0;
  local_2c = 0xf;
  local_40 = (void *)((uint)local_40 & 0xffffff00);
  if (0xf < local_10) {
                    /* WARNING: Subroutine does not return */
    _free(local_24);
  }
  ExceptionList = pvStack_c;
  return;
}


