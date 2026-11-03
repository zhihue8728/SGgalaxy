
void __fastcall FUN_005a1690(int param_1)

{
  char *pcVar1;
  char cVar2;
  char *pcVar3;
  char *pcVar4;
  char *pcVar5;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063acc8;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  FUN_005a8f10(2);
  pcVar4 = (char *)(param_1 + 0x310);
  local_4 = 0;
  FUN_005a9110(pcVar4);
  pcVar1 = (char *)(param_1 + 0x628);
  FUN_005a9110(pcVar1);
  pcVar5 = (char *)(param_1 + 0xc58);
  FUN_005a9110(pcVar5);
  FUN_005aa1e0();
  pcVar3 = pcVar4;
  do {
    cVar2 = *pcVar3;
    pcVar3 = pcVar3 + 1;
  } while (cVar2 != '\0');
  FUN_004026a0(pcVar4,(int)pcVar3 - (param_1 + 0x311));
  pcVar4 = pcVar1;
  do {
    cVar2 = *pcVar4;
    pcVar4 = pcVar4 + 1;
  } while (cVar2 != '\0');
  FUN_004026a0(pcVar1,(int)pcVar4 - (param_1 + 0x629));
  pcVar4 = pcVar5;
  do {
    cVar2 = *pcVar4;
    pcVar4 = pcVar4 + 1;
  } while (cVar2 != '\0');
  FUN_004026a0(pcVar5,(int)pcVar4 - (param_1 + 0xc59));
  local_4 = 0xffffffff;
  FUN_005a8f50();
  ExceptionList = local_c;
  return;
}


