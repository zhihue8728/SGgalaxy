
void FUN_00545d40(int param_1)

{
  byte bVar1;
  undefined2 uVar2;
  int iVar3;
  int iVar4;
  undefined4 uVar5;
  uint uVar6;
  CHAR local_50c [256];
  CHAR local_40c [1024];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  iVar4 = DAT_006ba7d8;
  puStack_8 = &LAB_006346bb;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  iVar3 = FUN_005a86b0(param_1);
  bVar1 = FUN_005a8680(param_1 + 4);
  if (*(int *)(iVar4 + 8) == iVar3) {
    FUN_00527bd0();
    iVar4 = 5;
    for (uVar6 = (uint)bVar1; uVar6 != 0; uVar6 = uVar6 - 1) {
      uVar2 = FUN_005a8690(iVar4 + param_1);
      FUN_00527ec0(uVar2);
      iVar4 = iVar4 + 2;
    }
  }
  else {
    iVar4 = FUN_004ee2c0(iVar3);
    if (iVar4 == 0) {
      uVar5 = FUN_004ee140(iVar3);
      wsprintfA(local_40c,"%s SET_INVENTORY on invalid ID %d. out of ",uVar5);
      uVar5 = FUN_004eda90();
      wsprintfA(local_50c,"(%d) ",uVar5);
      _strcat_s(local_40c,0x400,local_50c);
      iVar3 = 0;
      iVar4 = FUN_004eda90();
      if (0 < iVar4) {
        do {
          iVar4 = FUN_004edb40(iVar3);
          if (iVar4 != 0) {
            iVar4 = FUN_004edb40(iVar3);
            wsprintfA(local_50c,"%d, ",*(undefined4 *)(iVar4 + 4));
            _strcat_s(local_40c,0x400,local_50c);
          }
          iVar3 = iVar3 + 1;
          iVar4 = FUN_004eda90();
        } while (iVar3 < iVar4);
      }
      _strcat_s(local_40c,0x400," | ");
      uVar5 = FUN_004edae0();
      wsprintfA(local_50c,"(%d) ",uVar5);
      _strcat_s(local_40c,0x400,local_50c);
      iVar3 = 0;
      iVar4 = FUN_004edae0();
      if (0 < iVar4) {
        do {
          iVar4 = FUN_004edb70(iVar3);
          if (iVar4 != 0) {
            iVar4 = FUN_004edb70(iVar3);
            wsprintfA(local_50c,"%d, ",*(undefined4 *)(iVar4 + 4));
            _strcat_s(local_40c,0x400,local_50c);
          }
          iVar3 = iVar3 + 1;
          iVar4 = FUN_004edae0();
        } while (iVar3 < iVar4);
      }
      if (*(int *)(DAT_006ba7c8 + 0x1c58) != 2) {
        FUN_0047e540(DAT_006ba7dc,local_40c);
      }
    }
    else {
      FUN_00527bd0();
      iVar4 = 5;
      for (uVar6 = (uint)bVar1; uVar6 != 0; uVar6 = uVar6 - 1) {
        uVar2 = FUN_005a8690(iVar4 + param_1);
        iVar3 = FUN_00526150(uVar2);
        if (iVar3 != 0) {
          FUN_00527ec0(uVar2);
        }
        iVar4 = iVar4 + 2;
      }
    }
  }
  ExceptionList = local_c;
  return;
}


