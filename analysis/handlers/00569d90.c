
void __thiscall FUN_00569d90(int param_1,byte *param_2,undefined4 param_3)

{
  undefined **local_20;
  undefined4 local_1c;
  undefined4 local_18;
  uint local_14;
  byte *local_10;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_00637508;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  FUN_00568540(*(undefined4 *)(*(int *)(param_1 + 0xc) + 4));
  *(int *)(*(int *)(param_1 + 0xc) + 4) = *(int *)(param_1 + 0xc);
  *(undefined4 *)(param_1 + 0x10) = 0;
  *(undefined4 *)*(undefined4 *)(param_1 + 0xc) = *(undefined4 *)(param_1 + 0xc);
  *(int *)(*(int *)(param_1 + 0xc) + 8) = *(int *)(param_1 + 0xc);
  local_10 = param_2;
  local_14 = (uint)*param_2;
  local_1c = 0;
  local_18 = param_3;
  local_20 = CReceivedPacketEx::vftable;
  local_4 = 0;
  FUN_00569490(&local_20);
  FUN_00569830(&local_20);
  FUN_00565500();
  ExceptionList = local_c;
  return;
}


