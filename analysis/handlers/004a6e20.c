
void __fastcall FUN_004a6e20(int param_1)

{
  int iVar1;
  undefined1 local_50c [256];
  undefined1 local_40c [1024];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062c0cb;
  local_c = ExceptionList;
  if (*(char *)(param_1 + 0x29bdc) == '\0') {
    local_4 = 0;
    ExceptionList = &local_c;
    FUN_005a8da0(local_40c,0x100,"fldpmv1");
    FUN_005a8da0(local_50c,0x100,"fldpmv2");
    iVar1 = (**(code **)(*(int *)(param_1 + 0x29c90) + 0x54))
                      (*(undefined4 *)(DAT_006ba7c8 + 0xc0c),local_40c,1,3,0,0xffffffff,0xffffffff,1
                      );
    if (iVar1 == 3) {
      FUN_004a4dc0(local_50c);
    }
  }
  ExceptionList = local_c;
  return;
}


