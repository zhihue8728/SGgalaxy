
void __thiscall FUN_005c9520(int param_1,byte *param_2,undefined4 param_3)

{
  char cVar1;
  int iVar2;
  undefined2 uVar3;
  uint uVar4;
  uint uVar5;
  char *pcVar6;
  int local_448;
  undefined4 local_444;
  uint local_440;
  byte *local_43c;
  int local_438;
  uint local_434 [2];
  void *local_42c;
  undefined4 local_41c;
  uint local_418;
  undefined1 local_414 [8];
  char local_40c [1024];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063e8a6;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  local_438 = param_1;
  uVar3 = FUN_004338e0(param_2,param_3);
  *(undefined2 *)(param_1 + 6) = uVar3;
  uVar4 = *(uint *)(param_1 + 0x48);
  if (uVar4 < *(uint *)(param_1 + 0x44)) {
    FUN_00609e03();
  }
  uVar5 = *(uint *)(param_1 + 0x44);
  if (*(uint *)(param_1 + 0x48) < uVar5) {
    FUN_00609e03();
  }
  FUN_005c7b10(local_414,param_1 + 0x40,uVar5,param_1 + 0x40,uVar4);
  local_418 = 0xf;
  local_41c = 0;
  local_42c = (void *)((uint)local_42c & 0xffffff00);
  local_43c = param_2;
  local_440 = (uint)*param_2;
  local_444 = param_3;
  local_4 = 1;
  local_448 = 2;
  uVar4 = FUN_005a8690(param_2);
  iVar2 = local_448;
  for (uVar4 = uVar4 & 0xffff; uVar4 != 0; uVar4 = uVar4 - 1) {
    local_448 = iVar2 + 1;
    uVar5 = FUN_005a8680(local_43c + iVar2);
    FUN_005a8850(local_40c,local_43c,&local_448);
    pcVar6 = local_40c;
    do {
      cVar1 = *pcVar6;
      pcVar6 = pcVar6 + 1;
    } while (cVar1 != '\0');
    local_434[0] = uVar5 & 0xff;
    FUN_004026a0(local_40c,(int)pcVar6 - (int)(local_40c + 1));
    FUN_005c8f60(local_434);
    iVar2 = local_448;
  }
  local_448 = iVar2;
  FUN_005c6180(param_2,param_3);
  if (0xf < local_418) {
                    /* WARNING: Subroutine does not return */
    _free(local_42c);
  }
  ExceptionList = local_c;
  return;
}


