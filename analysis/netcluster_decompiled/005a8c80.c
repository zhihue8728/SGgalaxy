// xrefs to FUN_005a8c80: 005a92e4(005a9240) 

int FUN_005a8c80(undefined1 *param_1,int param_2,undefined1 *param_3)

{
  byte bVar1;
  int iVar2;
  undefined1 *puVar3;
  int iVar4;
  char cVar5;
  uint uVar6;
  char local_1;
  
  *param_3 = *param_1;
  bVar1 = DAT_00d69270;
  cVar5 = DAT_00d69270 + 1;
  param_3[1] = DAT_00d69270;
  DAT_00d69270 = cVar5;
  iVar4 = DAT_00d6926c;
  cVar5 = '\0';
  iVar2 = 0;
  local_1 = '\0';
  if (0 < param_2) {
    do {
      cVar5 = cVar5 + param_1[iVar2];
      iVar2 = iVar2 + 1;
      local_1 = cVar5;
    } while (iVar2 < param_2);
  }
  if (0 < param_2 + -1) {
    FUN_005a8910(param_1 + 1,param_3 + 2,param_2 + -1,&DAT_00d69274,DAT_00d6926c);
    uVar6 = 0;
    iVar2 = (param_2 + -2) / iVar4 + 1;
    if (0 < iVar2) {
      puVar3 = param_3 + 2;
      do {
        if (bVar1 != (byte)uVar6) {
          FUN_005a8910(puVar3,puVar3,iVar4,&DAT_006b6918 + (uVar6 & 0xff) * 4,1);
        }
        uVar6 = uVar6 + 1;
        puVar3 = puVar3 + iVar4;
      } while ((int)uVar6 < iVar2);
    }
    FUN_005a8910(param_3 + 2,param_3 + 2,param_2 + -1,&DAT_006b6918 + (uint)bVar1 * 4,1);
    cVar5 = '\0';
    iVar4 = 0;
    if (-1 < param_2) {
      do {
        cVar5 = cVar5 + param_3[iVar4];
        iVar4 = iVar4 + 1;
      } while (iVar4 <= param_2);
    }
    param_3[param_2 + 1] = -cVar5;
    param_3[param_2 + 2] = -local_1;
    param_3[param_2 + 3] = 0;
    return param_2 + 3;
  }
  param_3[param_2 + 1] = 0;
  return param_2 + 1;
}


