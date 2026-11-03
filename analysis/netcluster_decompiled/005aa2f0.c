// xrefs to FUN_005aa2f0: 0063bd03(0063bd00) 0063bd53(0063bd50) 005aa353(005aa350) 005abc6b(005abb70) 

void __fastcall FUN_005aa2f0(undefined4 *param_1)

{
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0063bc88;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  *param_1 = CSoundManager::vftable;
  param_1[1] = CSoundManager::vftable;
  local_4 = 0;
  FUN_0055f0c0();
  *param_1 = CSingletonBase<CSoundManager>::vftable;
  DAT_006ba7c4 = 0;
  ExceptionList = local_c;
  return;
}


