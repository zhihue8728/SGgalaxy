// xrefs to FUN_005a8530: 005a9ab7(005a97c0) 005a9ac9(005a97c0) 

void __thiscall FUN_005a8530(int param_1,char *param_2)

{
  char cVar1;
  char *pcVar2;
  int iVar3;
  
  if ((param_2 != (char *)0x0) && (*(int *)(param_1 + 8) != -1)) {
    pcVar2 = param_2;
    do {
      cVar1 = *pcVar2;
      pcVar2 = pcVar2 + 1;
    } while (cVar1 != '\0');
    iVar3 = Ordinal_19(*(int *)(param_1 + 8),param_2,(int)pcVar2 - (int)(param_2 + 1),0);
    if (iVar3 == -1) {
      MessageBoxA((HWND)0x0,&DAT_0065d278,&DAT_0064e624,0);
      PostQuitMessage(0);
                    /* WARNING: Subroutine does not return */
      _exit(0);
    }
  }
  return;
}


