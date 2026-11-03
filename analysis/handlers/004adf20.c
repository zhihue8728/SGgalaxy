
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __thiscall FUN_004adf20(int param_1,int param_2,int param_3)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  uint uVar5;
  bool bVar6;
  char cVar7;
  char cVar8;
  undefined1 uVar9;
  char cVar10;
  undefined2 uVar11;
  undefined2 uVar12;
  undefined2 uVar13;
  uint uVar14;
  undefined4 uVar15;
  uint uVar16;
  undefined4 uVar17;
  int iVar18;
  int iVar19;
  int iVar20;
  int iVar21;
  int iVar22;
  char *pcVar23;
  undefined4 uVar24;
  undefined4 uVar25;
  undefined4 uVar26;
  undefined4 uVar27;
  char *pcVar28;
  uint uVar29;
  uint uVar30;
  undefined4 uVar31;
  undefined4 uVar32;
  undefined4 uVar33;
  int *local_2bc8;
  char local_2bc3;
  uint local_2bbc;
  undefined1 auStack_2b78 [11112];
  undefined4 uStack_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  int local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062c486;
  pvStack_c = ExceptionList;
  uStack_10 = 0x4adf3f;
  ExceptionList = &pvStack_c;
  FUN_0049e2d0();
  FUN_005c5fc0();
  FUN_0057d410();
  FUN_0054ecb0();
  if (*(int *)(DAT_00c30bc4 + 0x10) == 0) {
    FUN_00565530(0);
  }
  *(undefined4 *)(param_1 + 0x29be4) = 0;
  DAT_00c32cd8 = 0;
  DAT_00c32ce8 = 0;
  local_4 = 0;
  if (*(int *)(DAT_006ba7c8 + 0xc0c) == param_1 + 4) {
    FUN_005ecde0();
  }
  FUN_00425740();
  bVar6 = false;
  local_2bc3 = '\0';
  *(undefined1 *)(param_1 + 0xb1e1) = 0;
  uVar14 = FUN_005a86b0(param_2);
  cVar7 = FUN_005a8680(param_2 + 4);
  uVar15 = FUN_005a86b0(param_2 + 5);
  *(undefined4 *)(param_1 + 0x29bd4) = uVar15;
  cVar8 = FUN_005a8680(param_2 + 9);
  iVar22 = *(int *)(param_1 + 0x29bf0);
  uVar5 = *(uint *)(param_1 + 0x29bd8);
  cVar1 = *(char *)(param_1 + 0x29bdc);
  uVar9 = FUN_005a8680(param_2 + 10);
  *(undefined1 *)(param_1 + 0x29bdd) = uVar9;
  uVar15 = FUN_005a86b0(param_2 + 0xb);
  *(undefined4 *)(param_1 + 0x29be8) = uVar15;
  uVar15 = FUN_005a86b0(param_2 + 0xf);
  *(undefined4 *)(param_1 + 0x29bec) = uVar15;
  uVar16 = FUN_005a8680(param_2 + 0x13);
  *(uint *)(param_1 + 0x29bf0) = uVar16 & 0xff;
  uVar9 = FUN_005a8680(param_2 + 0x14);
  iVar20 = 0x16;
  local_2bbc = FUN_005a8680(param_2 + 0x15);
  local_2bbc = local_2bbc & 0xff;
  if (*(uint *)(param_1 + 0x29bd8) != uVar14) {
    *(uint *)(param_1 + 0x380) = *(uint *)(param_1 + 0x29bd8);
  }
  FUN_00531bd0(uVar14);
  cVar10 = FUN_0049e340(uVar14);
  if (cVar10 == '\0') {
    FUN_004abcf0(param_2,param_3,"S_FIELD",0);
  }
  FUN_00548510();
  uVar15 = FUN_004ee140();
  FUN_0047e440(uVar15,uVar14,cVar8);
  if (((*(uint *)(param_1 + 0x29bd8) != 0xffffffff) &&
      ((uVar14 / 100000) % 1000 != (*(uint *)(param_1 + 0x29bd8) / 100000) % 1000)) &&
     (uVar14 < 100000000)) {
    local_2bc3 = '\x01';
  }
  if (((uVar14 != *(uint *)(param_1 + 0x29bd8)) || (cVar8 != *(char *)(param_1 + 0x29bdc))) ||
     (cVar7 != *(char *)(*(int *)(param_1 + 0x8564) + 0x3f8))) {
    FUN_004a5370();
    FUN_00544f50(1);
    FUN_00545370();
    FUN_00509c50();
    FUN_00509c50();
    FUN_005bf1f0();
    *(undefined4 *)(param_1 + 0x378) = 0;
    *(undefined4 *)(param_1 + 0x37c) = 0xffffffff;
    *(undefined1 *)(param_1 + 0x29bf4) = 0;
    FUN_0049f510(cVar8);
    bVar6 = true;
    FUN_005b76b0();
    if (*(int *)(DAT_006ba7c8 + 0x1c58) == 1) {
      if (uVar14 + 0xe8287c00 < 100000000) {
        FUN_0056d260(uVar14);
      }
      else if ((int)(((ulonglong)uVar14 / 10000) % 10) == 9) {
        FUN_0056e0c0(uVar14);
      }
      else {
        FUN_0056e280(uVar14,cVar7 != '\0');
      }
    }
    if (*(int *)(DAT_006ba7c8 + 0x1c58) == 2) {
      FUN_0049ae80();
    }
    else {
      FUN_00499910(uVar14,uVar9,cVar7);
    }
    *(undefined4 *)(param_1 + 0xb1e4) = 0;
    FUN_005c5220();
    FUN_005caa00();
    FUN_00402ca0();
    if (*(char *)(DAT_006ba818 + 0x51) == '\0') {
      if (*(char *)(param_1 + 0x29bdc) != '\0') {
        FUN_0057ade0(0);
      }
      FUN_0057bc80();
      FUN_0057cca0(param_2 + -1,param_3 + 1);
    }
  }
  *(uint *)(param_1 + 0x29bd8) = uVar14;
  FUN_004a4450(0);
  *(undefined1 *)(param_1 + 0x29bf5) = 0;
  if (bVar6) {
    FUN_004a49a0();
    FUN_004f08e0();
    FUN_00498ce0();
    if (local_2bbc != 0) {
      do {
        uVar15 = FUN_005a86b0(param_2 + iVar20);
        uVar11 = FUN_005a8690(param_2 + iVar20 + 4);
        uVar12 = FUN_005a8690(param_2 + iVar20 + 6);
        uVar13 = FUN_005a8690(param_2 + iVar20 + 8);
        uVar9 = FUN_005a8680(param_2 + iVar20 + 10);
        iVar20 = iVar20 + 0xf;
        uVar17 = FUN_005a86b0(param_2 + -4 + iVar20);
        uVar16 = *(uint *)(param_1 + 0x29bf0);
        if (((uVar16 == 5) || (uVar16 == 4)) || (uVar16 == 7)) {
          uVar16 = 1;
        }
        else {
          uVar16 = uVar16 & 0xffffff00;
        }
        FUN_00499350(uVar15,uVar11,uVar12,uVar9,uVar13,uVar17,cVar8 == '\0',uVar16);
        local_2bbc = local_2bbc - 1;
      } while (local_2bbc != 0);
    }
  }
  FUN_00499250();
  uVar15 = FUN_004255c0();
  *(undefined4 *)(param_1 + 0x29be0) = uVar15;
  *(char *)(param_1 + 0x29bdc) = cVar8;
  if (*(int *)(DAT_006ba7c8 + 0xc0c) == *(int *)(param_1 + 0x29af4)) {
    if ((cVar8 == '\0') && (*(char *)(DAT_006ba808 + 4) != '\0')) {
      FUN_00565530(1);
    }
    else {
      FUN_00421580();
    }
  }
  if (*(char *)(param_1 + 0x29bdc) == '\0') {
    if (*(char *)(DAT_00c32cd0 + 0x2d) != '\0') {
      FUN_00589e70();
    }
  }
  else if (*(char *)(DAT_00c32cd0 + 0x2d) == '\0') {
    FUN_0058c450();
  }
  if (*(int **)(DAT_006ba7c8 + 0xc0c) == *(int **)(param_1 + 0x29af8)) {
    (**(code **)(**(int **)(param_1 + 0x29af8) + 0x38))();
  }
  iVar20 = *(int *)(param_1 + 0x29bf0);
  if (cVar8 == '\0') {
    if (iVar20 == 3) goto LAB_004ae57d;
LAB_004ae566:
    if (iVar20 == 5) goto LAB_004ae57d;
    if (iVar20 == 4) {
      iVar20 = 6;
      goto LAB_004ae57d;
    }
    if (iVar20 == 7) goto LAB_004ae57d;
  }
  else {
    if (iVar20 != 3) goto LAB_004ae566;
    iVar20 = 4;
LAB_004ae57d:
    FUN_004a4450(iVar20);
  }
  FUN_004a30d0();
  if ((cVar8 == '\0') && (*(int *)(param_1 + 0x29bf0) == 1)) {
    FUN_004a4450(1);
    *(undefined1 *)(param_1 + 0x29bf5) = 1;
    *(undefined4 *)(param_1 + 0x29bf8) = 0x400;
    *(undefined4 *)(param_1 + 0x29bfc) = 0x400;
    *(undefined4 *)(param_1 + 0x29c00) = 0xc00;
    *(undefined4 *)(param_1 + 0x29c04) = 0xc00;
    if (*(int *)(param_1 + 0x29bf8) < 0x800) {
      *(undefined4 *)(param_1 + 0x29bf8) = 0x800;
    }
    if (0xfff < *(int *)(param_1 + 0x29c00)) {
      *(undefined4 *)(param_1 + 0x29c00) = 0xfff;
    }
    if (*(int *)(param_1 + 0x29bfc) < 0x800) {
      *(undefined4 *)(param_1 + 0x29bfc) = 0x800;
    }
    if (0xfff < *(int *)(param_1 + 0x29c04)) {
      *(undefined4 *)(param_1 + 0x29c04) = 0xfff;
    }
    local_2bc8 = (int *)(param_1 + 0x29c00);
    *(undefined4 *)(param_1 + 0x29c08) = 0;
    *(undefined4 *)(param_1 + 0x29c0c) = 0;
    *(undefined4 *)(param_1 + 0x29c10) = 0x800;
    *(undefined4 *)(param_1 + 0x29c14) = 0x800;
    local_2bbc = 0;
    do {
      iVar20 = FUN_00551ec0(local_2bbc + 7);
      if (iVar20 != 0) {
        bVar2 = *(byte *)(iVar20 + 0x106);
        bVar3 = *(byte *)(iVar20 + 0x107);
        bVar4 = *(byte *)(iVar20 + 0x108);
        iVar20 = local_2bc8[-1] + 0x28;
        if (iVar20 < local_2bc8[1] + -0x28) {
          iVar18 = *local_2bc8 + -0x4b;
          do {
            iVar21 = local_2bc8[-2] + 0x4b;
            if (iVar21 < iVar18) {
              do {
                iVar18 = _rand();
                iVar18 = iVar18 % 0x3c + -0x1e + iVar21;
                iVar19 = _rand();
                uVar33 = 0xffffffff;
                uVar32 = 0;
                uVar31 = 0;
                iVar19 = iVar19 % 0x78 + -0x3c + iVar20;
                pcVar28 = "atmsb.xpf";
                uVar27 = 0;
                uVar26 = 0;
                uVar25 = 0;
                uVar24 = 0xffffffff;
                uVar17 = 1;
                uVar15 = 0;
                pcVar23 = "atms.xpf";
                uVar16 = (uint)(bVar2 >> 3);
                uVar29 = (uint)(bVar3 >> 3);
                uVar30 = (uint)(bVar4 >> 3);
                FUN_005ca9f0(5);
                FUN_004e9c30(pcVar23,iVar18,iVar19,uVar15,uVar17,uVar24,uVar25,uVar26,uVar27,pcVar28
                             ,uVar16,uVar29,uVar30,uVar31,uVar32,uVar33);
                iVar21 = iVar21 + 0x96;
                iVar18 = *local_2bc8 + -0x4b;
              } while (iVar21 < iVar18);
            }
            iVar20 = iVar20 + 0x50;
          } while (iVar20 < local_2bc8[1] + -0x28);
        }
      }
      local_2bc8 = local_2bc8 + 4;
      local_2bbc = local_2bbc + 1;
    } while ((int)local_2bbc < 2);
  }
  *(undefined1 *)(param_1 + 0x29c85) = 0;
  if (*(char *)(param_1 + 0x29bdc) == '\0') {
    *(undefined4 *)(DAT_006ba830 + 0x100054) = 15000;
    FUN_004b6fc0();
    iVar20 = *(int *)(param_1 + 0x8564);
    *(undefined4 *)(iVar20 + 0x102608) = 2;
    *(undefined4 *)(iVar20 + 0x10260c) = 2;
    if (*(int **)(DAT_006ba7c8 + 0xc0c) == *(int **)(param_1 + 0x29b18)) {
      (**(code **)(**(int **)(param_1 + 0x29b18) + 0x38))();
    }
    if (*(int **)(DAT_006ba7c8 + 0xc0c) == *(int **)(param_1 + 0x29b14)) {
      (**(code **)(**(int **)(param_1 + 0x29b14) + 0x38))();
    }
    iVar20 = *(int *)(param_1 + 0x19e60);
    if (((iVar20 != 0) && (*(int *)(DAT_006ba7c8 + 0xc0c) == iVar20)) &&
       (*(int *)(iVar20 + 0x178) == *(int *)(param_1 + 0x29b18))) {
      *(undefined4 *)(iVar20 + 0x178) = *(undefined4 *)(*(int *)(param_1 + 0x29b18) + 0x23550);
      (**(code **)(**(int **)(param_1 + 0x29b18) + 0x38))();
      FUN_00548730(*(undefined4 *)(param_1 + 0x19e60));
      FUN_005ecde0();
    }
    FUN_005e9090(uVar14);
  }
  else {
    *(undefined1 *)(param_1 + 0xb1e0) = 0;
    *(undefined1 *)(param_1 + 0x29c2f) = 0;
    *(undefined4 *)(DAT_006ba830 + 0x100054) = 1000;
    FUN_004b6f70();
    uVar16 = *(uint *)(DAT_006ba7d8 + 0x3ec) & 0xf00 | *(uint *)(DAT_006ba7d8 + 0x3dc) & 0xf0 |
             *(uint *)(DAT_006ba7d8 + 0x3f0) & 3 | *(uint *)(DAT_006ba7d8 + 0x3e0) & 0xc |
             *(uint *)(DAT_006ba7d8 + 0x3f8) & 0xf000;
    FUN_00407ee0(uVar16);
    iVar20 = *(int *)(param_1 + 0x29bd4);
    if (((-1 < iVar20) && (iVar20 <= *(int *)(DAT_006ba80c + 0x1c))) &&
       (((int)uVar16 <= *(int *)(DAT_006ba80c + 0x1c) &&
        (*(int *)(*(int *)(DAT_006ba80c + 0x18) + iVar20 * 4) ==
         *(int *)(*(int *)(DAT_006ba80c + 0x18) + uVar16 * 4))))) {
      FUN_004b6d70();
    }
    iVar20 = *(int *)(param_1 + 0x8564);
    *(undefined4 *)(iVar20 + 0x102608) = 0;
    *(undefined4 *)(iVar20 + 0x10260c) = 0;
    FUN_004a4850();
    FUN_005e9060(uVar14);
    if ((cVar1 == '\0') || (uVar5 != uVar14)) {
      iVar20 = *DAT_006ba7c4;
      iVar18 = FUN_00545210(auStack_2b78);
      (**(code **)(iVar20 + 0x40))(*(undefined2 *)(iVar18 + 2));
      (**(code **)(*DAT_006ba7c4 + 0x60))("HR_BGM9.MP3","HR_BGM8.MP3");
    }
    DAT_00ea9501 = 0;
    FUN_0055ffe0();
  }
  cVar7 = (**(code **)(*DAT_006ba7c4 + 100))();
  if (((cVar7 == '\0') && (cVar8 == '\0')) && (*(char *)(DAT_006ba818 + 0x50) == '\0')) {
    if ((cVar1 != '\0') && (*(char *)(param_1 + 0xb1e0) != '\0')) goto LAB_004aea4a;
  }
  else if (((*(char *)(param_1 + 0xb1e0) != '\0') || (cVar8 != '\0')) || (cVar1 == '\0'))
  goto LAB_004aea4a;
  FUN_004a3060(0,"HR_BGM1.MP3|HR_BGM2.MP3");
LAB_004aea4a:
  if (((iVar22 == 5) && (cVar8 == '\0')) && (*(char *)(DAT_006ba818 + 0x50) == '\0')) {
    FUN_004a3060(0,"HR_BGM1.MP3|HR_BGM2.MP3");
  }
  if (*(int *)(DAT_006ba7c8 + 0x1c58) == 1) {
    if (((*(char *)(param_1 + 0x29bdc) == '\0') &&
        (iVar22 = *(int *)(param_1 + 0x29bf0), iVar22 != 1)) &&
       ((iVar22 != 3 && ((iVar22 != 5 && (iVar22 != 7)))))) {
      if (*(char *)(param_1 + 0x218f5) == '\0') {
        FUN_005b4d30(1);
      }
      else {
        FUN_0049efa0();
      }
      if (*(int *)(param_1 + 0x855c) != 0) {
        FUN_0057a1e0();
      }
    }
    else {
      FUN_00575470();
      FUN_005b4d30(0);
    }
    if (*(int *)(param_1 + 0x855c) != 0) {
      FUN_005758f0();
    }
  }
  FUN_004aaca0();
  FUN_00425760();
  if (local_2bc3 != '\0') {
    if (*(int *)(DAT_006ba7c8 + 0xc0c) == *(int *)(param_1 + 0x19e60)) {
      *(char *)(param_1 + 0xb1e1) = local_2bc3;
    }
    else {
      FUN_005a6aa0();
      local_4._0_1_ = 1;
      if (*(uint *)(param_1 + 0x23c) < 0x10) {
        iVar22 = param_1 + 0x228;
      }
      else {
        iVar22 = *(int *)(param_1 + 0x228);
      }
      FUN_005a6ba0(param_1 + 4,iVar22,1,1,0,0xffffffff,0xffffffff,1);
      local_4 = (uint)local_4._1_3_ << 8;
      FUN_005a6630();
    }
  }
  ExceptionList = pvStack_c;
  return;
}


