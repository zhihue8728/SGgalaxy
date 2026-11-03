// xrefs to FUN_005a8fc0: 0049f170(0049f130) 0049f2f0(0049f2b0) 0049f7a3(0049f760) 00463969(00463880) 004639af(00463880) 005b4cfd(005b4cb0) 00548e16(00548c50) 004aad32(004aaca0) 004aad3d(004aaca0) 00531a5c(00531a20) 0054857c(00548510) 00547ab2(00547a60) 00547acf(00547a60) 005655e3(00565530) 005655f6(00565530) 004de7c8(004de6e0) 0056228e(00562260) 005621e7(00562130) 00547288(00547250) 0049e141(0049e110) 0049f1f0(0049f1b0) 0049f270(0049f230) 004de8bd(004de840) 004de8c7(004de840) 004393ba(004390b0) 

void __thiscall FUN_005a8fc0(int param_1,undefined4 param_2)

{
  int iVar1;
  undefined4 uVar2;
  
  if (*(int *)(param_1 + 8) == 0) {
    **(undefined1 **)(param_1 + 0x10) = (char)param_2;
  }
  if (*(int *)(param_1 + 4) - 1U <= *(int *)(param_1 + 8) + 1U) {
    iVar1 = *(int *)(param_1 + 4) + 0x40;
    *(int *)(param_1 + 4) = iVar1;
    uVar2 = FUN_00551e20(*(undefined4 *)(param_1 + 0x10),iVar1);
    *(undefined4 *)(param_1 + 0x10) = uVar2;
  }
  FUN_005a8590(param_2,*(int *)(param_1 + 0x10) + *(int *)(param_1 + 8));
  *(int *)(param_1 + 8) = *(int *)(param_1 + 8) + 1;
  return;
}


