
void __fastcall FUN_004b2610(undefined4 param_1)

{
  int iVar1;
  char cVar2;
  int iVar3;
  char *pcVar4;
  int iVar5;
  int iVar6;
  uint uVar7;
  uint uVar8;
  uint local_528;
  uint local_524;
  char local_50c [256];
  char local_40c [1024];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062c7ab;
  local_c = ExceptionList;
  if (*(int *)(DAT_006ba7c8 + 0x1c58) == 2) {
    uVar7 = 0;
    local_4 = 0;
    ExceptionList = &local_c;
    FUN_005a8da0(local_50c,0x100,"fldsr");
    _sprintf_s(local_40c,0x400,"%s has left this battle.",local_50c);
    FUN_00438e00(local_40c,
                 (ushort)(0 >> (DAT_00c36dcc == 0) + 2) << 5 |
                 (ushort)(0x1f << (DAT_00c36e16 & 0x1f)),0,0);
    iVar3 = DAT_00c34984;
    iVar1 = DAT_00c34984 + 4;
    iVar6 = 0;
    while( true ) {
      if ((*(int *)(iVar3 + 8) == 0) ||
         ((uint)((*(int *)(iVar3 + 0xc) - *(int *)(iVar3 + 8)) / 0x34) <= uVar7)) goto LAB_004b27ed;
      if ((*(int *)(iVar3 + 8) == 0) ||
         ((uint)((*(int *)(iVar3 + 0xc) - *(int *)(iVar3 + 8)) / 0x34) <= uVar7)) {
        FUN_00609e03();
      }
      pcVar4 = local_50c;
      do {
        cVar2 = *pcVar4;
        pcVar4 = pcVar4 + 1;
      } while (cVar2 != '\0');
      iVar5 = FUN_00405fc0(0,*(undefined4 *)(*(int *)(iVar3 + 8) + iVar6 + 0x14),local_50c,
                           (int)pcVar4 - (int)(local_50c + 1));
      if (iVar5 == 0) break;
      uVar7 = uVar7 + 1;
      iVar6 = iVar6 + 0x34;
    }
    uVar8 = *(uint *)(iVar3 + 8);
    if (*(uint *)(iVar3 + 0xc) < uVar8) {
      FUN_00609e03();
    }
    uVar8 = uVar7 * 0x34 + uVar8;
    if ((*(uint *)(iVar3 + 0xc) < uVar8) || (uVar8 < *(uint *)(iVar3 + 8))) {
      FUN_00609e03();
    }
    local_524 = local_524 & 0xffffff00;
    local_528 = local_528 & 0xffffff00;
    FUN_004abc10(uVar8 + 0x34,*(undefined4 *)(iVar3 + 0xc),uVar8,param_1,local_528,local_524);
    FUN_004abaa0(*(int *)(iVar3 + 0xc) + -0x34,*(int *)(iVar3 + 0xc),iVar1,param_1);
    *(int *)(iVar3 + 0xc) = *(int *)(iVar3 + 0xc) + -0x34;
LAB_004b27ed:
    FUN_00583170();
  }
  ExceptionList = local_c;
  return;
}


