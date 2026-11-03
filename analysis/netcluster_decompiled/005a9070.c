// xrefs to FUN_005a9070: 0049f17e(0049f130) 0049f2fe(0049f2b0) 0049f30c(0049f2b0) 0049f7b1(0049f760) 00463980(00463880) 00463997(00463880) 00548e2c(00548c50) 00548e5d(00548c50) 00531a6c(00531a20) 004de78f(004de6e0) 0057d30b(0057d2d0) 0049f1fe(0049f1b0) 0049f27e(0049f230) 004de8b3(004de840) 0056572b(005656f0) 004393c8(004390b0) 0049e40e(0049e3d0) 004a4291(004a4250) 004de98f(004de930) 0054717d(00547130) 004a98ed(004a9890) 004a991e(004a9890) 004a9c9b(004a9890) 004a9cb6(004a9890) 004a9cf6(004a9890) 

void __thiscall FUN_005a9070(int param_1,undefined4 param_2)

{
  int iVar1;
  undefined4 uVar2;
  
  if (*(int *)(param_1 + 4) - 1U <= *(int *)(param_1 + 8) + 4U) {
    iVar1 = *(int *)(param_1 + 4) + 0x40;
    *(int *)(param_1 + 4) = iVar1;
    uVar2 = FUN_00551e20(*(undefined4 *)(param_1 + 0x10),iVar1);
    *(undefined4 *)(param_1 + 0x10) = uVar2;
  }
  FUN_005a85f0(param_2,*(int *)(param_1 + 0x10) + *(int *)(param_1 + 8));
  *(int *)(param_1 + 8) = *(int *)(param_1 + 8) + 4;
  return;
}


