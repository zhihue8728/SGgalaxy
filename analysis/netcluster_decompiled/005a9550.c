// xrefs to FUN_005a9550: 005a966a(005a9600) 

void __fastcall FUN_005a9550(int param_1)

{
  undefined4 *puVar1;
  undefined4 *puVar2;
  undefined4 *puVar3;
  
  if (*(int *)(param_1 + 0x2c) == 0) {
    return;
  }
  puVar3 = (undefined4 *)**(undefined4 **)(param_1 + 0x28);
  while( true ) {
    puVar2 = *(undefined4 **)(param_1 + 0x28);
    if (param_1 == -0x24) {
      FUN_00609e03();
    }
    if (puVar3 == puVar2) {
      FUN_005a94b0();
      return;
    }
    if (param_1 == -0x24) {
      FUN_00609e03();
    }
    if (puVar3 == *(undefined4 **)(param_1 + 0x28)) {
      FUN_00609e03();
    }
    if (*(int *)puVar3[2] != 0) break;
    if (puVar3 == *(undefined4 **)(param_1 + 0x28)) {
      FUN_00609e03();
    }
    puVar2 = (undefined4 *)*puVar3;
    if (param_1 == -0x24) {
      FUN_00609e03();
    }
    if (puVar3 == *(undefined4 **)(param_1 + 0x28)) {
      FUN_00609e03();
    }
    puVar1 = puVar3 + 2;
    puVar3 = puVar2;
    if ((void *)*puVar1 != (void *)0x0) {
                    /* WARNING: Subroutine does not return */
      _free((void *)*puVar1);
    }
  }
  if (puVar3 == *(undefined4 **)(param_1 + 0x28)) {
    FUN_00609e03();
  }
                    /* WARNING: Subroutine does not return */
  _free(*(void **)puVar3[2]);
}


