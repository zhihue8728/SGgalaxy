
void FUN_00549d30(int param_1)

{
  char cVar1;
  int iVar2;
  undefined1 uVar3;
  undefined4 uVar4;
  uint uVar5;
  char *pcVar6;
  char local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  iVar2 = DAT_006ba7d8;
  puStack_8 = &LAB_006349fb;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 8) = uVar4;
  FUN_005a86b0();
  FUN_004ee830();
  FUN_005a86b0();
  FUN_004ee8c0();
  uVar5 = FUN_005a8680();
  *(uint *)(iVar2 + 0x450) = uVar5 & 0xff;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 0x454) = uVar4;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 0x458) = uVar4;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 0x45c) = uVar4;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 0x460) = uVar4;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 0x464) = uVar4;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 0x468) = uVar4;
  uVar3 = FUN_005a8680(param_1 + 0x25);
  *(undefined1 *)(iVar2 + 0x470) = uVar3;
  uVar3 = FUN_005a8680(param_1 + 0x26);
  *(undefined1 *)(iVar2 + 0x46c) = uVar3;
  uVar3 = FUN_005a8680(param_1 + 0x27);
  *(undefined1 *)(iVar2 + 0x46d) = uVar3;
  uVar3 = FUN_005a8680(param_1 + 0x28);
  *(undefined1 *)(iVar2 + 0x46e) = uVar3;
  uVar3 = FUN_005a8680(param_1 + 0x29);
  *(undefined1 *)(iVar2 + 0x46f) = uVar3;
  uVar3 = FUN_005a8680(param_1 + 0x2a);
  *(undefined1 *)(iVar2 + 0x471) = uVar3;
  uVar5 = FUN_005a8690(param_1 + 0x2b);
  *(uint *)(iVar2 + 0x474) = uVar5 & 0xffff;
  uVar5 = FUN_005a8690(param_1 + 0x2d);
  *(uint *)(iVar2 + 0x478) = uVar5 & 0xffff;
  uVar3 = FUN_005a8680(param_1 + 0x2f);
  *(undefined1 *)(iVar2 + 0x47c) = uVar3;
  uVar3 = FUN_005a8680();
  *(undefined1 *)(iVar2 + 0x47e) = uVar3;
  uVar4 = FUN_005a86b0();
  *(undefined4 *)(iVar2 + 0x480) = uVar4;
  FUN_005a86b0();
  FUN_004edc80();
  uVar5 = FUN_005a8690();
  *(uint *)(iVar2 + 0x44c) = uVar5 & 0xffff;
  uVar3 = FUN_005a8680();
  *(undefined1 *)(iVar2 + 0x47f) = uVar3;
  FUN_005a8680();
  if (DAT_006ba7cc != 0) {
    FUN_005a6880();
  }
  uVar3 = FUN_005a8680();
  *(undefined1 *)(iVar2 + 0x47d) = uVar3;
  FUN_005a8da0();
  pcVar6 = local_10c;
  do {
    cVar1 = *pcVar6;
    pcVar6 = pcVar6 + 1;
  } while (cVar1 != '\0');
  FUN_004026a0(local_10c,(int)pcVar6 - (int)(local_10c + 1));
  FUN_004ab080();
  uVar3 = FUN_005a8680();
  *(undefined1 *)(iVar2 + 0x4a4) = uVar3;
  uVar3 = FUN_005a8680();
  *(undefined1 *)(iVar2 + 0x4a5) = uVar3;
  if (DAT_006ba7cc != 0) {
    FUN_0047fb00();
    FUN_004a30d0();
    FUN_004a3130();
    if (4 < *(byte *)(iVar2 + 0x47c)) {
      FUN_0049e8c0();
    }
  }
  ExceptionList = local_c;
  return;
}


