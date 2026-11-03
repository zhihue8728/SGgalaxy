
void __fastcall FUN_0059e110(int param_1)

{
  byte *pbVar1;
  char cVar2;
  byte bVar3;
  char *pcVar4;
  byte *pbVar5;
  byte *pbVar6;
  int iVar7;
  bool bVar8;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063aa38;
  local_c = ExceptionList;
  if (*(char *)(param_1 + 0x1698) != '\0') {
    return;
  }
  ExceptionList = &local_c;
  FUN_005a8ee0();
  pcVar4 = (char *)(param_1 + 0x2f4);
  local_4 = 0;
  do {
    cVar2 = *pcVar4;
    pcVar4 = pcVar4 + 1;
  } while (cVar2 != '\0');
  if (1 < (uint)((int)pcVar4 - (param_1 + 0x2f5))) {
    pcVar4 = (char *)(param_1 + 0x60c);
    do {
      cVar2 = *pcVar4;
      pcVar4 = pcVar4 + 1;
    } while (cVar2 != '\0');
    if (1 < (uint)((int)pcVar4 - (param_1 + 0x60d))) {
      pbVar1 = (byte *)(param_1 + 0x924);
      pbVar5 = pbVar1;
      do {
        bVar3 = *pbVar5;
        pbVar5 = pbVar5 + 1;
      } while (bVar3 != 0);
      if (1 < (uint)((int)pbVar5 - (param_1 + 0x925))) {
        pbVar5 = (byte *)(param_1 + 0xc3c);
        pbVar6 = pbVar1;
        do {
          bVar3 = *pbVar6;
          bVar8 = bVar3 < *pbVar5;
          if (bVar3 != *pbVar5) {
LAB_0059e1e0:
            iVar7 = (1 - (uint)bVar8) - (uint)(bVar8 != 0);
            goto LAB_0059e1e5;
          }
          if (bVar3 == 0) break;
          bVar3 = pbVar6[1];
          bVar8 = bVar3 < pbVar5[1];
          if (bVar3 != pbVar5[1]) goto LAB_0059e1e0;
          pbVar6 = pbVar6 + 2;
          pbVar5 = pbVar5 + 2;
        } while (bVar3 != 0);
        iVar7 = 0;
LAB_0059e1e5:
        if (iVar7 == 0) {
          FUN_005a8f80(7);
          FUN_005a9110(param_1 + 0x2f4);
          FUN_005a9110((char *)(param_1 + 0x60c));
          FUN_005a9110(pbVar1);
          FUN_005aa1e0();
          *(undefined1 *)(param_1 + 0x1698) = 1;
          *(undefined1 *)(param_1 + 0x1df0) = 1;
          FUN_00598020(1);
          FUN_0059af90(&DAT_0064c756,0);
          goto LAB_0059e28c;
        }
      }
    }
  }
  FUN_00598020(0);
  FUN_0059af90("Failed to confirm password",1);
  FUN_005ecde0();
  *(undefined1 *)(param_1 + 0x1698) = 0;
  *(undefined1 *)(param_1 + 0x1df0) = 0;
LAB_0059e28c:
  local_4 = 0xffffffff;
  FUN_005a8f50();
  ExceptionList = local_c;
  return;
}


