
void FUN_004a4c00(undefined4 param_1)

{
  int iVar1;
  DWORD DVar2;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062be98;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  iVar1 = FUN_005a86b0(param_1);
  DVar2 = GetTickCount();
  FUN_005496a0(DVar2 - iVar1);
  ExceptionList = local_c;
  return;
}


