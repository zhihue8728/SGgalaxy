
undefined4 __thiscall FUN_00547540(int param_1,int param_2)

{
  char cVar1;
  uint uVar2;
  int iVar3;
  uint uVar4;
  int iVar5;
  undefined1 local_54 [72];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00634848;
  local_c = ExceptionList;
  if (DAT_006ba7cc == 0) {
    return 0;
  }
  local_4 = 0;
  ExceptionList = &local_c;
  uVar2 = FUN_005a8680(param_2);
  switch((uVar2 & 0xff) - 1) {
  case 0:
    uVar2 = 0;
    iVar3 = DAT_006ba7d4;
    if (*(int *)(DAT_006ba7d4 + 0x50) != 0) {
      do {
        if ((((*(int *)(iVar3 + 0x58) != 0) && (-1 < (int)uVar2)) &&
            ((int)uVar2 < *(int *)(iVar3 + 0x50))) &&
           (*(int *)(*(int *)(iVar3 + 0x58) + uVar2 * 4) != 0)) {
          FUN_004c4c90();
          iVar3 = DAT_006ba7d4;
        }
        uVar2 = uVar2 + 1;
      } while (uVar2 < *(uint *)(iVar3 + 0x50));
    }
    uVar2 = FUN_005a86b0(param_2 + 1);
    iVar3 = FUN_005a86b0(param_2 + 5);
    uVar4 = FUN_004255c0();
    uVar4 = uVar4 / 10;
    if (uVar4 < uVar2 / 10) {
      FUN_005451a0(local_54);
      ExceptionList = local_c;
      return 0;
    }
    iVar5 = uVar4 - uVar2 / 10;
    if ((*(int *)(param_1 + 0x2598) < iVar5) || (iVar5 < *(int *)(param_1 + 0x2598) / 5)) {
      *(int *)(param_1 + 0x2598) = iVar5;
    }
    if (iVar5 < *(int *)(param_1 + 0x259c)) {
      *(int *)(param_1 + 0x259c) = iVar5;
      *(uint *)(param_1 + 0x1c54) = uVar4 - iVar3;
    }
    *(int *)(param_1 + 0x2590) = *(int *)(param_1 + 0x2590) + 1;
    FUN_00574530(*(undefined4 *)(param_1 + 0x2590));
    if (0 < *(int *)(param_1 + 0x2590)) {
      FUN_005471c0();
      ExceptionList = local_c;
      return 1;
    }
    goto LAB_005475fb;
  case 3:
    cVar1 = FUN_005a8680(param_2 + 1);
    iVar3 = FUN_005a86b0(param_2 + 2);
    if ((cVar1 != '\0') && (iVar3 != 0)) {
      uVar2 = FUN_004255c0();
      *(uint *)(param_1 + 0x1c54) = uVar2 / 10 - iVar3;
    }
    FUN_004aebb0(iVar3,cVar1);
    break;
  case 4:
    *(undefined4 *)(param_1 + 0x2590) = 0;
    FUN_00544f10();
    FUN_00574520(1);
    FUN_00574530(0);
LAB_005475fb:
    FUN_00547130();
    break;
  case 5:
    iVar3 = FUN_005a86b0(param_2 + 1);
    thunk_FUN_004a9890(iVar3);
    if (iVar3 != 0) {
      uVar2 = FUN_004255c0();
      *(uint *)(param_1 + 0x1c54) = uVar2 / 10 - iVar3;
    }
  }
  ExceptionList = local_c;
  return 1;
}


