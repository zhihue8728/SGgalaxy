
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __thiscall FUN_004390b0(int param_1,byte *param_2,undefined4 param_3)

{
  char *_Dst;
  char cVar1;
  int iVar2;
  undefined4 uVar3;
  int iVar4;
  uint uVar5;
  undefined4 uVar6;
  TypeDescriptor *pTVar7;
  TypeDescriptor *pTVar8;
  undefined4 uVar9;
  undefined4 local_648;
  undefined4 local_644;
  undefined4 local_62c;
  undefined4 local_628;
  undefined4 local_624;
  undefined **local_620;
  undefined4 local_61c;
  undefined4 local_618;
  uint local_614;
  byte *local_610;
  undefined1 local_60c [256];
  undefined1 local_50c [256];
  char local_40c [1024];
  void *local_c;
  undefined1 *puStack_8;
  uint local_4;
  
  puStack_8 = &LAB_00626d97;
  local_c = ExceptionList;
  local_610 = param_2;
  local_614 = (uint)*param_2;
  local_61c = 0;
  local_618 = param_3;
  local_620 = CReceivedPacketEx::vftable;
  local_4 = 0;
  ExceptionList = &local_c;
  FUN_005a8da0(local_40c,0x100,"chatcct");
  _Dst = (char *)(param_1 + 0x6ecc);
  _strcpy_s(_Dst,0x101,local_40c);
  iVar2 = FUN_0060ab80(_Dst,&DAT_0064f288);
  if (iVar2 != 0) {
    cVar1 = FUN_00437e30(0,&local_648);
    if (cVar1 == '\0') {
      cVar1 = FUN_00437d60(1);
      if (cVar1 == '\0') {
        cVar1 = FUN_00437d60(0xb);
        if (cVar1 == '\0') {
          cVar1 = FUN_00437d60(0x16);
          if (cVar1 == '\0') {
            cVar1 = FUN_00437d60(0xc);
            if (cVar1 == '\0') {
              cVar1 = FUN_00437d60(0xe);
              if (cVar1 == '\0') {
                cVar1 = FUN_00437d60(0xd);
                if (cVar1 == '\0') {
                  cVar1 = FUN_00437e30(2,&local_648);
                  if (cVar1 == '\0') {
                    cVar1 = FUN_00437db0(3,&local_624);
                    if (cVar1 == '\0') {
                      cVar1 = FUN_00437d60(4);
                      if (cVar1 != '\0') {
                        *(undefined4 *)(*(int *)(DAT_006ba7cc + 0x8564) + 0x10260c) = 2;
                        ExceptionList = local_c;
                        return 1;
                      }
                      cVar1 = FUN_00437d60(5);
                      if (cVar1 != '\0') {
                        *(undefined4 *)(*(int *)(DAT_006ba7cc + 0x8564) + 0x10260c) = 0;
                        ExceptionList = local_c;
                        return 1;
                      }
                      cVar1 = FUN_00437d60(6);
                      if (cVar1 != '\0') {
                        FUN_004a4250();
                        ExceptionList = local_c;
                        return 1;
                      }
                      cVar1 = FUN_00437eb0(7,local_60c);
                      if (cVar1 == '\0') {
                        cVar1 = FUN_00437eb0(8,local_60c);
                        if (cVar1 == '\0') {
                          cVar1 = FUN_00437d60(9);
                          if (cVar1 == '\0') {
                            cVar1 = FUN_00437d60(10);
                            if (cVar1 != '\0') {
                              *(bool *)(DAT_006ba7cc + 0x29c88) =
                                   *(char *)(DAT_006ba7cc + 0x29c88) == '\0';
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437d60(0x11);
                            if (cVar1 != '\0') {
                              DAT_00c32ccc = 0;
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437d60(0x12);
                            if (cVar1 != '\0') {
                              DAT_00c32ccc = 1;
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437d60(0x13);
                            if (cVar1 != '\0') {
                              FUN_004f3b50();
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437d60(0x14);
                            if (cVar1 != '\0') {
                              FUN_004f4400();
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437cd0(0x15,&local_648,local_50c);
                            if (cVar1 != '\0') {
                              FUN_004a3170(local_50c,local_648,local_644);
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437db0(0x17,&local_628);
                            if (cVar1 != '\0') {
                              FUN_004988c0(local_628);
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437db0(0x18,&local_62c);
                            if (cVar1 != '\0') {
                              FUN_004eddb0(local_62c);
                              ExceptionList = local_c;
                              return 1;
                            }
                            cVar1 = FUN_00437d60(0x19);
                            if (cVar1 != '\0') {
                              if (*(int *)(DAT_006ba7cc + 0x8560) != 0) {
                                *(undefined1 *)(*(int *)(DAT_006ba7cc + 0x8560) + 0xb2e0) = 1;
                              }
                              FUN_004eddb0(20000);
                              ExceptionList = local_c;
                              return 1;
                            }
                            iVar2 = FUN_0060ab80(_Dst,"runscript");
                            if (iVar2 == 0) {
                              ExceptionList = local_c;
                              return 1;
                            }
                            iVar2 = FUN_0060ab80(_Dst,"ctrl0");
                            if (iVar2 == 0) {
                              iVar2 = FUN_0060ab80(_Dst,"ctrl1");
                              if (iVar2 == 0) {
                                ExceptionList = local_c;
                                return 1;
                              }
                              uVar3 = 1;
                            }
                            else {
                              uVar3 = 0;
                            }
                            FUN_00589e60(uVar3);
                            ExceptionList = local_c;
                            return 1;
                          }
                          FUN_004017c0(0x7f);
                          local_4 = CONCAT31(local_4._1_3_,4);
                          FUN_005a8fc0(3);
                        }
                        else {
                          FUN_004017c0(0x7f);
                          local_4 = CONCAT31(local_4._1_3_,3);
                          FUN_005a8fc0(2);
                          FUN_005a9110(local_60c);
                        }
                      }
                      else {
                        FUN_004017c0(0x7f);
                        local_4 = CONCAT31(local_4._1_3_,2);
                        FUN_005a8fc0(1);
                        FUN_005a9110(local_60c);
                      }
                    }
                    else {
                      if (*(char *)(DAT_006ba7cc + 0x29bdc) != '\0') {
                        ExceptionList = local_c;
                        return 1;
                      }
                      FUN_004017c0(0x1b);
                      local_4 = CONCAT31(local_4._1_3_,1);
                      FUN_005a8fc0(1);
                      FUN_005a9070(local_624);
                      FUN_005a9020(0x5aa);
                      FUN_005a9020(0x5aa);
                    }
                    FUN_005aa1e0();
                    local_4 = local_4 & 0xffffff00;
                    FUN_005a8f50();
                  }
                  else if (*(char *)(DAT_006ba7cc + 0x29bdc) == '\0') {
                    FUN_005ca290(*(undefined4 *)(DAT_006ba7d8 + 8));
                    FUN_0042b130(local_648,local_644,0);
                  }
                }
                else {
                  uVar5 = 0;
                  if (*(int *)(DAT_006ba7d4 + 0x28) != 0) {
                    do {
                      uVar9 = 0;
                      pTVar8 = &CGMonster::RTTI_Type_Descriptor;
                      pTVar7 = &CGUnit::RTTI_Type_Descriptor;
                      uVar6 = 0;
                      uVar3 = FUN_004382d0(uVar5);
                      iVar2 = FUN_0060a1c9(uVar3,uVar6,pTVar7,pTVar8,uVar9);
                      if (iVar2 != 0) {
                        iVar4 = FUN_004edb40(0);
                        if (iVar4 == 0) {
                          FUN_004cb3d0(*(undefined4 *)
                                        (*(int *)(iVar2 + 0xa464 +
                                                 (uint)*(ushort *)(iVar2 + 0xa866) * 4) + 4),
                                       _DAT_00000004,0,0);
                        }
                        else {
                          FUN_004cb370(0);
                        }
                        FUN_004de930();
                      }
                      uVar5 = uVar5 + 1;
                    } while (uVar5 < *(uint *)(DAT_006ba7d4 + 0x28));
                  }
                }
              }
              else {
                FUN_004a6f20();
              }
            }
            else {
              iVar2 = 0;
              do {
                iVar2 = (int)(9 / (longlong)iVar2) + 1;
              } while (iVar2 < 10);
            }
          }
          else {
            *(bool *)(DAT_006ba7cc + 0x29c2d) = *(char *)(DAT_006ba7cc + 0x29c2d) == '\0';
          }
        }
        else {
          *(bool *)(DAT_006ba7cc + 0x29c2c) = *(char *)(DAT_006ba7cc + 0x29c2c) == '\0';
        }
      }
      else {
        *(bool *)(*(int *)(DAT_006ba7cc + 0x8564) + 0x969) =
             *(char *)(*(int *)(DAT_006ba7cc + 0x8564) + 0x969) == '\0';
      }
    }
    else if ((*(char *)(DAT_006ba7cc + 0x29bdc) == '\0') &&
            (iVar2 = FUN_005ca290(*(undefined4 *)(DAT_006ba7d8 + 8)), iVar2 != 0)) {
      FUN_00438c20();
      FUN_004382a0(local_648,local_644);
      FUN_00438ca0();
    }
  }
  ExceptionList = local_c;
  return 1;
}


