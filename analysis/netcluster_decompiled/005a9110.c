// xrefs to FUN_005a9110: 004aad62(004aaca0) 00548564(00548510) 00439493(004390b0) 004394d3(004390b0) 0049f433(0049f3c0) 0049f498(0049f3c0) 004a9834(004a9670) 004aab47(004aaa80) 0052e02b(0052dfb0) 0058a80a(0058a7c0) 0043889e(00438840) 004388ac(00438840) 00439851(004396e0) 00439866(004396e0) 00439881(004396e0) 0043992c(004396e0) 004399e5(004396e0) 00439a00(004396e0) 00439a89(004396e0) 0047be65(0047b7e0) 0047be76(0047b7e0) 0047be87(0047b7e0) 00484338(004842d0) 00581833(00581780) 00582304(00582120) 

void __thiscall FUN_005a9110(int param_1,char *param_2)

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
  FUN_005a87b0(param_2,*(undefined4 *)(param_1 + 0x10),param_1 + 8);
  return;
}


