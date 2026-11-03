
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

undefined4 __thiscall FUN_005a5c50(int param_1,byte *param_2,size_t param_3)

{
  byte *_Str;
  byte bVar1;
  uchar uVar2;
  char cVar3;
  char cVar4;
  undefined2 uVar5;
  int iVar6;
  undefined4 uVar7;
  byte *pbVar8;
  uchar *puVar9;
  uchar *puVar10;
  size_t sVar11;
  undefined4 *puVar12;
  LPSTR _Src;
  char *pcVar13;
  uint uVar14;
  char *pcVar15;
  char *pcVar16;
  char *pcStack_271d8;
  int iStack_271d4;
  undefined **ppuStack_271d0;
  int iStack_271cc;
  size_t sStack_271c8;
  uint uStack_271c4;
  byte *pbStack_271c0;
  uint uStack_271bc;
  int iStack_271b8;
  uchar *puStack_271b4;
  int iStack_271b0;
  byte abStack_271ac [4];
  uchar *puStack_271a8;
  undefined1 *puStack_271a4;
  undefined1 *puStack_271a0;
  byte bStack_2719c;
  byte bStack_2719b;
  byte bStack_2719a;
  byte bStack_27199;
  ushort uStack_27198;
  uint uStack_27194;
  int iStack_27190;
  undefined **ppuStack_2718c;
  undefined4 uStack_27164;
  undefined1 auStack_27160 [256];
  char acStack_27060 [260];
  uchar auStack_26f5c [2048];
  undefined1 auStack_2675c [1024];
  byte abStack_2635c [13456];
  undefined2 uStack_22ecc;
  undefined2 uStack_22eca;
  byte bStack_22ec8;
  char acStack_22ec7 [65536];
  char acStack_12ec7 [1024];
  char acStack_12ac7 [256];
  char acStack_129c7 [76219];
  void *local_c;
  undefined1 *puStack_8;
  uint local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063b63d;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  FUN_0058c730();
  local_4 = 0;
  FUN_005a8ee0();
  pbStack_271c0 = param_2;
  uStack_271c4 = (uint)*param_2;
  sStack_271c8 = param_3;
  ppuStack_271d0 = CReceivedPacketEx::vftable;
  local_4 = CONCAT31(local_4._1_3_,2);
  iStack_271cc = 1;
  cVar3 = FUN_005a8680(param_2);
  if (cVar3 == '\x02') {
    FUN_00544f50(1);
    pbVar8 = pbStack_271c0 + iStack_271cc;
    iStack_271cc = iStack_271cc + 1;
    cVar4 = FUN_005a8680(pbVar8);
    if (cVar4 == '\0') {
      if (*(char *)(DAT_006ba840 + 0xadc) != '\0') {
        *(undefined1 *)(DAT_006ba840 + 0xadd) = 1;
        FUN_004025c0(param_1 + 0x60a04,0,0xffffffff);
      }
      if (*(int *)(DAT_006ba7c8 + 0x1c58) != 1) {
        FUN_0059eef0();
      }
    }
  }
  else if (cVar3 == 'U') {
    FUN_005a55b0(param_2 + 1,param_3);
    goto LAB_005a65db;
  }
  if (*(char *)(DAT_006ba840 + 0xc5d) == '\0') {
    _memcpy(auStack_2675c,param_2,param_3);
    auStack_2675c[param_3] = 0;
    iVar6 = FUN_0060ab80(auStack_2675c,"SERVER CONNECTED");
    if (iVar6 == 0) {
      if (cVar3 == '\0') {
        pbVar8 = pbStack_271c0 + iStack_271cc;
        iStack_271cc = iStack_271cc + 1;
        cVar3 = FUN_005a8680(pbVar8);
        if (cVar3 == '\0') {
          uStack_271bc = FUN_00438220();
          pcVar16 = *(char **)(DAT_006ba840 + 0x494);
          auStack_26f5c[0] = (uchar)pcVar16;
          pcVar15 = (char *)0x1;
          if (0 < (int)pcVar16) {
            iStack_271d4 = 0;
            pcStack_271d8 = pcVar16;
            do {
              auStack_26f5c[(int)pcVar15] = *(uchar *)(iStack_271d4 + 0x94 + DAT_006ba840);
              iVar6 = iStack_271d4 + 0x94 + DAT_006ba840;
              auStack_26f5c[(int)(pcVar15 + 1)] = *(uchar *)(iStack_271d4 + 0xa7 + DAT_006ba840);
              auStack_26f5c[(int)(pcVar15 + 2)] = *(uchar *)(iVar6 + 0x12);
              auStack_26f5c[(int)(pcVar15 + 3)] = *(uchar *)(iVar6 + 0x11);
              auStack_26f5c[(int)(pcVar15 + 4)] = *(uchar *)(iVar6 + 0x10);
              auStack_26f5c[(int)(pcVar15 + 5)] =
                   (uchar)((int)*(short *)(iVar6 + 0x14) +
                           ((int)*(short *)(iVar6 + 0x14) >> 0x1f & 0xffU) >> 8);
              auStack_26f5c[(int)(pcVar15 + 6)] = (uchar)*(undefined2 *)(iVar6 + 0x14);
              puVar9 = *(uchar **)(iVar6 + 4);
              pcVar16 = pcVar15 + 7;
              if (puVar9 != (uchar *)0x0) {
                puVar10 = puVar9;
                do {
                  uVar2 = *puVar10;
                  puVar10 = puVar10 + 1;
                } while (uVar2 != '\0');
                __mbsnbcpy_s(auStack_26f5c + (int)(pcVar15 + 7),0x800 - (int)pcVar16,puVar9,
                             (int)puVar10 - (int)(puVar9 + 1));
                pcVar13 = *(char **)(iVar6 + 4);
                pcVar15 = pcVar13 + 1;
                do {
                  cVar3 = *pcVar13;
                  pcVar13 = pcVar13 + 1;
                } while (cVar3 != '\0');
                pcVar16 = pcVar13 + ((int)pcVar16 - (int)pcVar15);
              }
              if (*(int *)(iVar6 + 8) != 0) {
                auStack_26f5c[(int)pcVar16] = ';';
                puVar9 = *(uchar **)(iVar6 + 8);
                puVar10 = puVar9;
                do {
                  uVar2 = *puVar10;
                  puVar10 = puVar10 + 1;
                } while (uVar2 != '\0');
                __mbsnbcpy_s(auStack_26f5c + (int)(pcVar16 + 1),0x800 - (int)(pcVar16 + 1),puVar9,
                             (int)puVar10 - (int)(puVar9 + 1));
                pcVar13 = *(char **)(iVar6 + 8);
                pcVar15 = pcVar13 + 1;
                do {
                  cVar3 = *pcVar13;
                  pcVar13 = pcVar13 + 1;
                } while (cVar3 != '\0');
                pcVar16 = pcVar13 + ((int)(pcVar16 + 1) - (int)pcVar15);
              }
              auStack_26f5c[(int)pcVar16] = '\0';
              iStack_271d4 = iStack_271d4 + 0x20;
              pcVar15 = pcVar16 + 1;
              pcStack_271d8 = pcStack_271d8 + -1;
            } while (pcStack_271d8 != (char *)0x0);
          }
          uVar14 = FUN_004338e0(auStack_26f5c,pcVar15);
          if ((*(int *)(DAT_006ba840 + 0x494) < 1) || (uStack_271bc != (uVar14 & 0xffff))) {
            FUN_005a8f10(0xb);
            ppuStack_2718c = CSendPacketEx::vftable;
            local_4._0_1_ = 4;
            FUN_005a8fc0(1);
            FUN_005aa1e0();
            local_4 = CONCAT31(local_4._1_3_,2);
            FUN_005a8f50();
            *(undefined1 *)(DAT_006ba7c8 + 0x261d) = 1;
          }
          else {
            FUN_005a28e0();
            *(undefined1 *)(DAT_006ba7c8 + 0x261d) = 1;
          }
        }
        else if (cVar3 == '\x01') {
          FUN_005a8f80(0x15);
          FUN_005aa1e0();
          if (*(uint *)(param_1 + 0x548) < 0x10) {
            param_1 = param_1 + 0x534;
          }
          else {
            param_1 = *(int *)(param_1 + 0x534);
          }
          FUN_0058c9f0(0,param_1,0xff,0xff,0xff,0x10);
          FUN_005450c0();
        }
        else {
          if (cVar3 != '\x02') goto LAB_005a614f;
          uVar5 = FUN_00479490();
          puVar12 = (undefined4 *)thunk_FUN_006094fc(4);
          uVar7 = thunk_FUN_006094fc(0x100);
          *puVar12 = uVar7;
          FUN_005a8da0(uVar7,0x100,"stunt3");
          FUN_005a8da0(auStack_27160,0x100,"stunt4");
          uStack_22ecc = FUN_005485d0();
          bStack_22ec8 = 1;
          iVar6 = 0;
          pcVar16 = acStack_22ec7;
          uStack_22eca = uVar5;
          do {
            _strcpy_s(pcVar16,0x100,(char *)puVar12[iVar6]);
            iVar6 = iVar6 + 1;
            pcVar16 = pcVar16 + 0x100;
          } while (iVar6 < (int)(uint)bStack_22ec8);
          _Src = GetCommandLineA();
          _strcpy_s(acStack_12ec7,0x400,_Src);
          FUN_005483e0(acStack_27060);
          if (*(int *)(DAT_006ba7c8 + 0x1c58) == 2) {
            pcVar16 = "";
          }
          else {
            pcVar16 = acStack_27060;
          }
          _strcpy_s(acStack_12ac7,0x100,pcVar16);
          _strcpy_s(acStack_129c7,0x100,"");
          FUN_00563380(&uStack_22ecc,auStack_27160);
          local_4._0_1_ = 5;
          FUN_00562500(param_1);
          local_4 = CONCAT31(local_4._1_3_,2);
          FUN_00563250();
        }
      }
      else {
        if (cVar3 != 'F') {
LAB_005a614f:
          ppuStack_271d0 = CReceivedPacket::vftable;
          local_4 = local_4 & 0xffffff00;
          FUN_005a8f50();
          local_4 = 0xffffffff;
          FUN_0058c7b0();
          ExceptionList = local_c;
          return 0;
        }
        uVar5 = FUN_00479490();
        uStack_27164 = 0x800;
        FUN_005fc960(abStack_2635c,&uStack_27164,param_2 + 3,uVar5);
        pbVar8 = (byte *)0x1;
        iStack_271b8 = 0;
        uStack_271bc = (uint)abStack_2635c[0];
        FUN_0042cc10();
        local_4 = CONCAT31(local_4._1_3_,6);
        FUN_0042cc30();
        iStack_271b0 = 0;
        if (abStack_2635c[0] != 0) {
          iStack_271d4 = 0;
          do {
            abStack_271ac[0] = abStack_2635c[(int)pbVar8];
            bStack_27199 = abStack_2635c[(int)(pbVar8 + 1)];
            bStack_2719a = abStack_2635c[(int)(pbVar8 + 2)];
            bStack_2719b = abStack_2635c[(int)(pbVar8 + 3)];
            _Str = abStack_2635c + (int)(pbVar8 + 8);
            bStack_2719c = abStack_2635c[(int)(pbVar8 + 4)];
            uStack_27194 = (uint)abStack_2635c[(int)(pbVar8 + 7)];
            uStack_27198 = (ushort)abStack_2635c[(int)(pbVar8 + 6)];
            iStack_27190 = iStack_271b0;
            pbVar8 = _Str;
            do {
              bVar1 = *pbVar8;
              pbVar8 = pbVar8 + 1;
            } while (bVar1 != 0);
            pbVar8 = pbVar8 + -(int)abStack_2635c;
            iVar6 = FUN_0060c9e0(_Str,0x3b);
            if (iVar6 == 0) {
              puVar9 = (uchar *)_strtok_s((char *)_Str,":",&pcStack_271d8);
              puStack_271b4 = (uchar *)0x0;
            }
            else {
              puVar9 = (uchar *)_strtok_s((char *)_Str,";",&pcStack_271d8);
              puStack_271b4 = (uchar *)_strtok_s((char *)0x0,":",&pcStack_271d8);
            }
            puVar10 = puStack_271b4;
            if (puVar9 == (uchar *)0x0) {
              puStack_271a8 = (uchar *)thunk_FUN_006094fc(1);
              *puStack_271a8 = '\0';
            }
            else {
              puVar10 = puVar9;
              do {
                uVar2 = *puVar10;
                puVar10 = puVar10 + 1;
              } while (uVar2 != '\0');
              sVar11 = (int)puVar10 - (int)(puVar9 + 1);
              puStack_271a8 = (uchar *)thunk_FUN_006094fc(sVar11 + 1);
              __mbsnbcpy_s(puStack_271a8,sVar11 + 1,puVar9,sVar11);
              puStack_271a8[sVar11] = '\0';
              puVar10 = puStack_271b4;
            }
            if (puVar10 == (uchar *)0x0) {
              puStack_271a4 = (undefined1 *)thunk_FUN_006094fc(1);
              *puStack_271a4 = 0;
            }
            else {
              puVar9 = puVar10 + 1;
              do {
                uVar2 = *puVar10;
                puVar10 = puVar10 + 1;
              } while (uVar2 != '\0');
              sVar11 = (int)puVar10 - (int)puVar9;
              puStack_271a8 = (uchar *)thunk_FUN_006094fc(sVar11 + 1);
              __mbsnbcpy_s(puStack_271a8,sVar11 + 1,puStack_271b4,sVar11);
              puStack_271a8[sVar11] = '\0';
            }
            if (puStack_271a0 == (undefined1 *)0x0) {
              puStack_271a0 = (undefined1 *)thunk_FUN_006094fc(2);
              *puStack_271a0 = 0x20;
              puStack_271a0[1] = 0;
            }
            if ((uStack_27194 == *(uint *)(DAT_006ba840 + 0xd60)) ||
               (*(uint *)(DAT_006ba840 + 0xd60) == 1)) {
              iStack_271b8 = iStack_271b8 + 1;
              iStack_271d4 = iStack_271d4 + 0x20;
              FUN_0042cc80(abStack_271ac);
            }
            FUN_0042cc30();
            iStack_271b0 = iStack_271b0 + 1;
          } while (iStack_271b0 < (int)uStack_271bc);
        }
        *(int *)(DAT_006ba840 + 0x494) = iStack_271b8;
        FUN_005a28e0();
        local_4 = CONCAT31(local_4._1_3_,2);
        FUN_0042e270();
      }
    }
    else {
      FUN_005a8900();
      if (*(char *)(param_1 + 0x1c11c) == '\0') {
        FUN_005a8f10(0);
        ppuStack_2718c = CSendPacketEx::vftable;
        local_4._0_1_ = 3;
        uVar7 = FUN_005485d0();
        FUN_005a9020(uVar7);
        FUN_005a8fc0(0x57);
        FUN_005a8fc0(1);
        uVar7 = FUN_0042da00();
        FUN_005a8fc0(uVar7);
        FUN_005aa1e0();
        local_4 = CONCAT31(local_4._1_3_,2);
        FUN_005a8f50();
      }
      else {
        FUN_0059b760();
      }
    }
  }
  else {
    _memcpy(auStack_2675c,param_2,param_3);
    auStack_2675c[param_3] = 0;
    iVar6 = FUN_0060ab80(auStack_2675c,"SERVER CONNECTED");
    if (iVar6 != 0) {
      FUN_005a8900();
    }
  }
LAB_005a65db:
  ppuStack_271d0 = CReceivedPacket::vftable;
  local_4 = local_4 & 0xffffff00;
  FUN_005a8f50();
  local_4 = 0xffffffff;
  FUN_0058c7b0();
  ExceptionList = local_c;
  return 1;
}


