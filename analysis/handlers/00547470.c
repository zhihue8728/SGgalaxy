
undefined4 FUN_00547470(int param_1)

{
  uint uVar1;
  uint uVar2;
  int iVar3;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00634828;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a86b0(param_1);
  uVar2 = FUN_005a86b0(param_1 + 4);
  iVar3 = 0;
  do {
    if ((uVar1 & 1 << ((byte)iVar3 & 0x1f)) != 0) {
      FUN_0051ee00(iVar3);
    }
    iVar3 = iVar3 + 1;
  } while (iVar3 < 0x20);
  iVar3 = 0;
  do {
    if ((uVar2 & 1 << ((byte)iVar3 & 0x1f)) != 0) {
      FUN_0051ee00(iVar3 + 0x20);
    }
    iVar3 = iVar3 + 1;
  } while (iVar3 < 0x20);
  ExceptionList = local_c;
  return 1;
}


