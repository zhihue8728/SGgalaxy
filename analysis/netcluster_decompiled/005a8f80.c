// xrefs to FUN_005a8f80: 0049f165(0049f130) 0049f2e5(0049f2b0) 0049f795(0049f760) 0049f835(0049f800) 0056227e(00562260) 005621dc(00562130) 0049f1e5(0049f1b0) 0049f265(0049f230) 004aa2d9(004a9890) 0043887a(00438840) 00439793(004396e0) 004398fb(004396e0) 004399ae(004396e0) 00439a6e(004396e0) 004a32ea(004a32b0) 004a3324(004a32b0) 004a335e(004a32b0) 004dea4c(004de9f0) 004deb8f(004deb20) 0059e1ef(0059e110) 005a6326(005a5c50) 004d0c55(004d0b30) 004d0e5e(004d0b30) 004d0ff9(004d0b30) 0043248f(004323a0) 

void __thiscall FUN_005a8f80(int param_1,undefined4 param_2)

{
  undefined1 *puVar1;
  
  *(undefined4 *)(param_1 + 4) = 0x40;
  puVar1 = (undefined1 *)FUN_00551e20(*(undefined4 *)(param_1 + 0x10),0x40);
  *(undefined1 **)(param_1 + 0x10) = puVar1;
  *(undefined4 *)(param_1 + 0xc) = param_2;
  *puVar1 = (char)param_2;
  *(undefined4 *)(param_1 + 8) = 1;
  return;
}


