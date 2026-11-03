
uint __fastcall FUN_00432fc0(int param_1)

{
  int iVar1;
  DWORD DVar2;
  uint uVar3;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_006268e0;
  local_c = ExceptionList;
  uVar3 = *(uint *)(param_1 + 0x2830);
  switch(uVar3) {
  case 0:
    *(int *)(param_1 + 0x282c) = *(int *)(param_1 + 0x282c) + -2;
    uVar3 = *(uint *)(param_1 + 0x282c);
    if ((int)uVar3 < 1) {
      *(undefined4 *)(param_1 + 0x282c) = 0;
      *(undefined4 *)(param_1 + 0x2830) = 1;
      return uVar3 & 0xffffff00;
    }
    break;
  case 1:
    ExceptionList = &local_c;
    (**(code **)(*(int *)(param_1 + -4) + 4))(1);
    FUN_004318e0();
    FUN_0043e5b0(1);
    uVar3 = FUN_005ecde0();
    *(undefined4 *)(param_1 + 0x2830) = 0xb;
    if (*(char *)(param_1 + 0x2834) != '\0') {
      *(undefined4 *)(param_1 + 0x2830) = 8;
      ExceptionList = local_c;
      return uVar3 & 0xffffff00;
    }
    break;
  case 2:
  case 5:
  case 7:
    break;
  case 3:
    *(int *)(param_1 + 0x282c) = *(int *)(param_1 + 0x282c) + 2;
    if (0x16 < *(int *)(param_1 + 0x282c)) {
      *(undefined4 *)(param_1 + 0x2830) = 4;
      return uVar3 & 0xffffff00;
    }
    break;
  case 4:
    if (*(char *)(param_1 + 0x2588) != '\0') {
      ExceptionList = &local_c;
      uVar3 = FUN_005450a0(10,0);
      ExceptionList = local_c;
      return uVar3 & 0xffffff00;
    }
    ExceptionList = &local_c;
    uVar3 = FUN_005450a0(2,0);
    ExceptionList = local_c;
    return uVar3 & 0xffffff00;
  case 6:
    if ((0 < *(int *)(DAT_006ba80c + 8)) && (*(char *)(DAT_006ba7c8 + 0x261d) != '\0')) {
      if (*(char *)(DAT_006ba840 + 0xadf) == '\0') {
        ExceptionList = &local_c;
        FUN_005a8f10(3);
        local_4 = 1;
        FUN_005a9110(param_1 + 400);
        FUN_005a9110(param_1 + 0x4a8);
        FUN_005aa1e0();
        FUN_004328f0(param_1 + 400);
        FUN_004329b0(param_1 + 0x4a8);
        local_4 = 0xffffffff;
        uVar3 = FUN_005a8f50();
        *(undefined4 *)(param_1 + 0x2830) = 7;
        ExceptionList = local_c;
        return uVar3 & 0xffffff00;
      }
      ExceptionList = &local_c;
      FUN_005a8f10(0xd4);
      local_4 = 0;
      if (*(uint *)(DAT_006ba840 + 0xaf8) < 0x10) {
        iVar1 = DAT_006ba840 + 0xae4;
      }
      else {
        iVar1 = *(int *)(DAT_006ba840 + 0xae4);
      }
      FUN_005a9110(iVar1);
      FUN_005aa1e0();
      FUN_004328f0(param_1 + 400);
      if (*(uint *)(DAT_006ba840 + 0xb14) < 0x10) {
        iVar1 = DAT_006ba840 + 0xb00;
      }
      else {
        iVar1 = *(int *)(DAT_006ba840 + 0xb00);
      }
      FUN_004329b0(iVar1);
      local_4 = 0xffffffff;
      uVar3 = FUN_005a8f50();
      *(undefined4 *)(param_1 + 0x2830) = 7;
      ExceptionList = local_c;
      return uVar3 & 0xffffff00;
    }
    ExceptionList = &local_c;
    DVar2 = GetTickCount();
    uVar3 = DVar2 - *(int *)(param_1 + 0x258c);
    if (3000 < uVar3) {
      FUN_00547820();
      FUN_005a8900();
      DVar2 = GetTickCount();
      *(DWORD *)(param_1 + 0x258c) = DVar2;
      ExceptionList = local_c;
      return DVar2 & 0xffffff00;
    }
    break;
  case 8:
    ExceptionList = &local_c;
    uVar3 = FUN_00432ec0();
    break;
  default:
    goto switchD_00432feb_default;
  }
switchD_00432feb_default:
  ExceptionList = local_c;
  return uVar3 & 0xffffff00;
}


