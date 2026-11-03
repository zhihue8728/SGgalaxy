
void __thiscall FUN_004a6d70(int param_1,int param_2)

{
  undefined4 uVar1;
  undefined4 uVar2;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062c0a8;
  local_c = ExceptionList;
  if (*(char *)(param_1 + 0x29bdc) != '\0') {
    local_4 = 0;
    ExceptionList = &local_c;
    uVar1 = FUN_005a86b0(param_2);
    uVar2 = FUN_005a86b0(param_2 + 4);
    FUN_004a4fa0(uVar1,uVar2);
    FUN_004f08e0();
    FUN_0051d1f0(0x41);
  }
  ExceptionList = local_c;
  return;
}


