
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __fastcall FUN_004b0040(int param_1)

{
  byte bVar1;
  undefined1 uVar2;
  uint uVar3;
  undefined4 uVar4;
  uint uVar5;
  int iVar6;
  uint uVar7;
  uint *puVar8;
  undefined4 *puVar9;
  undefined4 *puVar10;
  undefined4 auStack_1a44 [1012];
  uint local_a74;
  int local_a6c;
  int local_a68;
  int iStack_a5c;
  int iStack_a58;
  uint local_a50;
  uint local_a4c;
  uint local_a48;
  undefined4 local_a44;
  uint local_a3c [59];
  undefined4 uStack_950;
  undefined4 uStack_94c;
  undefined4 uStack_948;
  undefined4 uStack_944;
  undefined4 uStack_940;
  uint uStack_93c;
  uint uStack_938;
  uint uStack_934;
  uint uStack_930;
  uint uStack_92c;
  uint uStack_928;
  undefined4 uStack_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062c526;
  pvStack_c = ExceptionList;
  uStack_10 = 0x4b005f;
  ExceptionList = &pvStack_c;
  *(undefined1 *)(param_1 + 0xb1e0) = 1;
  *(undefined1 *)(param_1 + 0x29c2f) = 0;
  FUN_004a4850();
  FUN_0040dfd0();
  iVar6 = 0;
  local_4 = 1;
  local_a74 = FUN_005a8680();
  local_a74 = local_a74 & 0xff;
  uVar3 = FUN_005a8680();
  FUN_004aef70();
  uVar7 = 0;
  if ((uVar3 & 0xff) != 0) {
    do {
      uVar4 = FUN_005a86b0();
      if ((local_a6c == 0) || ((uint)((local_a68 - local_a6c) / 0xc) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined4 *)(local_a6c + iVar6) = uVar4;
      uVar5 = FUN_005a8690();
      if ((local_a6c == 0) || ((uint)((local_a68 - local_a6c) / 0xc) <= uVar7)) {
        FUN_00609e03();
      }
      *(uint *)(local_a6c + 4 + iVar6) = uVar5 & 0xffff;
      uVar5 = FUN_005a8690();
      if ((local_a6c == 0) || ((uint)((local_a68 - local_a6c) / 0xc) <= uVar7)) {
        FUN_00609e03();
      }
      *(uint *)(local_a6c + 8 + iVar6) = uVar5 & 0xffff;
      uVar7 = uVar7 + 1;
      iVar6 = iVar6 + 0xc;
    } while ((int)uVar7 < (int)(uVar3 & 0xff));
  }
  local_a50 = FUN_005a8690();
  local_a50 = local_a50 & 0xffff;
  local_a4c = FUN_005a8690();
  local_a4c = local_a4c & 0xffff;
  local_a48 = FUN_005a8690();
  local_a48 = local_a48 & 0xffff;
  local_a44 = FUN_005a86b0();
  puVar8 = local_a3c;
  iVar6 = 4;
  do {
    uVar3 = FUN_005a8680();
    puVar8[-1] = uVar3 & 0xff;
    uVar3 = FUN_005a8680();
    *puVar8 = uVar3 & 0xff;
    uVar3 = FUN_005a86b0();
    puVar8[1] = uVar3;
    uVar3 = FUN_005a86b0();
    puVar8[2] = uVar3;
    uVar3 = FUN_005a86b0();
    puVar8[3] = uVar3;
    uVar3 = FUN_005a86b0();
    puVar8[4] = uVar3;
    uVar3 = FUN_005a8680();
    puVar8[5] = uVar3 & 0xff;
    FUN_005a9ff0();
    puVar8 = puVar8 + 0xf;
    iVar6 = iVar6 + -1;
  } while (iVar6 != 0);
  uStack_950 = FUN_005a86b0();
  uStack_94c = FUN_005a86b0();
  uStack_948 = FUN_005a86b0();
  uStack_944 = FUN_005a86b0();
  uStack_940 = FUN_005a86b0();
  uStack_93c = FUN_005a8690();
  uStack_93c = uStack_93c & 0xffff;
  uStack_938 = FUN_005a8690();
  uStack_938 = uStack_938 & 0xffff;
  uStack_934 = FUN_005a8690();
  uStack_934 = uStack_934 & 0xffff;
  uStack_930 = FUN_005a8690();
  uStack_930 = uStack_930 & 0xffff;
  uStack_92c = FUN_005a8690();
  uStack_92c = uStack_92c & 0xffff;
  uStack_928 = FUN_005a8690();
  uStack_928 = uStack_928 & 0xffff;
  uVar3 = FUN_005a8680();
  uVar3 = uVar3 & 0xff;
  _memset(auStack_1a44,0,0x34);
  puVar9 = auStack_1a44;
  puVar10 = (undefined4 *)&stack0xffffe55c;
  for (iVar6 = 0xd; iVar6 != 0; iVar6 = iVar6 + -1) {
    *puVar10 = *puVar9;
    puVar9 = puVar9 + 1;
    puVar10 = puVar10 + 1;
  }
  FUN_004af050(uVar3);
  uVar7 = 0;
  if (uVar3 != 0) {
    iVar6 = 0;
    do {
      uVar4 = FUN_005a86b0();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined4 *)(iVar6 + iStack_a5c) = uVar4;
      bVar1 = FUN_005a8680();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(uint *)(iVar6 + 4 + iStack_a5c) = (uint)bVar1;
      bVar1 = FUN_005a8680();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(uint *)(iVar6 + 8 + iStack_a5c) = (uint)bVar1;
      uVar4 = FUN_005a86b0();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined4 *)(iVar6 + 0xc + iStack_a5c) = uVar4;
      uVar4 = FUN_005a86b0();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined4 *)(iVar6 + 0x10 + iStack_a5c) = uVar4;
      uVar4 = FUN_005a86b0();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined4 *)(iVar6 + 0x14 + iStack_a5c) = uVar4;
      uVar4 = FUN_005a86b0();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined4 *)(iVar6 + 0x18 + iStack_a5c) = uVar4;
      uVar4 = FUN_005a86b0();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined4 *)(iVar6 + 0x1c + iStack_a5c) = uVar4;
      uVar5 = FUN_005a8690();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(uint *)(iVar6 + 0x20 + iStack_a5c) = uVar5 & 0xffff;
      bVar1 = FUN_005a8680();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(uint *)(iVar6 + 0x24 + iStack_a5c) = (uint)bVar1;
      bVar1 = FUN_005a8680();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(uint *)(iVar6 + 0x28 + iStack_a5c) = (uint)bVar1;
      uVar2 = FUN_005a8680();
      if ((iStack_a5c == 0) || ((uint)((iStack_a58 - iStack_a5c) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      *(undefined1 *)(iVar6 + 0x2c + iStack_a5c) = uVar2;
      uVar7 = uVar7 + 1;
      iVar6 = iVar6 + 0x34;
    } while ((int)uVar7 < (int)uVar3);
  }
  FUN_0040a430();
  FUN_0051d1f0();
  local_4 = 0xffffffff;
  FUN_0040dac0();
  ExceptionList = pvStack_c;
  return;
}


