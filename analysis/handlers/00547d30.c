
undefined4 FUN_00547d30(byte *param_1,undefined4 param_2)

{
  byte *pbVar1;
  char cVar2;
  undefined1 uVar3;
  undefined4 uVar4;
  undefined4 *puVar5;
  ushort *puVar6;
  uint uVar7;
  int local_1c;
  undefined4 local_18;
  uint local_14;
  byte *local_10;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_00634928;
  local_c = ExceptionList;
  local_10 = param_1;
  local_14 = (uint)*param_1;
  local_18 = param_2;
  local_4 = 0;
  local_1c = 1;
  ExceptionList = &local_c;
  cVar2 = FUN_005a8680(param_1);
  if (cVar2 == '\x01') {
    puVar5 = (undefined4 *)FUN_00551e90();
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 4;
    uVar4 = FUN_005a86b0(pbVar1);
    *puVar5 = uVar4;
    FUN_005a8da0(puVar5 + 1,0x80,&DAT_00652650);
    *(undefined1 *)(puVar5 + 0x41) = 0;
    *(undefined1 *)((int)puVar5 + 0x105) = 0;
    puVar6 = (ushort *)FUN_00438240(&param_2);
    *(ushort *)((int)puVar5 + 0x106) = *puVar6;
    *(char *)(puVar5 + 0x42) = (char)puVar6[1];
    param_1._1_1_ = (byte)(*puVar6 >> 8);
    *(ushort *)((int)puVar5 + 0x10a) =
         (*puVar6 >> 3 & 0x1f) << (DAT_00c36e16 & 0x1f) |
         (ushort)(param_1._1_1_ >> (DAT_00c36dcc == 0) + 2) << 5 |
         (ushort)(byte)((byte)puVar6[1] >> 3);
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 4;
    uVar4 = FUN_005a86b0(pbVar1);
    puVar5[0x44] = uVar4;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    uVar3 = FUN_005a8680(pbVar1);
    *(undefined1 *)(puVar5 + 0x43) = uVar3;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 2;
    uVar7 = FUN_005a8690(pbVar1);
    puVar5[0x54] = uVar7 & 0xffff;
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 2;
    uVar7 = FUN_005a8690(pbVar1);
    puVar5[0x55] = uVar7 & 0xffff;
    FUN_005a9ff0(puVar5 + 0x45,local_10,&local_1c);
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 1;
    uVar3 = FUN_005a8680(pbVar1);
    *(undefined1 *)(puVar5 + 0x4c) = uVar3;
    FUN_005aa060(puVar5 + 0x4d,local_10,&local_1c);
  }
  else if (cVar2 == '\x02') {
    pbVar1 = local_10 + local_1c;
    local_1c = local_1c + 4;
    uVar4 = FUN_005a86b0(pbVar1);
    FUN_00551eb0(uVar4);
    ExceptionList = local_c;
    return 1;
  }
  ExceptionList = local_c;
  return 1;
}


