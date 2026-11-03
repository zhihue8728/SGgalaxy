// xrefs to FUN_005a89b0: 005a9979(005a97c0) 

void __fastcall FUN_005a89b0(int *param_1)

{
  int *piVar1;
  
  piVar1 = (int *)*param_1;
  if (piVar1 == (int *)0x0) {
    FUN_00623a60(0x80004003);
    return;
  }
  (**(code **)(*piVar1 + 8))(piVar1);
  *param_1 = 0;
  return;
}


