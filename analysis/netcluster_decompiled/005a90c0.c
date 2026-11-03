// xrefs to FUN_005a90c0: 004e1e9f(004e1cf0) 

void __thiscall FUN_005a90c0(int param_1,undefined4 param_2,undefined4 param_3)

{
  int iVar1;
  undefined4 uVar2;
  
  if (*(int *)(param_1 + 4) - 1U <= *(int *)(param_1 + 8) + 8U) {
    iVar1 = *(int *)(param_1 + 4) + 0x40;
    *(int *)(param_1 + 4) = iVar1;
    uVar2 = FUN_00551e20(*(undefined4 *)(param_1 + 0x10),iVar1);
    *(undefined4 *)(param_1 + 0x10) = uVar2;
  }
  FUN_005a8620(param_2,param_3,*(int *)(param_1 + 0x10) + *(int *)(param_1 + 8));
  *(int *)(param_1 + 8) = *(int *)(param_1 + 8) + 8;
  return;
}


