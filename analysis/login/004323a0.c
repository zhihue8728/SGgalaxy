
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __fastcall FUN_004323a0(int param_1)

{
  byte *pbVar1;
  char cVar2;
  byte bVar3;
  char *pcVar4;
  byte *pbVar5;
  byte *pbVar6;
  int iVar7;
  bool bVar8;
  undefined4 uVar9;
  void *local_c;
  undefined1 *puStack_8;
  uint local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_006267f6;
  local_c = ExceptionList;
  if (*(char *)(param_1 + 0x2991) == '\0') {
    return;
  }
  ExceptionList = &local_c;
  FUN_005a8ee0();
  local_4 = 0;
  FUN_0058c730();
  pcVar4 = (char *)(param_1 + 0x2e70);
  local_4 = CONCAT31(local_4._1_3_,1);
  do {
    cVar2 = *pcVar4;
    pcVar4 = pcVar4 + 1;
  } while (cVar2 != '\0');
  if (1 < (uint)((int)pcVar4 - (param_1 + 0x2e71))) {
    pcVar4 = (char *)(param_1 + 0x3188);
    do {
      cVar2 = *pcVar4;
      pcVar4 = pcVar4 + 1;
    } while (cVar2 != '\0');
    if (1 < (uint)((int)pcVar4 - (param_1 + 0x3189))) {
      pbVar1 = (byte *)(param_1 + 0x34a0);
      pbVar5 = pbVar1;
      do {
        bVar3 = *pbVar5;
        pbVar5 = pbVar5 + 1;
      } while (bVar3 != 0);
      if (1 < (uint)((int)pbVar5 - (param_1 + 0x34a1))) {
        pbVar5 = (byte *)(param_1 + 0x37b8);
        pbVar6 = pbVar1;
        do {
          bVar3 = *pbVar6;
          bVar8 = bVar3 < *pbVar5;
          if (bVar3 != *pbVar5) {
LAB_00432480:
            iVar7 = (1 - (uint)bVar8) - (uint)(bVar8 != 0);
            goto LAB_00432485;
          }
          if (bVar3 == 0) break;
          bVar3 = pbVar6[1];
          bVar8 = bVar3 < pbVar5[1];
          if (bVar3 != pbVar5[1]) goto LAB_00432480;
          pbVar6 = pbVar6 + 2;
          pbVar5 = pbVar5 + 2;
        } while (bVar3 != 0);
        iVar7 = 0;
LAB_00432485:
        if (iVar7 == 0) {
          FUN_005a8f80(7);
          FUN_005a9110(param_1 + 0x2e70);
          FUN_005a9110((char *)(param_1 + 0x3188));
          FUN_005a9110(pbVar1);
          FUN_005aa1e0();
          *(undefined4 *)(param_1 + 0x2834) = 5;
          FUN_005ecf00(0);
          uVar9 = 0;
          goto LAB_0043251f;
        }
      }
    }
  }
  (**(code **)(*DAT_006ba7c4 + 0xc))(0x2e,0x7f,0x40);
  FUN_0058c9f0(0,"Failed to confirm password",0xff,0xff,0xff,0x10);
  FUN_005ecf00(1);
  uVar9 = 1;
LAB_0043251f:
  FUN_005ecf00(uVar9);
  local_4 = local_4 & 0xffffff00;
  FUN_0058c7b0();
  local_4 = 0xffffffff;
  FUN_005a8f50();
  ExceptionList = local_c;
  return;
}


