// xrefs to FUN_005a87b0: 005a9171(005a9110) 

void FUN_005a87b0(char *param_1,int param_2,int *param_3)

{
  char cVar1;
  char *pcVar2;
  size_t _Size;
  int extraout_EDX;
  
  pcVar2 = param_1;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  _Size = (int)pcVar2 - (int)(param_1 + 1);
  FUN_005a8590(_Size,*param_3 + param_2);
  *param_3 = *param_3 + 1;
  _memcpy((void *)(*param_3 + extraout_EDX),param_1,_Size);
  *param_3 = *param_3 + _Size;
  return;
}


