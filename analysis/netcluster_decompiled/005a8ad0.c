// xrefs to FUN_005a8ad0: 005a9439(005a9340) 

int FUN_005a8ad0(undefined1 *param_1,int param_2,undefined1 *param_3)

{
  byte bVar1;
  undefined4 uVar2;
  int iVar3;
  undefined4 uVar4;
  undefined1 *puVar5;
  char cVar6;
  uint uVar7;
  undefined1 *puVar8;
  int iVar9;
  
  uVar2 = DAT_006ba7dc;
  cVar6 = '\0';
  iVar3 = 0;
  if (0 < param_2 + -1) {
    do {
      cVar6 = cVar6 + param_1[iVar3];
      iVar3 = iVar3 + 1;
    } while (iVar3 < param_2 + -1);
    if (cVar6 != '\0') {
      uVar4 = FUN_00545260(*param_1);
      FUN_0047e540(uVar2,"S_%d O_%d CheckSumError at packet No : %d\n",DAT_00d69268,uVar4);
      Beep(500,300);
      Beep(1000,300);
      Beep(500,300);
                    /* WARNING: Subroutine does not return */
      _exit(0);
    }
  }
  *param_3 = *param_1;
  bVar1 = param_1[1];
  if (0 < param_2 + -4) {
    puVar8 = param_3 + 1;
    FUN_005a8910(param_1 + 2,puVar8,param_2 + -4,&DAT_006b6918 + (uint)bVar1 * 4,1);
    iVar3 = DAT_00d6926c;
    uVar7 = 0;
    iVar9 = (param_2 + -5) / DAT_00d6926c + 1;
    puVar5 = puVar8;
    if (0 < iVar9) {
      do {
        if (bVar1 != (byte)uVar7) {
          FUN_005a8910(puVar5,puVar5,iVar3,&DAT_006b6918 + (uVar7 & 0xff) * 4,1);
        }
        uVar7 = uVar7 + 1;
        puVar5 = puVar5 + iVar3;
      } while ((int)uVar7 < iVar9);
    }
    FUN_005a8910(puVar8,puVar8,param_2 + -4,&DAT_00d69274,iVar3);
    iVar3 = param_2 + -3;
    cVar6 = '\0';
    iVar9 = 0;
    param_3[param_2 + -3] = 0;
    uVar2 = DAT_006ba7dc;
    if (0 < iVar3) {
      do {
        cVar6 = cVar6 + param_3[iVar9];
        iVar9 = iVar9 + 1;
      } while (iVar9 < iVar3);
    }
    if ((char)(param_1[param_2 + -1] + cVar6) != '\0') {
      uVar4 = FUN_00545260(*param_1);
      FUN_0047e540(uVar2,"S_%d O_%d CheckSumOrigError at packet No : %d\n",DAT_00d69268,uVar4);
      Beep(1000,100);
    }
    return iVar3;
  }
  param_3[param_2 + -3] = 0;
  return param_2 + -3;
}


