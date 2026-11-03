
void FUN_0057e5e0(byte *param_1,undefined4 param_2)

{
  byte *pbVar1;
  undefined1 uVar2;
  undefined2 uVar3;
  undefined2 uVar4;
  undefined4 uVar5;
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
  
  puStack_8 = &LAB_00638918;
  pvStack_c = ExceptionList;
  local_10 = 0xf;
  local_14 = 0;
  local_24 = (void *)((uint)local_24 & 0xffffff00);
  local_2c = 0xf;
  local_30 = 0;
  local_40 = (void *)((uint)local_40 & 0xffffff00);
  local_48 = param_1;
  local_4c = (uint)*param_1;
  local_50 = param_2;
  local_4 = 2;
  local_54 = 4;
  ExceptionList = &pvStack_c;
  uVar5 = FUN_005a86b0(param_1);
  pbVar1 = local_48 + local_54;
  local_54 = local_54 + 2;
  uVar3 = FUN_005a8690(pbVar1);
  pbVar1 = local_48 + local_54;
  local_54 = local_54 + 1;
  uVar2 = FUN_005a8680(pbVar1);
  FUN_005a9ff0(local_28,local_48,&local_54);
  pbVar1 = local_48 + local_54;
  local_54 = local_54 + 2;
  uVar4 = FUN_005a8690(pbVar1);
  FUN_005a9ff0(auStack_44,local_48,&local_54);
  FUN_0057e380(uVar5,uVar3,uVar2,local_28,uVar4,auStack_44);
  if (0xf < local_2c) {
                    /* WARNING: Subroutine does not return */
    _free(local_40);
  }
  local_30 = 0;
  local_40 = (void *)((uint)local_40 & 0xffffff00);
  local_2c = 0xf;
  if (0xf < local_10) {
                    /* WARNING: Subroutine does not return */
    _free(local_24);
  }
  ExceptionList = pvStack_c;
  return;
}


