
void FUN_004a9470(int param_1)

{
  char cVar1;
  undefined1 uVar2;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062c148;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  cVar1 = FUN_005a8680(param_1);
  if (cVar1 == '\x01') {
    uVar2 = FUN_005a8680(param_1 + 1);
    FUN_004a6ff0(uVar2);
  }
  ExceptionList = local_c;
  return;
}


