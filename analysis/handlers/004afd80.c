
void FUN_004afd80(byte *param_1,undefined4 param_2)

{
  byte bVar1;
  uint uVar2;
  undefined4 *puVar3;
  uint uVar4;
  byte *pbVar5;
  int iVar6;
  int iVar7;
  byte *pbVar8;
  bool bVar9;
  undefined1 local_144 [4];
  undefined4 *local_140;
  undefined4 *local_13c;
  int local_138;
  uint local_134;
  undefined **local_130;
  int local_12c;
  undefined4 local_128;
  uint local_124;
  byte *local_120;
  undefined4 local_118;
  undefined1 local_114 [8];
  byte local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062c506;
  local_c = ExceptionList;
  local_140 = (undefined4 *)0x0;
  local_13c = (undefined4 *)0x0;
  local_138 = 0;
  local_130 = CReceivedPacket::vftable;
  local_120 = param_1;
  local_124 = (uint)*param_1;
  local_12c = 0;
  local_128 = param_2;
  local_4 = 1;
  ExceptionList = &local_c;
  FUN_005a8da0(local_10c,0x100,"fldcuo");
  pbVar8 = local_120 + local_12c;
  local_12c = local_12c + 1;
  uVar4 = FUN_005a8680(pbVar8);
  uVar4 = uVar4 & 0xff;
  uVar2 = uVar4;
  iVar6 = local_12c;
  for (; local_134 = uVar2, uVar4 != 0; uVar4 = uVar4 - 1) {
    local_12c = iVar6 + 4;
    local_118 = FUN_005a86b0(local_120 + iVar6);
    puVar3 = local_13c;
    if ((local_140 == (undefined4 *)0x0) ||
       ((uint)(local_138 - (int)local_140 >> 2) <= (uint)((int)local_13c - (int)local_140 >> 2))) {
      if (local_13c < local_140) {
        FUN_00609e03();
      }
      FUN_004aeee0(local_114,local_144,puVar3,&local_118);
    }
    else {
      *local_13c = local_118;
      local_13c = local_13c + 1;
    }
    uVar2 = local_134;
    iVar6 = local_12c;
  }
  local_12c = iVar6;
  pbVar5 = (byte *)FUN_004ee140();
  pbVar8 = local_10c;
  do {
    bVar1 = *pbVar8;
    bVar9 = bVar1 < *pbVar5;
    if (bVar1 != *pbVar5) {
LAB_004afed8:
      iVar6 = (1 - (uint)bVar9) - (uint)(bVar9 != 0);
      goto LAB_004afedd;
    }
    if (bVar1 == 0) break;
    bVar1 = pbVar8[1];
    bVar9 = bVar1 < pbVar5[1];
    if (bVar1 != pbVar5[1]) goto LAB_004afed8;
    pbVar8 = pbVar8 + 2;
    pbVar5 = pbVar5 + 2;
  } while (bVar1 != 0);
  iVar6 = 0;
LAB_004afedd:
  uVar4 = 0;
  if (0 < (int)uVar2) {
    do {
      if ((local_140 == (undefined4 *)0x0) ||
         ((uint)((int)local_13c - (int)local_140 >> 2) <= uVar4)) {
        FUN_00609e03();
      }
      iVar7 = FUN_005ca290(local_140[uVar4]);
      if (iVar7 != 0) {
        if (iVar6 == 0) {
          if (*(char *)(iVar7 + 0x69) == '\0') {
            _strcpy_s((char *)(iVar7 + 0xb9),0xd,(char *)local_10c);
            FUN_004c68a0(1);
            FUN_004c67a0();
            if (((*(uint *)(iVar7 + 0x15c) & 0x200000) != 0) &&
               (*(int *)(*(int *)(iVar7 + 0xa868 + (uint)*(ushort *)(iVar7 + 0xac6a) * 4) + 4) ==
                0x33)) {
              FUN_005d15b0(*(undefined4 *)(iVar7 + 4));
            }
          }
        }
        else if (*(char *)(iVar7 + 0x69) == '\0') {
          _strcpy_s((char *)(iVar7 + 0xb9),0xd,(char *)local_10c);
        }
        else {
          _strcpy_s((char *)(iVar7 + 0xb9),0xd,(char *)local_10c);
          FUN_004c68a0(0);
          FUN_004c67d0(*(undefined4 *)(iVar7 + 0x354));
          FUN_005c4ff0(iVar7);
        }
      }
      uVar4 = uVar4 + 1;
    } while ((int)uVar4 < (int)local_134);
  }
  local_130 = CReceivedPacket::vftable;
  if (local_140 != (undefined4 *)0x0) {
                    /* WARNING: Subroutine does not return */
    _free(local_140);
  }
  ExceptionList = local_c;
  return;
}


