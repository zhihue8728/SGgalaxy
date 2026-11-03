
void FUN_004a5d20(undefined4 param_1)

{
  char cVar1;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bf58;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  cVar1 = FUN_005a8680(param_1);
  if (cVar1 == '\0') {
    FUN_004a4450(2);
  }
  ExceptionList = local_c;
  return;
}


