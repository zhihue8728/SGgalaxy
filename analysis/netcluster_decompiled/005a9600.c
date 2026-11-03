// xrefs to FUN_005a9600: 00634b09(00634b00) 00634d6c(00634d60) 005a9fd3(005a9fd0) 

void __fastcall FUN_005a9600(undefined4 *param_1)

{
  undefined4 uVar1;
  void *pvStack_14;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0063bbba;
  pvStack_c = ExceptionList;
  ExceptionList = &pvStack_c;
  *param_1 = CSocket::vftable;
  param_1[1] = CSocket::vftable;
  local_4 = 2;
  uVar1 = FUN_00551ce0(param_1[6]);
  param_1[6] = uVar1;
  uVar1 = FUN_00551ce0(param_1[5]);
  param_1[5] = uVar1;
  if (param_1[2] != -1) {
    FUN_005a8a50();
  }
  FUN_005a9550();
  FUN_005453c0();
  FUN_005636a0();
  pvStack_c = (void *)((uint)pvStack_c & 0xffffff00);
  FUN_0055f0c0();
  *param_1 = CSingletonBase<CSocket>::vftable;
  DAT_00c32cc0 = 0;
  ExceptionList = pvStack_14;
  return;
}


