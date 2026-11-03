// xrefs to FUN_005a9770: 005a9952(005a97c0) 

undefined4 __fastcall FUN_005a9770(IUnknown *param_1)

{
  undefined4 uVar1;
  ULONG UVar2;
  undefined4 *puVar3;
  undefined4 local_4;
  
  puVar3 = &local_4;
  local_4 = 0;
  UVar2 = (*param_1->lpVtbl[3].Release)(param_1);
  if ((int)UVar2 < 0) {
    _com_issue_errorex(UVar2,param_1,(_GUID *)&DAT_0064e46c);
  }
  uVar1 = local_4;
  FUN_0042e730(puVar3,0);
  return uVar1;
}


