// xrefs to FUN_005a9180: 0047e5a0(0047e540) 0047e7b8(0047e630) 004b85fb(004b8590) 00523d44(00523b50) 005e41e3(005e4030) 005e62d2(005e61f0) 

void __thiscall FUN_005a9180(int param_1,char *param_2)

{
  char cVar1;
  char *pcVar2;
  undefined4 uVar3;
  
  pcVar2 = param_2;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  if ((char *)(*(int *)(param_1 + 4) + -1) <=
      pcVar2 + *(int *)(param_1 + 8) + (1 - (int)(param_2 + 1))) {
    pcVar2 = param_2;
    do {
      cVar1 = *pcVar2;
      pcVar2 = pcVar2 + 1;
    } while (cVar1 != '\0');
    *(int *)(param_1 + 4) = (int)(pcVar2 + *(int *)(param_1 + 4) + (1 - (int)(param_2 + 1)));
    uVar3 = FUN_00551e20(*(undefined4 *)(param_1 + 0x10),*(undefined4 *)(param_1 + 4));
    *(undefined4 *)(param_1 + 0x10) = uVar3;
  }
  FUN_005a8800(param_2,*(undefined4 *)(param_1 + 0x10),param_1 + 8);
  return;
}


