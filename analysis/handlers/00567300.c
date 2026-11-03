
void __thiscall FUN_00567300(int param_1,int param_2,undefined4 param_3)

{
  uint uVar1;
  undefined4 uVar2;
  undefined4 *puVar3;
  int iVar4;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00637208;
  local_c = ExceptionList;
  iVar4 = 2;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8690(param_2);
  FUN_00565850(*(undefined4 *)(*(int *)(param_1 + 0x18) + 4));
  *(int *)(*(int *)(param_1 + 0x18) + 4) = *(int *)(param_1 + 0x18);
  *(undefined4 *)(param_1 + 0x1c) = 0;
  *(undefined4 *)*(undefined4 *)(param_1 + 0x18) = *(undefined4 *)(param_1 + 0x18);
  *(int *)(*(int *)(param_1 + 0x18) + 8) = *(int *)(param_1 + 0x18);
  for (uVar1 = uVar1 & 0xffff; uVar1 != 0; uVar1 = uVar1 - 1) {
    param_3 = FUN_005a86b0(param_2 + iVar4);
    iVar4 = iVar4 + 8;
    uVar2 = FUN_005a86b0(param_2 + -4 + iVar4);
    puVar3 = (undefined4 *)FUN_004667d0(&param_3);
    *puVar3 = uVar2;
  }
  ExceptionList = local_c;
  return;
}


