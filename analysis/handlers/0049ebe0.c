
void __thiscall FUN_0049ebe0(int param_1,undefined4 param_2)

{
  uint uVar1;
  undefined1 local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062b90b;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  FUN_00574bd0();
  uVar1 = FUN_005a8680(param_2);
  for (uVar1 = uVar1 & 0xff; uVar1 != 0; uVar1 = uVar1 - 1) {
    FUN_005a8da0(local_10c,0x100,"fldltu");
    FUN_00574c30(local_10c);
  }
  if (*(char *)(*(int *)(param_1 + 0x29b1c) + 0x155) != '\0') {
    FUN_005ecf00(1);
  }
  ExceptionList = local_c;
  return;
}


