
undefined4 __thiscall FUN_004a2090(int param_1,undefined4 param_2)

{
  int iVar1;
  char cVar2;
  uint uVar3;
  undefined4 uVar4;
  undefined1 local_20c [256];
  undefined1 local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062bbfb;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar3 = FUN_005a8680(param_2);
  uVar3 = uVar3 & 0xff;
  switch(uVar3) {
  case 1:
  case 4:
  case 8:
  case 0xd:
    FUN_005a8da0(local_20c,0x100,"fldjb1");
    FUN_005a8da0(local_10c,0x100,"fldjb2");
    cVar2 = FUN_00437fb0(local_20c);
    if (cVar2 != '\0') {
      FUN_0049f3c0(0,uVar3,local_20c);
      ExceptionList = local_c;
      return 0;
    }
    iVar1 = *(int *)(param_1 + 0x218f0);
    if (iVar1 != 0) {
      if (iVar1 == 1) {
        FUN_0049f3c0(1,uVar3,local_20c);
        ExceptionList = local_c;
        return 1;
      }
      if (iVar1 != 2) {
        ExceptionList = local_c;
        return 0;
      }
      FUN_0049f3c0(0,uVar3,local_20c);
      ExceptionList = local_c;
      return 1;
    }
    break;
  default:
    goto switchD_004a210f_caseD_2;
  }
                    /* WARNING (jumptable): Sanity check requires truncation of jumptable */
                    /* WARNING: Could not find normalized switch variable to match jumptable */
  switch(*(undefined1 *)((int)&PTR_caseD_4_004a2278 + uVar3 + 3)) {
  case 0:
    uVar4 = 1;
    break;
  case 1:
    uVar4 = 2;
    break;
  case 2:
    uVar4 = 3;
    break;
  case 3:
    uVar4 = 4;
    break;
  case 4:
    goto switchD_004a21bf_caseD_4;
  }
  FUN_00402eb0(local_20c,local_10c,uVar4,0,0,0,0);
switchD_004a21bf_caseD_4:
  FUN_0051d1f0(0x1c);
switchD_004a210f_caseD_2:
  ExceptionList = local_c;
  return 0;
}


