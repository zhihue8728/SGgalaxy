// xrefs to FUN_005a9d60: 005aa22b(005aa1e0) 

void __fastcall FUN_005a9d60(int param_1)

{
  int *piVar1;
  int iVar2;
  int *_Memory;
  
  if (*(int *)(param_1 + 0x2c) != 0) {
    piVar1 = (int *)**(undefined4 **)(param_1 + 0x28);
    while( true ) {
      _Memory = piVar1;
      piVar1 = *(int **)(param_1 + 0x28);
      if (param_1 == -0x24) {
        FUN_00609e03();
      }
      if (_Memory == piVar1) break;
      if (param_1 == -0x24) {
        FUN_00609e03();
      }
      if ((_Memory == *(int **)(param_1 + 0x28)) &&
         (FUN_00609e03(), _Memory == *(int **)(param_1 + 0x28))) {
        FUN_00609e03();
      }
      iVar2 = FUN_005a9240(*(undefined4 *)_Memory[2],((undefined4 *)_Memory[2])[1]);
      if (iVar2 == -1) {
        return;
      }
      if (_Memory == *(int **)(param_1 + 0x28)) {
        FUN_00609e03();
      }
      if (*(int *)_Memory[2] != 0) {
        if (_Memory == *(int **)(param_1 + 0x28)) {
          FUN_00609e03();
        }
                    /* WARNING: Subroutine does not return */
        _free(*(void **)_Memory[2]);
      }
      if (_Memory == *(int **)(param_1 + 0x28)) {
        FUN_00609e03();
      }
      piVar1 = (int *)*_Memory;
      if (param_1 == -0x24) {
        FUN_00609e03();
      }
      if (_Memory == *(int **)(param_1 + 0x28)) {
        FUN_00609e03();
      }
      if ((void *)_Memory[2] != (void *)0x0) {
                    /* WARNING: Subroutine does not return */
        _free((void *)_Memory[2]);
      }
      *(int *)(param_1 + 0x30) = *(int *)(param_1 + 0x30) + -1;
      if (_Memory == *(int **)(param_1 + 0x28)) {
        FUN_00609e03();
      }
      if (_Memory != *(int **)(param_1 + 0x28)) {
        *(int *)_Memory[1] = *_Memory;
        *(int *)(*_Memory + 4) = _Memory[1];
                    /* WARNING: Subroutine does not return */
        _free(_Memory);
      }
    }
  }
  return;
}


