// xrefs to FUN_005a8850: 005c97fa(005c96b0) 005c961c(005c9520) 0055e87b(0055e7c0) 005e874c(005e85b0) 005e86aa(005e85b0) 005e86ff(005e85b0) 005e7a04(005e7770) 005e7c3f(005e7770) 

void FUN_005a8850(void *param_1,int param_2,int *param_3)

{
  int iVar1;
  uint _Size;
  undefined8 uVar2;
  
  uVar2 = FUN_005a8690(*param_3 + param_2);
  _Size = (uint)uVar2 & 0xffff;
  iVar1 = (int)((ulonglong)uVar2 >> 0x20) + 2;
  *param_3 = iVar1;
  _memcpy(param_1,(void *)(iVar1 + param_2),_Size);
  *param_3 = *param_3 + _Size;
  *(undefined1 *)(_Size + (int)param_1) = 0;
  return;
}


