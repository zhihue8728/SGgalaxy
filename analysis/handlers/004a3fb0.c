
void __fastcall FUN_004a3fb0(int param_1)

{
  char local_11c [260];
  undefined4 uStack_18;
  undefined4 uStack_14;
  undefined4 uStack_10;
  undefined4 uStack_c;
  int iStack_8;
  undefined4 uStack_4;
  
  if (*(int **)(DAT_006ba7c8 + 0xc18) != (int *)0x0) {
    (**(code **)(**(int **)(DAT_006ba7c8 + 0xc18) + 0x38))();
    *(undefined4 *)(DAT_006ba7c8 + 0xc18) = 0;
  }
  if ((*(char *)(DAT_006ba818 + 0x50) == '\0') &&
     (*(int *)(DAT_006ba7c8 + 0xc0c) != *(int *)(param_1 + 0x29afc))) {
    _strcpy_s(local_11c,0x101,"UnitManage Wnd");
    iStack_8 = param_1 + 4;
    uStack_18 = 0;
    uStack_14 = 0;
    uStack_10 = 800;
    uStack_c = 600;
    uStack_4 = 0xf0;
    (**(code **)(**(int **)(param_1 + 0x29afc) + 0x34))(local_11c);
    FUN_005ecde0();
    *(undefined4 *)(*(int *)(param_1 + 0x29afc) + 0x23c) = *(undefined4 *)(DAT_006ba7c8 + 0xc0c);
    FUN_00548730(*(undefined4 *)(param_1 + 0x29afc));
    FUN_0051d1f0(0x36);
  }
  return;
}


