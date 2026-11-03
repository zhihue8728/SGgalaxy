// xrefs to FUN_005a96c0: 005a9972(005a97c0) 

ULONG __thiscall FUN_005a96c0(IUnknown *param_1,undefined4 param_2,int *param_3,void *param_4)

{
  ULONG UVar1;
  LONG LVar2;
  void *pvStack_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_0063bbd8;
  pvStack_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &pvStack_c;
  UVar1 = (*param_1->lpVtbl[2].AddRef)(param_1);
  if ((int)UVar1 < 0) {
    _com_issue_errorex(UVar1,param_1,(_GUID *)&DAT_0064e46c);
  }
  if ((param_3 == (int *)0x0) || (LVar2 = InterlockedDecrement(param_3 + 2), LVar2 != 0)) {
    ExceptionList = param_4;
    return UVar1;
  }
  if (*param_3 != 0) {
    Ordinal_6(*param_3);
  }
  if ((void *)param_3[1] != (void *)0x0) {
                    /* WARNING: Subroutine does not return */
    _free((void *)param_3[1]);
  }
                    /* WARNING: Subroutine does not return */
  _free(param_3);
}


