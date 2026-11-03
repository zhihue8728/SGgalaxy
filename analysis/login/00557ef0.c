
void __thiscall FUN_00557ef0(int param_1,char param_2)

{
  int iVar1;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_00635de0;
  local_c = ExceptionList;
  if (param_2 == '\0') {
    ExceptionList = &local_c;
    FUN_005a8f10(2);
    local_4 = 1;
    if (*(uint *)(param_1 + 0x28870) < 0x10) {
      iVar1 = param_1 + 0x2885c;
    }
    else {
      iVar1 = *(int *)(param_1 + 0x2885c);
    }
    FUN_005a9110(iVar1);
    if (*(uint *)(param_1 + 0x2888c) < 0x10) {
      iVar1 = param_1 + 0x28878;
    }
    else {
      iVar1 = *(int *)(param_1 + 0x28878);
    }
    FUN_005a9110(iVar1);
    if (*(uint *)(param_1 + 0x288a8) < 0x10) {
      param_1 = param_1 + 0x28894;
    }
    else {
      param_1 = *(int *)(param_1 + 0x28894);
    }
    FUN_005a9110(param_1);
    FUN_005aa1e0();
  }
  else {
    ExceptionList = &local_c;
    FUN_005a8f10(2);
    local_4 = 0;
    if (*(uint *)(param_1 + 0x28870) < 0x10) {
      iVar1 = param_1 + 0x2885c;
    }
    else {
      iVar1 = *(int *)(param_1 + 0x2885c);
    }
    FUN_005a9110(iVar1);
    if (*(uint *)(param_1 + 0x2888c) < 0x10) {
      iVar1 = param_1 + 0x28878;
    }
    else {
      iVar1 = *(int *)(param_1 + 0x28878);
    }
    FUN_005a9110(iVar1);
    if (*(uint *)(param_1 + 0x288a8) < 0x10) {
      param_1 = param_1 + 0x28894;
    }
    else {
      param_1 = *(int *)(param_1 + 0x28894);
    }
    FUN_005a9110(param_1);
    FUN_005aa1e0();
  }
  local_4 = 0xffffffff;
  FUN_005a8f50();
  ExceptionList = local_c;
  return;
}


