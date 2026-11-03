
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __thiscall FUN_004aa340(int param_1,byte *param_2,undefined4 param_3)

{
  undefined4 ***pppuVar1;
  int iVar2;
  undefined4 local_2a80;
  undefined4 local_2a7c;
  uint local_2a78;
  byte *local_2a74;
  undefined1 local_2a70 [4];
  undefined4 **local_2a6c [4];
  undefined4 local_2a5c;
  uint local_2a58;
  undefined4 uStack_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined1 local_4;
  undefined3 uStack_3;
  
  puStack_8 = &LAB_0062c221;
  pvStack_c = ExceptionList;
  uStack_10 = 0x4aa35f;
  iVar2 = 0;
  local_2a58 = 0xf;
  local_2a5c = 0;
  local_2a6c[0] = (undefined4 **)((uint)local_2a6c[0] & 0xffffff00);
  local_2a74 = param_2;
  local_2a78 = (uint)*param_2;
  local_2a80 = 0;
  local_2a7c = param_3;
  local_4 = 1;
  uStack_3 = 0;
  ExceptionList = &pvStack_c;
  FUN_005a9ff0(local_2a70,param_2,&local_2a80);
  FUN_0055e8f0();
  local_4 = 2;
  if (param_1 != 0) {
    iVar2 = param_1 + 4;
  }
  pppuVar1 = (undefined4 ***)local_2a6c[0];
  if (local_2a58 < 0x10) {
    pppuVar1 = local_2a6c;
  }
  FUN_0055e180(iVar2,1,pppuVar1);
  _local_4 = CONCAT31(uStack_3,1);
  FUN_0055e350();
  if (0xf < local_2a58) {
                    /* WARNING: Subroutine does not return */
    _free(local_2a6c[0]);
  }
  ExceptionList = pvStack_c;
  return;
}


