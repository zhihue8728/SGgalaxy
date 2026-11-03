
undefined4 FUN_00547b00(void)

{
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_006348e8;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  FUN_005a8f10(0xc);
  local_4 = 0;
  FUN_005aa1e0(CSendPacketEx::vftable);
  local_4 = 0xffffffff;
  FUN_005a8f50();
  ExceptionList = local_c;
  return 1;
}


