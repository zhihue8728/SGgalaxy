// xrefs to FUN_005a80f0: 0062c6ca(0062c6c1) 0062c91e(0062c915) 004b2446(004b2160) 005a81c3(005a81c0) 

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __fastcall FUN_005a80f0(undefined4 *param_1)

{
  void *local_c;
  undefined1 *puStack_8;
  int local_4;
  
  puStack_8 = &LAB_0063ba7f;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  *param_1 = CCtrlPermissionWnd::vftable;
  param_1[1] = CCtrlPermissionWnd::vftable;
  local_4 = 6;
  FUN_00470640();
  local_4._0_1_ = 5;
  FUN_00470640();
  local_4._0_1_ = 4;
  FUN_00470640();
  local_4._0_1_ = 3;
  FUN_00470640();
  local_4._0_1_ = 2;
  FUN_00470600();
  local_4._0_1_ = 1;
  _eh_vector_destructor_iterator_(param_1 + 0xbd,0x1c,4,FUN_005d3000);
  local_4 = (uint)local_4._1_3_ << 8;
  FUN_00470410();
  *param_1 = CSingletonBase<CCtrlPermissionWnd>::vftable;
  _DAT_00d69260 = 0;
  ExceptionList = local_c;
  return;
}


