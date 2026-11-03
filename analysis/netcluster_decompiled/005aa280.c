// xrefs to FUN_005aa280: 005abdc0(005abda0) 

undefined4 * __fastcall FUN_005aa280(undefined4 *param_1)

{
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0063bc68;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  *param_1 = CSingletonBase<CSoundManager>::vftable;
  local_4 = 0;
  DAT_006ba7c4 = param_1;
  FUN_0055f0b0();
  param_1[1] = CSoundManager::vftable;
  *param_1 = CSoundManager::vftable;
  ExceptionList = local_c;
  return param_1;
}


