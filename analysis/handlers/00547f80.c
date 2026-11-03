
undefined4 FUN_00547f80(byte *param_1,undefined4 param_2)

{
  byte *pbVar1;
  undefined1 uVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  uint uVar6;
  int iVar7;
  uint uVar8;
  undefined4 uVar9;
  int *piVar10;
  undefined4 *puVar11;
  int iVar12;
  int local_1c;
  undefined4 local_18;
  uint local_14;
  byte *local_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00634948;
  pvStack_c = ExceptionList;
  local_10 = param_1;
  local_14 = (uint)*param_1;
  local_18 = param_2;
  iVar12 = 0;
  local_4 = 0;
  local_1c = 1;
  ExceptionList = &pvStack_c;
  uVar6 = FUN_005a8680(param_1);
  uVar6 = uVar6 & 0xff;
  FUN_00552100(uVar6);
  iVar7 = local_1c;
  for (; uVar6 != 0; uVar6 = uVar6 - 1) {
    local_1c = iVar7 + 4;
    piVar10 = (int *)(*(int *)(DAT_006ba80c + 0x10) + iVar12);
    iVar7 = FUN_005a86b0(local_10 + iVar7);
    *piVar10 = iVar7;
    FUN_005a8da0(piVar10 + 1,0x80,&DAT_00652650);
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    uVar2 = FUN_005a8680(pbVar1);
    *(undefined1 *)(piVar10 + 0x41) = uVar2;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    uVar2 = FUN_005a8680(pbVar1);
    *(undefined1 *)((int)piVar10 + 0x105) = uVar2;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    bVar3 = FUN_005a8680(pbVar1);
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    bVar4 = FUN_005a8680(pbVar1);
    param_1._0_2_ = CONCAT11(bVar4,bVar3);
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    bVar5 = FUN_005a8680(pbVar1);
    *(undefined2 *)((int)piVar10 + 0x106) = param_1._0_2_;
    *(byte *)(piVar10 + 0x42) = bVar5;
    *(ushort *)((int)piVar10 + 0x10a) =
         (ushort)(bVar3 >> 3) << (DAT_00c36e16 & 0x1f) |
         (ushort)(bVar4 >> (DAT_00c36dcc == 0) + 2) << 5 | (ushort)(bVar5 >> 3);
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 4;
    iVar7 = FUN_005a86b0(pbVar1);
    piVar10[0x44] = iVar7;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    uVar2 = FUN_005a8680(pbVar1);
    *(undefined1 *)(piVar10 + 0x43) = uVar2;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 2;
    uVar8 = FUN_005a8690(pbVar1);
    piVar10[0x54] = uVar8 & 0xffff;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 2;
    uVar8 = FUN_005a8690(pbVar1);
    piVar10[0x55] = uVar8 & 0xffff;
    iVar7 = *piVar10;
    if (iVar7 == 7 || iVar7 == 8) {
      FUN_004ba4d0(iVar7 + -7,*(undefined1 *)((int)piVar10 + 0x106),
                   *(undefined1 *)((int)piVar10 + 0x107),(char)piVar10[0x42]);
    }
    iVar12 = iVar12 + 0x168;
    iVar7 = local_1c;
  }
  local_1c = iVar7 + 2;
  uVar6 = FUN_005a8690(local_10 + iVar7);
  iVar12 = local_1c;
  for (uVar6 = uVar6 & 0xffff; uVar6 != 0; uVar6 = uVar6 - 1) {
    local_1c = iVar12 + 4;
    uVar9 = FUN_005a86b0(local_10 + iVar12);
    iVar12 = FUN_00551ec0(uVar9);
    if (iVar12 == 0) {
      uVar9 = FUN_004ee140();
      FUN_0047e540(DAT_006ba7dc,"%s Wrong Nation ID\n",uVar9);
    }
    FUN_005a9ff0(iVar12 + 0x114,local_10,&local_1c);
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    uVar2 = FUN_005a8680(pbVar1);
    *(undefined1 *)(iVar12 + 0x130) = uVar2;
    FUN_005aa060(iVar12 + 0x134,local_10,&local_1c);
    iVar12 = local_1c;
  }
  local_1c = iVar12 + 2;
  uVar6 = FUN_005a8690(local_10 + iVar12);
  uVar6 = uVar6 & 0xffff;
  FUN_00551f40(uVar6);
  FUN_00551f80();
  if (uVar6 != 0) {
    iVar12 = 0;
    do {
      pbVar1 = local_10 + local_1c;
      puVar11 = (undefined4 *)(*(int *)(DAT_006ba80c + 0x14) + iVar12);
      local_1c = local_1c + 4;
      uVar9 = FUN_005a86b0(pbVar1);
      *puVar11 = uVar9;
      pbVar1 = local_10 + local_1c;
      local_1c = local_1c + 4;
      uVar9 = FUN_005a86b0(pbVar1);
      puVar11[1] = uVar9;
      pbVar1 = local_10 + local_1c;
      local_1c = local_1c + 1;
      uVar2 = FUN_005a8680(pbVar1);
      *(undefined1 *)(puVar11 + 2) = uVar2;
      iVar7 = FUN_00551ec0(puVar11[1]);
      if (iVar7 != 0) {
        *(int *)(iVar7 + 0x158) = *(int *)(iVar7 + 0x158) + (uint)*(byte *)(puVar11 + 2);
        *(int *)(iVar7 + 0x15c) = *(int *)(iVar7 + 0x15c) + 1;
      }
      iVar12 = iVar12 + 0xc;
      uVar6 = uVar6 - 1;
    } while (uVar6 != 0);
  }
  FUN_004f2c50();
  ExceptionList = pvStack_c;
  return 1;
}


