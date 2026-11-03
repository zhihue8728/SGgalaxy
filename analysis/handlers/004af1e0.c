
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __thiscall FUN_004af1e0(int param_1,int param_2)

{
  char cVar1;
  int *piVar2;
  bool bVar3;
  undefined1 uVar4;
  byte bVar5;
  undefined1 uVar6;
  undefined4 uVar7;
  uint uVar8;
  int iVar9;
  int iVar10;
  uint uVar11;
  char *pcVar12;
  uint uVar13;
  int iStack_15ec0;
  int iStack_15ea8;
  int iStack_15ea4;
  uint uStack_15e9c;
  char *pcStack_15e98;
  char *pcStack_15e94;
  uint uStack_15e90;
  undefined **ppuStack_15e8c;
  undefined1 auStack_15e78 [12];
  char acStack_15e6c [256];
  char acStack_15d6c [1060];
  undefined1 uStack_15948;
  int iStack_15944;
  int iStack_15940;
  int iStack_1593c;
  char acStack_15934 [3072];
  char acStack_14d34 [3072];
  int *piStack_14134;
  int iStack_14110;
  undefined4 uStack_1410c;
  uint uStack_14108;
  undefined4 uStack_14104;
  undefined4 uStack_14100;
  undefined1 uStack_140fc;
  void *local_c;
  undefined1 *puStack_8;
  int local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062c4bc;
  local_c = ExceptionList;
  if (DAT_00c3499d != '\0') {
    return;
  }
  if (*(char *)(param_1 + 0xa119) != '\0') {
    return;
  }
  ExceptionList = &local_c;
  FUN_004a4850();
  local_4 = 0;
  iStack_15ea8 = 0;
  iStack_15ea4 = 0;
  bVar3 = false;
  FUN_00409e30();
  local_4 = CONCAT31(local_4._1_3_,1);
  uVar7 = FUN_005a86b0(param_2);
  uVar8 = FUN_005a8680(param_2 + 4);
  uVar4 = FUN_005a8680(param_2 + 5);
  iVar9 = FUN_005a86b0(param_2 + 6);
  FUN_005a8da0(acStack_15e6c,0x100,"fldbctrl");
  iStack_15ec0 = 0xb;
  uStack_15e9c = FUN_005a8680(param_2 + 10);
  uStack_15e9c = uStack_15e9c & 0xff;
  if (uStack_15e9c != 0) {
    pcStack_15e98 = acStack_15934;
    pcStack_15e94 = acStack_14d34;
    do {
      FUN_005a8da0(acStack_15d6c,0x40,&DAT_00652650);
      iVar10 = iStack_15ec0 + 4;
      uVar11 = FUN_005a86b0(iStack_15ec0 + param_2);
      iStack_15ec0 = iStack_15ec0 + 8;
      uStack_15e90 = uVar11;
      iVar10 = FUN_005a86b0(iVar10 + param_2);
      if ((((iVar9 < 0) || (*(int *)(DAT_006ba80c + 0x1c) < iVar9)) || (iVar10 < 0)) ||
         ((*(int *)(DAT_006ba80c + 0x1c) < iVar10 ||
          (*(int *)(*(int *)(DAT_006ba80c + 0x18) + iVar9 * 4) !=
           *(int *)(*(int *)(DAT_006ba80c + 0x18) + iVar10 * 4))))) {
        *(uint *)(pcStack_15e98 + -4) = uVar11;
        _strcpy_s(pcStack_15e98,0x12,acStack_15d6c);
        iStack_15ea8 = iStack_15ea8 + 1;
        pcStack_15e98 = pcStack_15e98 + 0x18;
        if (uVar11 != 5) {
          FUN_00445e30(auStack_15e78,&uStack_15e90);
        }
      }
      else {
        *(uint *)(pcStack_15e94 + -4) = uVar11;
        _strcpy_s(pcStack_15e94,0x12,acStack_15d6c);
        iStack_15ea4 = iStack_15ea4 + 1;
        pcStack_15e94 = pcStack_15e94 + 0x18;
      }
      uVar13 = *(uint *)(DAT_006ba7d8 + 0x3d0) & 0xf000 | *(uint *)(DAT_006ba7d8 + 0x3c4) & 0xf00 |
               *(uint *)(DAT_006ba7d8 + 0x3b4) & 0xf0 | *(uint *)(DAT_006ba7d8 + 0x3c8) & 3 |
               *(uint *)(DAT_006ba7d8 + 0x3b8) & 0xc;
      FUN_00407ee0(uVar13);
      if (uVar11 == uVar13) {
        bVar3 = true;
      }
      uStack_15e9c = uStack_15e9c - 1;
    } while (uStack_15e9c != 0);
  }
  bVar5 = FUN_005a8680(iStack_15ec0 + param_2);
  uStack_15948 = FUN_005a8680(iStack_15ec0 + 1 + param_2);
  pcVar12 = acStack_15e6c;
  do {
    cVar1 = *pcVar12;
    pcVar12 = pcVar12 + 1;
  } while (cVar1 != '\0');
  FUN_004026a0(acStack_15e6c,(int)pcVar12 - (int)(acStack_15e6c + 1));
  uStack_14104 = *(undefined4 *)(param_1 + 0x29c18);
  uStack_14100 = *(undefined4 *)(param_1 + 0x29c1c);
  iStack_15944 = (uint)bVar5 * 100 + *(int *)(DAT_006ba7c8 + 0x25a0);
  iStack_1593c = iStack_15ea4;
  iStack_15940 = iStack_15ea8;
  DAT_00c3499d = 1;
  iStack_14110 = iVar9;
  uStack_1410c = uVar7;
  uStack_14108 = uVar8 & 0xff;
  uStack_140fc = uVar4;
  iVar10 = FUN_00407fc0(param_1 + 4);
  DAT_00c3499d = 0;
  FUN_005a8ee0();
  ppuStack_15e8c = CSendPacketEx::vftable;
  uVar8 = *(uint *)(DAT_006ba7d8 + 0x3c4) & 0xf00 | *(uint *)(DAT_006ba7d8 + 0x3b4) & 0xf0 |
          *(uint *)(DAT_006ba7d8 + 0x3c8) & 3 | *(uint *)(DAT_006ba7d8 + 0x3b8) & 0xc |
          *(uint *)(DAT_006ba7d8 + 0x3d0) & 0xf000;
  local_4 = CONCAT31(local_4._1_3_,2);
  FUN_00407ee0(uVar8);
  if (uVar8 == 5) {
    if (iVar10 == 0x10) {
      FUN_0049f2b0(uVar7,iVar9);
      FUN_004a5130();
      *(undefined4 *)(param_1 + 0xa238) = uStack_1410c;
      *(undefined4 *)(param_1 + 0xa23c) = uStack_14104;
      *(undefined4 *)(param_1 + 0xa240) = uStack_14100;
      *(int *)(param_1 + 0xa244) = iVar9;
      FUN_00531b50();
    }
    else {
      if (iVar10 != 0x11) {
        if (iVar10 == 0x12) {
          uVar7 = 1;
          goto LAB_004af736;
        }
        goto LAB_004af7cb;
      }
      piVar2 = (int *)*piStack_14134;
      if (piVar2 == piStack_14134) {
        FUN_00609e03();
      }
      FUN_0049f2b0(uVar7,piVar2[3]);
      FUN_004a5130();
      *(undefined4 *)(param_1 + 0xa23c) = uStack_14104;
      *(undefined4 *)(param_1 + 0xa238) = uStack_1410c;
      *(undefined4 *)(param_1 + 0xa240) = uStack_14100;
      piVar2 = (int *)*piStack_14134;
      if (piVar2 == piStack_14134) {
        FUN_00609e03();
      }
      *(int *)(param_1 + 0xa244) = piVar2[3];
      FUN_00531b50();
    }
LAB_004af7db:
    if (*(char *)(param_1 + 0xa119) == '\0') goto LAB_004af8a8;
  }
  else {
    if (iVar10 < 0x10) {
LAB_004af7cb:
      if (iVar10 == 0x14) {
        FUN_005b4cb0();
      }
      goto LAB_004af7db;
    }
    if (0x12 < iVar10) {
      if (iVar10 == 0x13) {
        uVar7 = 2;
        goto LAB_004af736;
      }
      goto LAB_004af7cb;
    }
    if (!bVar3) {
      uVar7 = 1;
LAB_004af736:
      FUN_0049f760(uVar7,uStack_1410c,uStack_14104,uStack_14100);
      FUN_0049f800(0);
      goto LAB_004af7db;
    }
    if (*(char *)(param_1 + 0xa119) == '\0') {
      FUN_0051d1f0(0x20);
      FUN_0049f130(uVar7);
      FUN_004a5130();
      *(undefined4 *)(param_1 + 0xa240) = uStack_14100;
      *(undefined4 *)(param_1 + 0xa238) = uStack_1410c;
      *(undefined4 *)(param_1 + 0xa23c) = uStack_14104;
      FUN_00531b50();
      goto LAB_004af7db;
    }
  }
  iVar9 = iStack_15ec0 + 3;
  uVar8 = FUN_005a8680(iStack_15ec0 + 2 + param_2);
  FUN_004d5930();
  local_4._0_1_ = 3;
  for (uVar8 = uVar8 & 0xff; uVar8 != 0; uVar8 = uVar8 - 1) {
    uVar7 = FUN_005a86b0(iVar9 + param_2);
    iVar10 = iVar9 + 5;
    uVar4 = FUN_005a8680(iVar9 + 4 + param_2);
    iVar9 = iVar9 + 6;
    uVar6 = FUN_005a8680(iVar10 + param_2);
    FUN_004d3050(uVar7,uVar7,uVar4,uVar6,1,0);
  }
  local_4 = CONCAT31(local_4._1_3_,2);
  FUN_004d5520();
LAB_004af8a8:
  local_4._0_1_ = 1;
  FUN_005a8f50();
  local_4 = (uint)local_4._1_3_ << 8;
  FUN_00409cd0();
  ExceptionList = local_c;
  return;
}


