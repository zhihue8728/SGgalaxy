
uint __fastcall FUN_0059dd40(int param_1)

{
  uint uVar1;
  int iVar2;
  DWORD DVar3;
  _OSVERSIONINFOA local_a0;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063aa06;
  local_c = ExceptionList;
  if (*(int *)(param_1 + 0x377c) == 0) {
    ExceptionList = &local_c;
    FUN_00599d40();
    uVar1 = FUN_0043e5b0(1);
    *(undefined4 *)(param_1 + 0x377c) = 1;
    ExceptionList = local_c;
    return uVar1 & 0xffffff00;
  }
  uVar1 = *(int *)(param_1 + 0x377c) - 2;
  if (uVar1 == 0) {
    if ((*(int *)(DAT_006ba80c + 8) < 1) || (*(char *)(DAT_006ba7c8 + 0x261d) == '\0')) {
      ExceptionList = &local_c;
      DVar3 = GetTickCount();
      uVar1 = DVar3 - *(int *)(param_1 + 0x3778);
      if (3000 < uVar1) {
        FUN_00547820();
        FUN_005a8900();
        uVar1 = GetTickCount();
        *(uint *)(param_1 + 0x3778) = uVar1;
      }
    }
    else {
      if (*(char *)(DAT_006ba840 + 0xadf) == '\0') {
        ExceptionList = &local_c;
        FUN_005a8f10(3);
        local_4 = 1;
        FUN_005a9110(param_1 + 0x2f4);
        FUN_005a9110(param_1 + 0x60c);
        FUN_005a8fc0(1);
        FUN_005a9070(*(undefined4 *)(DAT_006ba840 + 0x4c4));
        local_a0.dwOSVersionInfoSize = 0x94;
        GetVersionExA(&local_a0);
        FUN_005a9070((uint)CONCAT21(CONCAT11((undefined1)local_a0.dwPlatformId,
                                             (undefined1)local_a0.dwMajorVersion),
                                    (undefined1)local_a0.dwMinorVersion));
        FUN_005aa1e0();
        FUN_004328f0(param_1 + 0x2f4);
        FUN_004329b0(param_1 + 0x60c);
        local_4 = 0xffffffff;
        uVar1 = FUN_005a8f50();
      }
      else {
        ExceptionList = &local_c;
        FUN_005a8f10(0xd4);
        local_4 = 0;
        if (*(uint *)(DAT_006ba840 + 0xaf8) < 0x10) {
          iVar2 = DAT_006ba840 + 0xae4;
        }
        else {
          iVar2 = *(int *)(DAT_006ba840 + 0xae4);
        }
        FUN_005a9110(iVar2);
        FUN_005aa1e0();
        local_4 = 0xffffffff;
        uVar1 = FUN_005a8f50();
      }
      *(undefined4 *)(param_1 + 0x377c) = 3;
    }
  }
  ExceptionList = local_c;
  return uVar1 & 0xffffff00;
}


