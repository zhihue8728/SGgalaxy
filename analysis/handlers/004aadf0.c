
void FUN_004aadf0(void)

{
  uint uVar1;
  undefined1 local_38 [4];
  void *local_34;
  undefined4 local_24;
  uint local_20;
  uint uStack_1c;
  uint uStack_18;
  uint uStack_14;
  uint uStack_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062c330;
  pvStack_c = ExceptionList;
  if (*(int *)(DAT_006ba7c8 + 0x1c58) == 1) {
    ExceptionList = &pvStack_c;
    FUN_005802b0();
  }
  else {
    ExceptionList = &pvStack_c;
    FUN_005802b0();
  }
  local_20 = 0xf;
  local_24 = 0;
  local_34 = (void *)((uint)local_34 & 0xffffff00);
  local_4 = 1;
  uVar1 = FUN_005a8680();
  for (uVar1 = uVar1 & 0xff; uVar1 != 0; uVar1 = uVar1 - 1) {
    FUN_005a9ff0();
    uStack_1c = FUN_005a8680();
    uStack_1c = uStack_1c & 0xff;
    uStack_18 = FUN_005a8680();
    uStack_18 = uStack_18 & 0xff;
    uStack_14 = FUN_005a8690();
    uStack_14 = uStack_14 & 0xffff;
    uStack_10 = FUN_005a8690();
    uStack_10 = uStack_10 & 0xffff;
    if (*(int *)(DAT_006ba7c8 + 0x1c58) == 1) {
      FUN_004025c0(local_38,0,0xffffffff);
      FUN_00580980();
    }
    else {
      FUN_004025c0(local_38,0,0xffffffff);
      FUN_005808e0();
    }
  }
  if (*(int *)(DAT_006ba7c8 + 0x1c58) == 1) {
    FUN_00580a20();
  }
  else {
    FUN_00580a20();
  }
  FUN_004a40c0();
  if (0xf < local_20) {
                    /* WARNING: Subroutine does not return */
    _free(local_34);
  }
  ExceptionList = pvStack_c;
  return;
}


