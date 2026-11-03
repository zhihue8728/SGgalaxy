
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

undefined4 __thiscall FUN_00548c50(int param_1,byte *param_2,undefined4 param_3)

{
  byte *pbVar1;
  byte bVar2;
  char cVar3;
  uint uVar4;
  int iVar5;
  undefined4 uVar6;
  uint uVar7;
  undefined4 local_2f5c;
  undefined **local_2f58;
  int local_2f54;
  undefined4 local_2f50;
  uint local_2f4c;
  byte *local_2f48;
  undefined **local_2f44;
  _OSVERSIONINFOA local_2f30;
  undefined1 local_2e9c [11916];
  undefined4 uStack_10;
  void *local_c;
  undefined1 *puStack_8;
  uint local_4;
  
  puStack_8 = &LAB_006349e1;
  local_c = ExceptionList;
  uStack_10 = 0x548c6f;
  local_2f48 = param_2;
  local_2f4c = (uint)*param_2;
  local_2f50 = param_3;
  local_2f58 = CReceivedPacketEx::vftable;
  local_4 = 0;
  local_2f54 = 4;
  ExceptionList = &local_c;
  local_2f5c = FUN_005a86b0(param_2);
  pbVar1 = local_2f48 + local_2f54;
  local_2f54 = local_2f54 + 2;
  uVar4 = FUN_005a8690(pbVar1);
  pbVar1 = local_2f48 + local_2f54;
  local_2f54 = local_2f54 + 1;
  bVar2 = FUN_005a8680(pbVar1);
  uVar7 = (uint)bVar2;
  FUN_005a88c0(local_2e9c,uVar7,local_2f48,&local_2f54);
  local_2e9c[uVar7] = 0;
  FUN_005a8a50();
  Sleep(1000);
  cVar3 = FUN_005a97c0(*(undefined4 *)(param_1 + 0xc00),&local_2f5c,uVar4 & 0xffff);
  if (cVar3 == '\0') {
    if (DAT_00d67eb0 != 0) {
      *(undefined1 *)(DAT_00d67eb0 + 0x300) = 0;
    }
    FUN_0058c730();
    local_4 = CONCAT31(local_4._1_3_,1);
    if (*(uint *)(param_1 + 0x20) < 0x10) {
      iVar5 = param_1 + 0xc;
    }
    else {
      iVar5 = *(int *)(param_1 + 0xc);
    }
    FUN_0058c9f0(*(undefined4 *)(param_1 + 0xc0c),iVar5,0xff,0xff,0xff,0x10);
    *(undefined1 *)(DAT_006ba840 + 0xc5d) = 0;
    if (*(int *)(param_1 + 0x184) == 2) {
      FUN_0054caf0(2);
    }
    local_4 = local_4 & 0xffffff00;
    FUN_0058c7b0();
    uVar6 = 0;
  }
  else {
    FUN_005a8f10(5);
    local_2f44 = CSendPacketEx::vftable;
    local_4 = CONCAT31(local_4._1_3_,2);
    FUN_005a91f0(local_2e9c,uVar7);
    FUN_005a8fc0(1);
    FUN_005a9070(*(undefined4 *)(DAT_006ba840 + 0x4c4));
    local_2f30.dwOSVersionInfoSize = 0x94;
    GetVersionExA(&local_2f30);
    FUN_005a9070((uint)CONCAT21(CONCAT11((undefined1)local_2f30.dwPlatformId,
                                         (undefined1)local_2f30.dwMajorVersion),
                                (undefined1)local_2f30.dwMinorVersion));
    FUN_005aa1e0();
    if ((*(char *)(DAT_006ba840 + 0xc5d) == '\0') && (bVar2 == 0)) {
      FUN_005a88f0();
      *(undefined1 *)(DAT_006ba840 + 0xc5d) = 1;
      *(undefined4 *)(DAT_006ba840 + 0x4c0) = local_2f5c;
      *(uint *)(DAT_006ba840 + 0x4bc) = uVar4 & 0xffff;
      if (DAT_00d67eb4 != 0) {
        FUN_0059b760();
      }
    }
    else {
      *(undefined1 *)(DAT_006ba840 + 0xc5c) = 1;
    }
    local_4 = local_4 & 0xffffff00;
    FUN_005a8f50();
    uVar6 = 1;
  }
  ExceptionList = local_c;
  return uVar6;
}


