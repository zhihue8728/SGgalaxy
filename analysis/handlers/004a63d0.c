
void __thiscall FUN_004a63d0(int param_1,int param_2,int param_3)

{
  char cVar1;
  undefined4 uVar2;
  int iVar3;
  int *piVar4;
  char acStack_128 [260];
  undefined4 uStack_24;
  undefined4 uStack_20;
  undefined4 uStack_1c;
  undefined4 uStack_18;
  int iStack_14;
  undefined4 uStack_10;
  void *pvStack_c;
  undefined1 *puStack_8;
  int local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062c049;
  pvStack_c = ExceptionList;
  ExceptionList = &pvStack_c;
  if (*(int **)(DAT_006ba7c8 + 0xc18) != (int *)0x0) {
    ExceptionList = &pvStack_c;
    (**(code **)(**(int **)(DAT_006ba7c8 + 0xc18) + 0x38))();
    *(undefined4 *)(DAT_006ba7c8 + 0xc18) = 0;
  }
  local_4 = 0;
  cVar1 = FUN_005a8680(param_2);
  if (cVar1 == '@') {
    _strcpy_s(acStack_128,0x101,"Shop Wnd");
    uStack_24 = 0;
    uStack_20 = 0;
    uStack_1c = 800;
    uStack_18 = 600;
    if (param_1 == 0) {
      iStack_14 = 0;
    }
    else {
      iStack_14 = param_1 + 4;
    }
    uStack_10 = 0xf0;
    uVar2 = FUN_005a86b0(param_2 + 1);
    if (*(int *)(DAT_006ba7c8 + 0xc0c) != *(int *)(param_1 + 0x29b00)) {
      FUN_004a4850();
      if (*(undefined4 **)(param_1 + 0x29b00) != (undefined4 *)0x0) {
        (**(code **)**(undefined4 **)(param_1 + 0x29b00))(1);
      }
      iVar3 = FUN_0055f0d0(0x15870);
      local_4._0_1_ = 1;
      if (iVar3 == 0) {
        piVar4 = (int *)0x0;
      }
      else {
        piVar4 = (int *)FUN_00489ec0(uVar2);
      }
      *(int **)(param_1 + 0x29b00) = piVar4;
      local_4 = (uint)local_4._1_3_ << 8;
      (**(code **)(*piVar4 + 0x34))(acStack_128);
      FUN_005ecde0();
      *(undefined4 *)(*(int *)(param_1 + 0x29b00) + 0x46c) = *(undefined4 *)(DAT_006ba7c8 + 0xc0c);
      FUN_00548730(*(undefined4 *)(param_1 + 0x29b00));
      FUN_004a3060(0,"HR_BGM10.MP3");
    }
    FUN_00425740();
    FUN_0048ade0(param_2 + 5,param_3 + -5);
    FUN_00425760();
  }
  else if (((cVar1 == 'B') && (*(int *)(param_1 + 0x29b00) != 0)) &&
          (*(char *)(*(int *)(param_1 + 0x29b00) + 0x155) != '\0')) {
    FUN_00484040(param_2 + 1,param_3 + -1);
  }
  ExceptionList = pvStack_c;
  return;
}


