// xrefs to FUN_005a9020: 0049f7bf(0049f760) 0049f7cd(0049f760) 0049f843(0049f800) 004638d1(00463880) 0046390c(00463880) 0046391e(00463880) 004639c7(00463880) 005478c3(00547880) 00547933(005478f0) 005c6005(005c5fc0) 004de799(004de6e0) 004de7a3(004de6e0) 004de7b1(004de6e0) 005622e8(005622b0) 005621f5(00562130) 0057d319(0057d2d0) 004393d6(004390b0) 004393e4(004390b0) 0049e41c(0049e3d0) 0049e42a(0049e3d0) 004a98fa(004a9890) 004a9936(004a9890) 004a9940(004a9890) 004a9976(004a9890) 004a9991(004a9890) 

void __thiscall FUN_005a9020(int param_1,undefined4 param_2)

{
  int iVar1;
  undefined4 uVar2;
  
  if (*(int *)(param_1 + 4) - 1U <= *(int *)(param_1 + 8) + 2U) {
    iVar1 = *(int *)(param_1 + 4) + 0x40;
    *(int *)(param_1 + 4) = iVar1;
    uVar2 = FUN_00551e20(*(undefined4 *)(param_1 + 0x10),iVar1);
    *(undefined4 *)(param_1 + 0x10) = uVar2;
  }
  FUN_005a85b0(param_2,*(int *)(param_1 + 0x10) + *(int *)(param_1 + 8));
  *(int *)(param_1 + 8) = *(int *)(param_1 + 8) + 2;
  return;
}


