// xrefs to FUN_005a9e80: 0054bb2d(0054baa0) 

undefined4 * __fastcall FUN_005a9e80(undefined4 *param_1)

{
  undefined4 *puVar1;
  void *_Memory;
  undefined4 uVar2;
  char *pcVar3;
  char *pcVar4;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0063bc2e;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  *param_1 = CSingletonBase<CSocket>::vftable;
  local_4 = 0;
  DAT_00c32cc0 = param_1;
  FUN_0055f0b0();
  param_1[1] = CSocket::vftable;
  local_4._0_1_ = 1;
  *param_1 = CSocket::vftable;
  uVar2 = FUN_005a94f0();
  param_1[10] = uVar2;
  param_1[0xb] = 0;
  local_4 = CONCAT31(local_4._1_3_,2);
  DAT_00d69268 = GetTickCount();
  pcVar4 = s_NexonInc__006b6908;
  do {
    pcVar3 = pcVar4;
    pcVar4 = pcVar3 + 1;
  } while (*pcVar3 != '\0');
  pcVar4 = pcVar3 + -0x6b6908;
  DAT_00d6926c = pcVar4;
  if (0 < (int)pcVar4) {
    _memcpy(&DAT_00d69274,s_NexonInc__006b6908,(size_t)pcVar4);
    _memcpy(pcVar3 + 0x6b296c,s_NexonInc__006b6908,(size_t)pcVar4);
    _memcpy(&DAT_00d69274 + (int)pcVar4 * 2,s_NexonInc__006b6908,(size_t)pcVar4);
    _memcpy(&DAT_00d69274 + (int)pcVar4 * 3,s_NexonInc__006b6908,(size_t)pcVar4);
  }
  param_1[2] = 0xffffffff;
  uVar2 = FUN_00551d70(0x50000);
  param_1[5] = uVar2;
  uVar2 = FUN_00551d70(0x50000);
  param_1[6] = uVar2;
  param_1[7] = 0;
  puVar1 = (undefined4 *)param_1[10];
  _Memory = (void *)*puVar1;
  *puVar1 = puVar1;
  *(undefined4 *)(param_1[10] + 4) = param_1[10];
  param_1[0xb] = 0;
  if (_Memory != (void *)param_1[10]) {
                    /* WARNING: Subroutine does not return */
    _free(_Memory);
  }
  param_1[0xc] = 0;
  ExceptionList = local_c;
  return param_1;
}


