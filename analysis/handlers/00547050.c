
undefined4 FUN_00547050(int param_1)

{
  int iVar1;
  undefined4 uVar2;
  uint uVar3;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  iVar1 = DAT_006ba7d8;
  puStack_8 = &LAB_00634748;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar2 = FUN_005a86b0(param_1);
  *(undefined4 *)(iVar1 + 8) = uVar2;
  uVar3 = FUN_005a8690(param_1 + 4);
  *(uint *)(iVar1 + 0x838) = uVar3 & 0xffff;
  uVar3 = FUN_005a8690(param_1 + 6);
  *(uint *)(iVar1 + 0x474) = uVar3 & 0xffff;
  uVar3 = FUN_005a8690(param_1 + 8);
  *(uint *)(iVar1 + 0x478) = uVar3 & 0xffff;
  uVar2 = FUN_005a86b0(param_1 + 10);
  *(undefined4 *)(iVar1 + 0x454) = uVar2;
  ExceptionList = local_c;
  return 1;
}


