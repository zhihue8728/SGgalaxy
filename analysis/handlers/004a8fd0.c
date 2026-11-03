
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __thiscall FUN_004a8fd0(int param_1,char *param_2,uint param_3)

{
  undefined4 uVar1;
  uint uVar2;
  int iVar3;
  byte *pbVar4;
  int iVar5;
  int iVar6;
  uint uStack_10034;
  uint uStack_10030;
  int iStack_1002c;
  uint uStack_10028;
  undefined4 uStack_10024;
  undefined **ppuStack_10020;
  int iStack_1001c;
  uint uStack_10018;
  uint uStack_10014;
  byte *pbStack_10010;
  byte abStack_1000c [65532];
  undefined4 uStack_10;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062c10b;
  local_c = ExceptionList;
  uStack_10 = 0x4a8fef;
  uStack_10034 = 0x10000;
  iStack_1002c = param_1;
  if (*param_2 == '\0') {
    pbVar4 = (byte *)(param_2 + 1);
    ExceptionList = &local_c;
  }
  else {
    ExceptionList = &local_c;
    FUN_005fc960(abStack_1000c,&uStack_10034,param_2 + 3,CONCAT11(param_2[1],param_2[2]));
    pbVar4 = abStack_1000c;
    param_3 = uStack_10034;
  }
  uStack_10014 = (uint)*pbVar4;
  uStack_10018 = param_3;
  ppuStack_10020 = CReceivedPacketEx::vftable;
  local_4 = 0;
  uStack_10030 = 0;
  iStack_1001c = 1;
  pbStack_10010 = pbVar4;
  FUN_005a8680(pbVar4);
  iStack_1001c = 5;
  uVar1 = FUN_005a86b0(pbVar4 + 1);
  iStack_1001c = 7;
  uStack_10024 = uVar1;
  uStack_10028 = FUN_005a8690(pbVar4 + 5);
  uStack_10028 = uStack_10028 & 0xffff;
  *(undefined4 *)(param_1 + 0x29be4) = uVar1;
  iVar3 = 0;
  if (uStack_10028 != 0) {
    iVar5 = 7;
    do {
      iVar6 = iVar5 + 2;
      iStack_1001c = iVar6;
      uVar2 = FUN_005a8690(pbVar4 + iVar5);
      uVar2 = uVar2 & 0xffff;
      uStack_10030 = uStack_10030 + uVar2;
      if (param_3 < uStack_10030) {
        ExceptionList = local_c;
        return;
      }
      FUN_004a8ed0(pbVar4 + iVar6,uVar2,uStack_10024);
      iVar3 = iVar3 + 1;
      iVar5 = iVar6 + uVar2;
    } while (iVar3 < (int)uStack_10028);
  }
  ExceptionList = local_c;
  return;
}


