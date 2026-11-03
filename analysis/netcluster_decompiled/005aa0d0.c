// xrefs to FUN_005aa0d0: 005aa1c2(005aa170) 

void __thiscall FUN_005aa0d0(int param_1,uint param_2)

{
  undefined1 local_50 [4];
  undefined1 local_4c;
  undefined4 local_3c;
  undefined4 local_38;
  undefined **local_34 [10];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0063bc48;
  local_c = ExceptionList;
  if (0x3fffffffU - *(int *)(param_1 + 8) < param_2) {
    local_38 = 0xf;
    local_3c = 0;
    local_4c = 0;
    ExceptionList = &local_c;
    FUN_004026a0("list<T> too long",0x10);
    local_4 = 0;
    FUN_004040f0(local_50);
    local_34[0] = std::length_error::vftable;
                    /* WARNING: Subroutine does not return */
    __CxxThrowException_8(local_34,&DAT_00675fc4);
  }
  *(uint *)(param_1 + 8) = *(int *)(param_1 + 8) + param_2;
  return;
}


