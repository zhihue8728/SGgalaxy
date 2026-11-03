
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void FUN_004b4720(byte *param_1,undefined4 param_2)

{
  byte *pbVar1;
  uint uVar2;
  int local_1250;
  undefined4 local_124c;
  uint local_1248;
  byte *local_1244;
  int local_1240;
  undefined1 local_123c [4];
  void *local_1238;
  undefined4 local_1228;
  uint local_1224;
  uint uStack_1220;
  undefined2 uStack_121c;
  uint uStack_1214;
  uint uStack_1210;
  uint uStack_120c;
  uint uStack_1208;
  uint local_f20;
  uint local_f1c;
  undefined4 uStack_10;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062cb01;
  local_c = ExceptionList;
  uStack_10 = 0x4b473f;
  if (DAT_00c3499e == '\0') {
    ExceptionList = &local_c;
    FUN_00427aa0();
    local_1224 = 0xf;
    local_1228 = 0;
    local_1238 = (void *)((uint)local_1238 & 0xffffff00);
    local_1244 = param_1;
    local_1248 = (uint)*param_1;
    local_124c = param_2;
    local_4 = 2;
    local_1250 = 1;
    uVar2 = FUN_005a8680(param_1);
    pbVar1 = local_1244 + local_1250;
    local_1250 = local_1250 + 1;
    local_f1c = FUN_005a8680(pbVar1);
    local_f1c = local_f1c & 0xff;
    pbVar1 = local_1244 + local_1250;
    local_1250 = local_1250 + 1;
    local_f20 = uVar2 & 0xff;
    uVar2 = FUN_005a8680(pbVar1);
    for (uVar2 = uVar2 & 0xff; uVar2 != 0; uVar2 = uVar2 - 1) {
      FUN_005a9ff0(local_123c,local_1244,&local_1250);
      pbVar1 = local_1244 + local_1250;
      local_1250 = local_1250 + 1;
      uStack_1220 = FUN_005a8680(pbVar1);
      uStack_1220 = uStack_1220 & 0xff;
      pbVar1 = local_1244 + local_1250;
      local_1250 = local_1250 + 2;
      uStack_121c = FUN_005a8690(pbVar1);
      pbVar1 = local_1244 + local_1250;
      local_1250 = local_1250 + 2;
      uStack_1214 = FUN_005a8690(pbVar1);
      uStack_1214 = uStack_1214 & 0xffff;
      pbVar1 = local_1244 + local_1250;
      local_1250 = local_1250 + 1;
      uStack_1210 = FUN_005a8680(pbVar1);
      uStack_1210 = uStack_1210 & 0xff;
      pbVar1 = local_1244 + local_1250;
      local_1250 = local_1250 + 1;
      uStack_120c = FUN_005a8680(pbVar1);
      uStack_120c = uStack_120c & 0xff;
      pbVar1 = local_1244 + local_1250;
      local_1250 = local_1250 + 1;
      uStack_1208 = FUN_005a8680(pbVar1);
      uStack_1208 = uStack_1208 & 0xff;
      FUN_004b46a0(local_123c);
    }
    DAT_00c3499e = 1;
    if (local_1240 == 0) {
      local_1240 = 0;
    }
    else {
      local_1240 = local_1240 + 4;
    }
    FUN_004280e0(local_1240);
    DAT_00c3499e = '\0';
    if (0xf < local_1224) {
                    /* WARNING: Subroutine does not return */
      _free(local_1238);
    }
    local_1224 = 0xf;
    local_1228 = 0;
    local_1238 = (void *)((uint)local_1238 & 0xffffff00);
    local_4 = 0xffffffff;
    FUN_00427b40(CReceivedPacket::vftable);
  }
  ExceptionList = local_c;
  return;
}


