
undefined4 FUN_00546000(int param_1)

{
  byte bVar1;
  undefined1 uVar2;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_006346d8;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  bVar1 = FUN_005a8680(param_1);
  uVar2 = FUN_005a8680(param_1 + 1);
  *(undefined1 *)(DAT_00c53094 + 5) = uVar2;
  if (bVar1 - 1 < 100) {
    *(byte *)(DAT_00c53094 + 4) = bVar1;
  }
  ExceptionList = local_c;
  return CONCAT31((int3)(bVar1 - 1 >> 8),1);
}


