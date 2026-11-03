
void FUN_005473e0(byte *param_1,undefined4 param_2)

{
  undefined4 uVar1;
  void *_Memory;
  undefined4 local_1c;
  undefined4 local_18;
  uint local_14;
  byte *local_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00634808;
  pvStack_c = ExceptionList;
  local_10 = param_1;
  local_14 = (uint)*param_1;
  local_18 = param_2;
  local_4 = 0;
  local_1c = 4;
  ExceptionList = &pvStack_c;
  uVar1 = FUN_005a86b0(param_1);
  _Memory = (void *)thunk_FUN_006094fc(uVar1);
  FUN_005a88c0(_Memory,uVar1,local_10,&local_1c);
                    /* WARNING: Subroutine does not return */
  _free(_Memory);
}


