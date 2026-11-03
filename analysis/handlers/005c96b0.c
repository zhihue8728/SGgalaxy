
void __thiscall FUN_005c96b0(int param_1,byte *param_2,undefined4 param_3)

{
  char cVar1;
  uint uVar2;
  short sVar3;
  uint uVar4;
  char *pcVar5;
  int iVar6;
  undefined4 local_564;
  undefined4 local_560;
  uint local_55c;
  byte *local_558;
  int local_554 [2];
  undefined1 local_54c [4];
  void *local_548;
  undefined4 local_538;
  uint local_534;
  void *local_52c;
  undefined4 local_51c;
  uint local_518;
  undefined1 local_514 [8];
  char local_50c [256];
  char local_40c [1024];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063e8c6;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  local_554[0] = param_1;
  sVar3 = FUN_004338e0(param_2,param_3);
  *(short *)(param_1 + 4) = sVar3;
  uVar4 = *(uint *)(param_1 + 0x38);
  iVar6 = param_1 + 0x30;
  if (sVar3 == 0) {
    if (uVar4 < *(uint *)(param_1 + 0x34)) {
      FUN_00609e03();
    }
    uVar2 = *(uint *)(param_1 + 0x34);
    if (*(uint *)(param_1 + 0x38) < uVar2) {
      FUN_00609e03();
    }
    FUN_00541d00(local_554,iVar6,uVar2,iVar6,uVar4);
  }
  else {
    if (uVar4 < *(uint *)(param_1 + 0x34)) {
      FUN_00609e03();
    }
    uVar2 = *(uint *)(param_1 + 0x34);
    if (*(uint *)(param_1 + 0x38) < uVar2) {
      FUN_00609e03();
    }
    FUN_00541d00(local_514,iVar6,uVar2,iVar6,uVar4);
    local_534 = 0xf;
    local_538 = 0;
    local_548 = (void *)((uint)local_548 & 0xffffff00);
    local_518 = 0xf;
    local_51c = 0;
    local_52c = (void *)((uint)local_52c & 0xffffff00);
    local_558 = param_2;
    local_55c = (uint)*param_2;
    local_560 = param_3;
    local_4 = 1;
    local_564 = 2;
    uVar4 = FUN_005a8690(param_2);
    for (uVar4 = uVar4 & 0xffff; uVar4 != 0; uVar4 = uVar4 - 1) {
      FUN_005a8da0(local_50c,0x100,"uniudi");
      FUN_005a8850(local_40c,local_558,&local_564);
      pcVar5 = local_50c;
      do {
        cVar1 = *pcVar5;
        pcVar5 = pcVar5 + 1;
      } while (cVar1 != '\0');
      FUN_004026a0(local_50c,(int)pcVar5 - (int)(local_50c + 1));
      pcVar5 = local_40c;
      do {
        cVar1 = *pcVar5;
        pcVar5 = pcVar5 + 1;
      } while (cVar1 != '\0');
      FUN_004026a0(local_40c,(int)pcVar5 - (int)(local_40c + 1));
      FUN_005c8eb0(local_54c);
    }
    FUN_005c60d0(param_2,param_3);
    if (0xf < local_518) {
                    /* WARNING: Subroutine does not return */
      _free(local_52c);
    }
    local_518 = 0xf;
    local_51c = 0;
    local_52c = (void *)((uint)local_52c & 0xffffff00);
    if (0xf < local_534) {
                    /* WARNING: Subroutine does not return */
      _free(local_548);
    }
  }
  ExceptionList = local_c;
  return;
}


