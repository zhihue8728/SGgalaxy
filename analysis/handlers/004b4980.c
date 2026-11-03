
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void FUN_004b4980(byte *param_1,undefined4 param_2)

{
  uint *puVar1;
  byte *pbVar2;
  char cVar3;
  undefined1 uVar4;
  undefined2 uVar5;
  undefined2 uVar6;
  int iVar7;
  uint uVar8;
  undefined4 uVar9;
  void *_Memory;
  undefined1 *puVar10;
  uint *puVar11;
  int iStack_11864;
  undefined4 uStack_11860;
  uint uStack_1185c;
  byte *pbStack_11858;
  uint *puStack_11850;
  uint *puStack_1184c;
  int iStack_11848;
  uint uStack_11844;
  uint *puStack_1183c;
  uint *puStack_11838;
  undefined4 uStack_11834;
  uint uStack_11830;
  undefined4 uStack_1182c;
  uint uStack_11828;
  uint uStack_11824;
  undefined4 uStack_11820;
  undefined4 uStack_1181c;
  undefined4 uStack_11818;
  undefined4 uStack_11814;
  uint uStack_11810;
  undefined1 *puStack_1180c;
  undefined1 auStack_11800 [4];
  void *pvStack_117fc;
  undefined4 uStack_117ec;
  uint uStack_117e8;
  void *pvStack_117e0;
  undefined4 uStack_117d0;
  uint uStack_117cc;
  undefined1 auStack_117c8 [2828];
  undefined1 uStack_10cbc;
  undefined1 local_45c [1100];
  undefined4 uStack_10;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062cb5d;
  local_c = ExceptionList;
  uStack_10 = 0x4b499f;
  if (DAT_00c3499f == '\0') {
    pbStack_11858 = param_1;
    uStack_1185c = (uint)*param_1;
    iStack_11864 = 0;
    uStack_11860 = param_2;
    uStack_117cc = 0xf;
    uStack_117d0 = 0;
    pvStack_117e0 = (void *)((uint)pvStack_117e0 & 0xffffff00);
    uStack_117e8 = 0xf;
    uStack_117ec = 0;
    pvStack_117fc = (void *)((uint)pvStack_117fc & 0xffffff00);
    local_4._0_1_ = 2;
    local_4._1_3_ = 0;
    ExceptionList = &local_c;
    FUN_005e2ea0();
    puStack_11850 = (uint *)0x0;
    puStack_1184c = (uint *)0x0;
    iStack_11848 = 0;
    puStack_1183c = (uint *)0x0;
    puStack_11838 = (uint *)0x0;
    uStack_11834 = 0;
    iStack_11864 = iStack_11864 + 1;
    local_4 = CONCAT31(local_4._1_3_,5);
    cVar3 = FUN_005a8680();
    if (cVar3 == '\0') {
      FUN_005a8da0();
      iStack_11864 = iStack_11864 + 1;
      uStack_11828 = FUN_005a8680();
      uStack_11828 = uStack_11828 & 0xff;
      puVar10 = local_45c;
      iVar7 = 4;
      do {
        iStack_11864 = iStack_11864 + 1;
        uVar8 = FUN_005a8680();
        *(uint *)(puVar10 + -4) = uVar8 & 0xff;
        FUN_005a8da0();
        iStack_11864 = iStack_11864 + 1;
        uVar8 = FUN_005a8680();
        *(uint *)(puVar10 + 0x100) = uVar8 & 0xff;
        iStack_11864 = iStack_11864 + 1;
        uVar8 = FUN_005a8680();
        *(uint *)(puVar10 + 0x104) = uVar8 & 0xff;
        iStack_11864 = iStack_11864 + 4;
        uVar9 = FUN_005a86b0();
        *(undefined4 *)(puVar10 + 0x108) = uVar9;
        iStack_11864 = iStack_11864 + 4;
        uVar9 = FUN_005a86b0();
        *(undefined4 *)(puVar10 + 0x10c) = uVar9;
        puVar10 = puVar10 + 0x114;
        iVar7 = iVar7 + -1;
      } while (iVar7 != 0);
      iStack_11864 = iStack_11864 + 1;
      uStack_11824 = FUN_005a8680();
      uStack_11824 = uStack_11824 & 0xff;
      iStack_11864 = iStack_11864 + 4;
      uStack_11814 = FUN_005a86b0();
      iStack_11864 = iStack_11864 + 4;
      uStack_1181c = FUN_005a86b0();
      iStack_11864 = iStack_11864 + 4;
      uStack_11818 = FUN_005a86b0();
      iStack_11864 = iStack_11864 + 1;
      uVar8 = FUN_005a8680();
      uVar8 = uVar8 & 0xff;
      if (puStack_1184c < puStack_11850) {
        FUN_00609e03();
      }
      if (puStack_1184c < puStack_11850) {
        FUN_00609e03();
      }
      FUN_00501b80();
      if (puStack_11838 < puStack_1183c) {
        FUN_00609e03();
      }
      if (puStack_11838 < puStack_1183c) {
        FUN_00609e03();
      }
      FUN_004304c0();
      for (; uVar8 != 0; uVar8 = uVar8 - 1) {
        iStack_11864 = iStack_11864 + 4;
        uStack_11844 = FUN_005a86b0();
        if ((puStack_11850 == (uint *)0x0) ||
           ((uint)(iStack_11848 - (int)puStack_11850 >> 2) <=
            (uint)((int)puStack_1184c - (int)puStack_11850 >> 2))) {
          if (puStack_1184c < puStack_11850) {
            FUN_00609e03();
          }
          FUN_00465690();
        }
        else {
          *puStack_1184c = uStack_11844;
          puStack_1184c = puStack_1184c + 1;
        }
        FUN_005a9ff0();
        FUN_00424e30();
      }
      iStack_11864 = iStack_11864 + 2;
      uVar5 = FUN_005a8690();
      iStack_11864 = iStack_11864 + 2;
      uVar6 = FUN_005a8690();
      iStack_11864 = iStack_11864 + 1;
      FUN_005a8680();
      iStack_11864 = iStack_11864 + 1;
      uStack_11810 = FUN_005a8680();
      uStack_11810 = uStack_11810 & 0xff;
      iStack_11864 = iStack_11864 + 1;
      uStack_11844 = FUN_005a8680();
      uStack_11844 = uStack_11844 & 0xff;
      iStack_11864 = iStack_11864 + 1;
      uStack_11830 = FUN_005a8680();
      uStack_11830 = uStack_11830 & 0xff;
      iStack_11864 = iStack_11864 + 2;
      FUN_005a8690();
      FUN_005a9ff0(auStack_11800,pbStack_11858,&iStack_11864);
      pbVar2 = pbStack_11858 + iStack_11864;
      iStack_11864 = iStack_11864 + 1;
      FUN_005a8680(pbVar2);
      FUN_005e09f0();
      uStack_10cbc = 1;
      FUN_005e0860();
      puStack_1180c = &stack0xfffee76c;
      FUN_004025c0(auStack_11800,0,0xffffffff);
      uStack_1182c = *(undefined4 *)(DAT_006ba7d8 + 0x44c);
      uVar8 = *(uint *)(DAT_006ba7d8 + 0x3c4) & 0xf00 | *(uint *)(DAT_006ba7d8 + 0x3b4) & 0xf0 |
              *(uint *)(DAT_006ba7d8 + 0x3c8) & 3 | *(uint *)(DAT_006ba7d8 + 0x3b8) & 0xc |
              *(uint *)(DAT_006ba7d8 + 0x3d0) & 0xf000;
      local_4._0_1_ = 6;
      FUN_00407ee0(uVar8);
      uStack_11820 = *(undefined4 *)(DAT_006ba7d8 + 0x450);
      uVar9 = FUN_004ee140();
      local_4 = CONCAT31(local_4._1_3_,5);
      FUN_005e1630(uVar9,uStack_11820,uVar8,uStack_1182c,auStack_117c8,uStack_11824,uStack_11828,
                   uStack_11814,uStack_1181c,uStack_11818,uVar5,uVar6,&DAT_0064c756);
      FUN_005e0830();
      FUN_005e3270();
      for (uVar8 = 0;
          (puStack_11850 != (uint *)0x0 &&
          (uVar8 < (uint)((int)puStack_1184c - (int)puStack_11850 >> 2))); uVar8 = uVar8 + 1) {
        if ((puStack_1183c == (uint *)0x0) ||
           ((uint)(((int)puStack_11838 - (int)puStack_1183c) / 0x1c) <= uVar8)) {
          FUN_00609e03();
        }
        if ((puStack_11850 == (uint *)0x0) ||
           ((uint)((int)puStack_1184c - (int)puStack_11850 >> 2) <= uVar8)) {
          FUN_00609e03();
        }
        FUN_005e3320();
      }
    }
    else if (cVar3 == '\x01') {
      FUN_005a8da0();
      iStack_11864 = iStack_11864 + 1;
      uVar4 = FUN_005a8680();
      uStack_1182c = CONCAT31(uStack_1182c._1_3_,uVar4);
      iStack_11864 = iStack_11864 + 4;
      uStack_11820 = FUN_005a86b0();
      iStack_11864 = iStack_11864 + 2;
      uStack_11830 = FUN_005a8690();
      uStack_11830 = uStack_11830 & 0xffff;
      if ((uStack_11830 != 0) && (iVar7 = FUN_0057e310(), iVar7 != 0)) {
        FUN_0057d2d0();
      }
      FUN_005a8da0();
      iStack_11864 = iStack_11864 + 1;
      uStack_11828 = FUN_005a8680();
      uStack_11828 = uStack_11828 & 0xff;
      puVar10 = local_45c;
      iVar7 = 4;
      do {
        iStack_11864 = iStack_11864 + 1;
        uVar8 = FUN_005a8680();
        *(uint *)(puVar10 + -4) = uVar8 & 0xff;
        FUN_005a8da0();
        iStack_11864 = iStack_11864 + 1;
        uVar8 = FUN_005a8680();
        *(uint *)(puVar10 + 0x100) = uVar8 & 0xff;
        iStack_11864 = iStack_11864 + 1;
        uVar8 = FUN_005a8680();
        *(uint *)(puVar10 + 0x104) = uVar8 & 0xff;
        iStack_11864 = iStack_11864 + 4;
        uVar9 = FUN_005a86b0();
        *(undefined4 *)(puVar10 + 0x108) = uVar9;
        iStack_11864 = iStack_11864 + 4;
        uVar9 = FUN_005a86b0();
        *(undefined4 *)(puVar10 + 0x10c) = uVar9;
        puVar10 = puVar10 + 0x114;
        iVar7 = iVar7 + -1;
      } while (iVar7 != 0);
      iStack_11864 = iStack_11864 + 1;
      uStack_11824 = FUN_005a8680();
      uStack_11824 = uStack_11824 & 0xff;
      iStack_11864 = iStack_11864 + 4;
      uStack_11814 = FUN_005a86b0();
      iStack_11864 = iStack_11864 + 4;
      uStack_1181c = FUN_005a86b0();
      iStack_11864 = iStack_11864 + 4;
      uStack_11818 = FUN_005a86b0();
      iStack_11864 = iStack_11864 + 1;
      uVar8 = FUN_005a8680();
      uVar8 = uVar8 & 0xff;
      if (puStack_1184c < puStack_11850) {
        FUN_00609e03();
      }
      if (puStack_1184c < puStack_11850) {
        FUN_00609e03();
      }
      FUN_00501b80();
      for (; uVar8 != 0; uVar8 = uVar8 - 1) {
        iStack_11864 = iStack_11864 + 4;
        uStack_11844 = FUN_005a86b0();
        if ((puStack_11850 == (uint *)0x0) ||
           ((uint)(iStack_11848 - (int)puStack_11850 >> 2) <=
            (uint)((int)puStack_1184c - (int)puStack_11850 >> 2))) {
          if (puStack_1184c < puStack_11850) {
            FUN_00609e03();
          }
          FUN_00465690();
        }
        else {
          *puStack_1184c = uStack_11844;
          puStack_1184c = puStack_1184c + 1;
        }
        FUN_005a9ff0();
        FUN_00424e30();
      }
      iStack_11864 = iStack_11864 + 2;
      FUN_005a8690();
      iStack_11864 = iStack_11864 + 2;
      FUN_005a8690();
      FUN_005a8da0();
      iStack_11864 = iStack_11864 + 2;
      FUN_005a8690();
      _Memory = (void *)thunk_FUN_006094fc();
      FUN_005a88c0();
                    /* WARNING: Subroutine does not return */
      _free(_Memory);
    }
    DAT_00c3499f = 1;
    FUN_005e0a40();
    DAT_00c3499f = '\0';
    if (puStack_1183c != (uint *)0x0) {
      if (puStack_1183c != puStack_11838) {
        puVar11 = puStack_1183c + 6;
        do {
          if (0xf < *puVar11) {
                    /* WARNING: Subroutine does not return */
            _free((void *)puVar11[-5]);
          }
          *puVar11 = 0xf;
          puVar11[-1] = 0;
          *(undefined1 *)(puVar11 + -5) = 0;
          puVar1 = puVar11 + 1;
          puVar11 = puVar11 + 7;
        } while (puVar1 != puStack_11838);
      }
                    /* WARNING: Subroutine does not return */
      _free(puStack_1183c);
    }
    puStack_1183c = (uint *)0x0;
    puStack_11838 = (uint *)0x0;
    uStack_11834 = 0;
    if (puStack_11850 != (uint *)0x0) {
                    /* WARNING: Subroutine does not return */
      _free(puStack_11850);
    }
    puStack_11850 = (uint *)0x0;
    puStack_1184c = (uint *)0x0;
    iStack_11848 = 0;
    local_4 = CONCAT31(local_4._1_3_,2);
    FUN_005e3070();
    if (0xf < uStack_117e8) {
                    /* WARNING: Subroutine does not return */
      _free(pvStack_117fc);
    }
    uStack_117e8 = 0xf;
    uStack_117ec = 0;
    pvStack_117fc = (void *)((uint)pvStack_117fc & 0xffffff00);
    if (0xf < uStack_117cc) {
                    /* WARNING: Subroutine does not return */
      _free(pvStack_117e0);
    }
  }
  ExceptionList = local_c;
  return;
}


