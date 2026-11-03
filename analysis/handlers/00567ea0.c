
/* WARNING: Removing unreachable block (ram,0x00568305) */

void __fastcall FUN_00567ea0(int param_1)

{
  undefined1 uVar1;
  byte bVar2;
  undefined4 uVar3;
  uint uVar4;
  uint uVar5;
  DWORD DVar6;
  undefined4 *puVar7;
  uint uVar8;
  int iVar9;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00637328;
  pvStack_c = ExceptionList;
  uVar8 = 0;
  local_4 = 0;
  ExceptionList = &pvStack_c;
  uVar3 = FUN_005a86b0();
  *(undefined4 *)(param_1 + 0x24) = uVar3;
  uVar4 = FUN_005a8680();
  *(uint *)(param_1 + 0x48) = uVar4 & 0xff;
  uVar1 = FUN_005a8680();
  *(undefined1 *)(param_1 + 0x28) = uVar1;
  uVar1 = FUN_005a8680();
  *(undefined1 *)(param_1 + 0x29) = uVar1;
  uVar4 = FUN_005a8690();
  uVar4 = uVar4 & 0xffff;
  FUN_00567ad0(uVar4);
  if (uVar4 != 0) {
    iVar9 = 0;
    do {
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      FUN_005a9ff0();
      uVar3 = FUN_005a86b0();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(undefined4 *)(*(int *)(param_1 + 100) + 0x1c + iVar9) = uVar3;
      uVar1 = FUN_005a8680();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(undefined1 *)(iVar9 + 0x20 + *(int *)(param_1 + 100)) = uVar1;
      uVar5 = FUN_005a8680();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(uint *)(*(int *)(param_1 + 100) + 0x24 + iVar9) = uVar5 & 0xff;
      uVar1 = FUN_005a8680();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(undefined1 *)(*(int *)(param_1 + 100) + 0x28 + iVar9) = uVar1;
      bVar2 = FUN_005a8680();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(uint *)(iVar9 + 0x2c + *(int *)(param_1 + 100)) = (uint)bVar2;
      bVar2 = FUN_005a8680();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(uint *)(*(int *)(param_1 + 100) + 0x30 + iVar9) = (uint)bVar2;
      uVar3 = FUN_005a86b0();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(undefined4 *)(iVar9 + 0x34 + *(int *)(param_1 + 100)) = uVar3;
      uVar5 = FUN_005a8690();
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      *(uint *)(*(int *)(param_1 + 100) + 0x38 + iVar9) = uVar5 & 0xffff;
      if ((*(int *)(param_1 + 100) == 0) ||
         ((uint)((*(int *)(param_1 + 0x68) - *(int *)(param_1 + 100)) / 0x58) <= uVar8)) {
        FUN_00609e03();
      }
      FUN_005aa060();
      uVar8 = uVar8 + 1;
      iVar9 = iVar9 + 0x58;
    } while ((int)uVar8 < (int)uVar4);
  }
  FUN_005aa060();
  puVar7 = (undefined4 *)(param_1 + 0x4c);
  iVar9 = 5;
  do {
    uVar3 = FUN_005a86b0();
    *puVar7 = uVar3;
    puVar7 = puVar7 + 1;
    iVar9 = iVar9 + -1;
  } while (iVar9 != 0);
  if (*(uint *)(param_1 + 0x68) < *(uint *)(param_1 + 100)) {
    FUN_00609e03();
  }
  if (*(uint *)(param_1 + 0x68) < *(uint *)(param_1 + 100)) {
    FUN_00609e03();
  }
  FUN_00567c10();
  DVar6 = GetTickCount();
  *(DWORD *)(param_1 + 0x70) = DVar6;
  ExceptionList = pvStack_c;
  return;
}


