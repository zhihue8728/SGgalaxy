
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void FUN_004aaa80(void)

{
  undefined1 uVar1;
  char cVar2;
  undefined1 local_2d34 [256];
  CHAR local_2c34 [11300];
  undefined4 uStack_10;
  void *local_c;
  undefined1 *puStack_8;
  int local_4;
  
  puStack_8 = &LAB_0062c2f1;
  local_c = ExceptionList;
  uStack_10 = 0x4aaa9f;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8680();
  switch(uVar1) {
  case 0:
    FUN_005a8da0();
    FUN_005a8f10();
    local_4._0_1_ = 1;
    FUN_005a8fc0();
    FUN_005a9110();
    FUN_005a8fc0();
    FUN_005aa1e0();
    FUN_00402790(local_2d34);
    FUN_004aa6f0();
    local_4 = (uint)local_4._1_3_ << 8;
    FUN_005a8f50();
    break;
  case 1:
    FUN_005a8da0();
    cVar2 = FUN_005a8680();
    if (cVar2 == '\0') {
      FUN_005a6aa0();
      local_4._0_1_ = 2;
      wsprintfA(local_2c34,&DAT_00652864);
      FUN_005a6ba0(*(undefined4 *)(DAT_006ba7c8 + 0xc0c));
      local_4 = (uint)local_4._1_3_ << 8;
      FUN_005a6630();
    }
    else {
      FUN_00402790(local_2d34);
      FUN_004aa6f0();
    }
    break;
  case 2:
  case 3:
  case 4:
    FUN_00525770();
  }
  ExceptionList = local_c;
  return;
}


