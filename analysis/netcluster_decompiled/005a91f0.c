// xrefs to FUN_005a91f0: 00548e0b(00548c50) 005622f7(005622b0) 00562208(00562130) 004aa2fa(004a9890) 00547331(005472c0) 

void __thiscall FUN_005a91f0(int param_1,undefined4 param_2,int param_3)

{
  int iVar1;
  undefined4 uVar2;
  
  if (*(int *)(param_1 + 4) - 1U <= (uint)(*(int *)(param_1 + 8) + param_3)) {
    iVar1 = *(int *)(param_1 + 4) + param_3;
    *(int *)(param_1 + 4) = iVar1;
    uVar2 = FUN_00551e20(*(undefined4 *)(param_1 + 0x10),iVar1);
    *(undefined4 *)(param_1 + 0x10) = uVar2;
  }
  FUN_005a8890(param_2,param_3,*(undefined4 *)(param_1 + 0x10),param_1 + 8);
  return;
}


