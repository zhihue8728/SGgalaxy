
void FUN_004a27c0(int param_1)

{
  uint uVar1;
  undefined4 uVar2;
  int iVar3;
  int iVar4;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bcd8;
  local_c = ExceptionList;
  iVar4 = 2;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8690(param_1);
  for (uVar1 = uVar1 & 0xffff; uVar1 != 0; uVar1 = uVar1 - 1) {
    iVar4 = iVar4 + 4;
    uVar2 = FUN_005a86b0(param_1 + -4 + iVar4);
    iVar3 = FUN_005ca290(uVar2);
    if (iVar3 != 0) {
      thunk_FUN_004d9e30();
    }
  }
  ExceptionList = local_c;
  return;
}


