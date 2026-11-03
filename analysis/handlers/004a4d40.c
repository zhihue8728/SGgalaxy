
void __thiscall FUN_004a4d40(int param_1,undefined4 param_2)

{
  undefined2 uVar1;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062beb8;
  local_c = ExceptionList;
  if (*(char *)(param_1 + 0x29bdc) != '\0') {
    local_4 = 0;
    ExceptionList = &local_c;
    uVar1 = FUN_005a8690(param_2);
    FUN_0049f5d0(uVar1);
  }
  ExceptionList = local_c;
  return;
}


