
void __thiscall FUN_005c8ff0(int param_1,int param_2,int param_3)

{
  char cVar1;
  uint uVar2;
  undefined2 uVar3;
  uint uVar4;
  char *pcVar5;
  int iVar6;
  int iVar7;
  undefined8 uVar8;
  uint local_19c [2];
  undefined2 local_194 [4];
  void *local_18c;
  undefined4 local_17c;
  uint local_178;
  uint local_174;
  undefined1 local_170;
  uint local_16c;
  void *local_164;
  undefined4 local_154;
  uint local_150;
  undefined2 local_14c;
  undefined2 local_14a;
  undefined2 local_148;
  undefined8 local_144;
  undefined2 local_13c;
  undefined2 local_13a;
  undefined2 local_138;
  undefined2 local_136;
  undefined2 local_134;
  undefined1 local_132;
  undefined2 local_130;
  undefined2 local_12e;
  void *local_128;
  undefined4 local_118;
  uint local_114;
  char local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063e881;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  uVar3 = FUN_004338e0(param_2,param_3);
  *(undefined2 *)(param_1 + 8) = uVar3;
  FUN_005c7f00();
  local_150 = 0xf;
  local_154 = 0;
  local_164 = (void *)((uint)local_164 & 0xffffff00);
  local_114 = 0xf;
  local_118 = 0;
  local_128 = (void *)((uint)local_128 & 0xffffff00);
  local_178 = 0xf;
  local_17c = 0;
  local_18c = (void *)((uint)local_18c & 0xffffff00);
  uVar4 = *(uint *)(param_1 + 0x28);
  local_4 = 2;
  if (uVar4 < *(uint *)(param_1 + 0x24)) {
    FUN_00609e03();
  }
  uVar2 = *(uint *)(param_1 + 0x24);
  if (*(uint *)(param_1 + 0x28) < uVar2) {
    FUN_00609e03();
  }
  FUN_005c7a30(local_19c,param_1 + 0x20,uVar2,param_1 + 0x20,uVar4);
  uVar4 = FUN_005a8690(param_2);
  iVar6 = 2;
  for (uVar4 = uVar4 & 0xffff; uVar4 != 0; uVar4 = uVar4 - 1) {
    local_194[0] = FUN_005a8690(iVar6 + param_2);
    FUN_005a8da0(local_10c,0x100,"uniuni1");
    pcVar5 = local_10c;
    do {
      cVar1 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar1 != '\0');
    FUN_004026a0(local_10c,(int)pcVar5 - (int)(local_10c + 1));
    FUN_005c8e20(local_194);
    iVar6 = iVar6 + 2;
  }
  uVar4 = *(uint *)(param_1 + 0x18);
  if (uVar4 < *(uint *)(param_1 + 0x14)) {
    FUN_00609e03();
  }
  uVar2 = *(uint *)(param_1 + 0x14);
  local_19c[0] = uVar2;
  if (*(uint *)(param_1 + 0x18) < uVar2) {
    FUN_00609e03();
  }
  if (uVar2 != uVar4) {
    uVar2 = *(uint *)(param_1 + 0x18);
    iVar7 = ((int)(uVar2 - uVar4) / 0x68) * 0x68 + local_19c[0];
    if (uVar4 != uVar2) {
      local_19c[0] = local_19c[0] - uVar4;
      do {
        FUN_00445380(uVar4);
        uVar4 = uVar4 + 0x68;
      } while (uVar4 != uVar2);
    }
    FUN_005c6ca0(iVar7,*(undefined4 *)(param_1 + 0x18),param_1 + 0x10,param_1);
    *(int *)(param_1 + 0x18) = iVar7;
  }
  iVar7 = iVar6 + 2;
  uVar4 = FUN_005a8690(iVar6 + param_2);
  for (uVar4 = uVar4 & 0xffff; uVar4 != 0; uVar4 = uVar4 - 1) {
    local_174 = FUN_005a8680(iVar7 + param_2);
    local_174 = local_174 & 0xff;
    local_170 = FUN_005a8680(iVar7 + 1 + param_2);
    local_16c = FUN_005a8690(iVar7 + 2 + param_2);
    local_16c = local_16c & 0xffff;
    FUN_005a8da0(local_10c,0x100,"uniuni2");
    pcVar5 = local_10c;
    do {
      cVar1 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar1 != '\0');
    FUN_004026a0(local_10c,(int)pcVar5 - (int)(local_10c + 1));
    local_14c = FUN_005a8690(iVar7 + 4 + param_2);
    local_14a = FUN_005a8690(iVar7 + 6 + param_2);
    local_148 = FUN_005a8690(iVar7 + 8 + param_2);
    uVar8 = FUN_005a86e0(iVar7 + 10 + param_2);
    local_144 = uVar8;
    local_13c = FUN_005a8690(iVar7 + 0x12 + param_2);
    local_13a = FUN_005a8690(iVar7 + 0x14 + param_2);
    local_138 = FUN_005a8690(iVar7 + 0x16 + param_2);
    local_136 = FUN_005a8690(iVar7 + 0x18 + param_2);
    local_134 = FUN_005a8690(iVar7 + 0x1a + param_2);
    local_132 = FUN_005a8680(iVar7 + 0x1c + param_2);
    iVar6 = iVar7 + 0x1f;
    local_130 = FUN_005a8690(iVar7 + 0x1d + param_2);
    iVar7 = iVar7 + 0x21;
    local_12e = FUN_005a8690(iVar6 + param_2);
    FUN_005c8d80(&local_174);
  }
  if (iVar7 == param_3) {
    FUN_005c6230(param_2,param_3);
  }
  if (0xf < local_178) {
                    /* WARNING: Subroutine does not return */
    _free(local_18c);
  }
  local_178 = 0xf;
  local_17c = 0;
  local_18c = (void *)((uint)local_18c & 0xffffff00);
  if (0xf < local_114) {
                    /* WARNING: Subroutine does not return */
    _free(local_128);
  }
  local_114 = 0xf;
  local_118 = 0;
  local_128 = (void *)((uint)local_128 & 0xffffff00);
  if (0xf < local_150) {
                    /* WARNING: Subroutine does not return */
    _free(local_164);
  }
  ExceptionList = local_c;
  return;
}


