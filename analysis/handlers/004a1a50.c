
void __thiscall FUN_004a1a50(int param_1,int param_2)

{
  uint uVar1;
  undefined4 uVar2;
  DWORD DVar3;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bb58;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8690(param_2);
  *(uint *)(param_1 + 0x29c34) = uVar1 & 0xffff;
  uVar2 = FUN_005a86b0(param_2 + 2);
  *(undefined4 *)(param_1 + 0x29c3c) = uVar2;
  uVar1 = FUN_005a8690(param_2 + 6);
  *(uint *)(param_1 + 0x29c38) = uVar1 & 0xffff;
  uVar2 = FUN_005a86b0(param_2 + 8);
  *(undefined4 *)(param_1 + 0x29c40) = uVar2;
  if ((*(int *)(param_1 + 0x29c34) == 0) && (*(int *)(param_1 + 0x29c38) == 0)) {
    *(undefined1 *)(param_1 + 0x29c2f) = 0;
  }
  else {
    *(undefined1 *)(param_1 + 0x29c2f) = 1;
  }
  DVar3 = GetTickCount();
  *(DWORD *)(param_1 + 0x29c30) = DVar3;
  ExceptionList = local_c;
  return;
}


