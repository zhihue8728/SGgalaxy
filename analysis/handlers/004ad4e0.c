
void FUN_004ad4e0(int param_1,int param_2)

{
  undefined4 uVar1;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0062c458;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  uVar1 = FUN_005a86b0(param_1);
  FUN_00548f00(uVar1,"Delayed Put");
  FUN_005c30b0(uVar1,param_1 + 4,param_2 + -4);
  FUN_004ac800(param_1 + 4,param_2 + -4,0);
  ExceptionList = local_c;
  return;
}


