
/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __fastcall FUN_004ac000(int param_1)

{
  undefined1 uVar1;
  LPCSTR pCVar2;
  undefined1 local_2d34 [256];
  CHAR local_2c34 [11300];
  undefined4 uStack_10;
  void *local_c;
  undefined1 *puStack_8;
  int local_4;
  
  puStack_8 = &LAB_0062c406;
  local_c = ExceptionList;
  uStack_10 = 0x4ac01f;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a8680();
  switch(uVar1) {
  case 0:
    FUN_005a8680();
    FUN_005a8680();
    FUN_005a8da0();
    FUN_00402790(local_2d34);
    FUN_004f32c0();
    break;
  case 1:
    FUN_005a8da0();
    FUN_00402790();
    FUN_004f2120();
    break;
  case 3:
    FUN_004a3520();
    FUN_005dfea0();
    break;
  case 5:
    FUN_005a8680();
    FUN_005a8da0();
    FUN_00402790();
    FUN_004a9670();
    break;
  case 6:
    DAT_00ea94fc = 0;
    uVar1 = FUN_005a8680();
    FUN_005a6aa0();
    local_4._0_1_ = 1;
    switch(uVar1) {
    case 0:
      break;
    case 1:
      FUN_005a8da0();
      if (*(uint *)(param_1 + 0x2e4) < 0x10) {
        pCVar2 = (LPCSTR)(param_1 + 0x2d0);
      }
      else {
        pCVar2 = *(LPCSTR *)(param_1 + 0x2d0);
      }
      wsprintfA(local_2c34,pCVar2);
      FUN_00402790();
      FUN_004ab080();
      break;
    case 2:
    case 3:
    case 4:
    case 5:
    case 6:
    case 7:
    case 8:
    case 9:
    case 10:
      break;
    default:
      goto switchD_004ac200_default;
    }
    FUN_005a6ba0();
switchD_004ac200_default:
    local_4 = (uint)local_4._1_3_ << 8;
    FUN_005a6630();
  }
  ExceptionList = local_c;
  return;
}


