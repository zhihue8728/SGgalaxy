// xrefs to FUN_005aa170: 005aa217(005aa1e0) 

void __thiscall FUN_005aa170(undefined4 *param_1,void *param_2,size_t param_3)

{
  int iVar1;
  undefined4 *puVar2;
  void *_Dst;
  int iVar3;
  undefined4 *local_4;
  
  local_4 = param_1;
  puVar2 = (undefined4 *)FUN_006094fc(8);
  puVar2[1] = param_3;
  local_4 = puVar2;
  _Dst = (void *)thunk_FUN_006094fc(param_3 + 1);
  *puVar2 = _Dst;
  _memcpy(_Dst,param_2,param_3);
  iVar1 = param_1[10];
  iVar3 = FUN_005a9510(iVar1,*(undefined4 *)(iVar1 + 4),&local_4);
  FUN_005aa0d0(1);
  *(int *)(iVar1 + 4) = iVar3;
  **(int **)(iVar3 + 4) = iVar3;
  param_1[0xc] = param_1[0xc] + 1;
  return;
}


