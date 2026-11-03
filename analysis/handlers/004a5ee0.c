
void FUN_004a5ee0(int param_1,int param_2)

{
  char cVar1;
  undefined4 uVar2;
  int iVar3;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bfb8;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar2 = FUN_005a86b0(param_1);
  iVar3 = FUN_005ca290(uVar2);
  if (iVar3 != 0) {
    cVar1 = FUN_004dcbf0(param_1 + 4,param_2 + -4);
    if (cVar1 == '\0') {
      FUN_004a5a00();
    }
  }
  ExceptionList = local_c;
  return;
}


