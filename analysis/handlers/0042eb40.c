
void __fastcall FUN_0042eb40(int param_1)

{
  char cVar1;
  char *pcVar2;
  char *_Dst;
  char local_40c [1024];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  puStack_8 = &LAB_006262fb;
  local_c = ExceptionList;
  local_4 = 0;
  ExceptionList = &local_c;
  FUN_005a8da0(local_40c,0x100,"config");
  if (*(void **)(param_1 + 0xb1c) != (void *)0x0) {
                    /* WARNING: Subroutine does not return */
    _free(*(void **)(param_1 + 0xb1c));
  }
  pcVar2 = local_40c;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  _Dst = (char *)thunk_FUN_006094fc(pcVar2 + (1 - (int)(local_40c + 1)));
  pcVar2 = local_40c;
  *(char **)(param_1 + 0xb1c) = _Dst;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  _strcpy_s(_Dst,(rsize_t)(pcVar2 + (1 - (int)(local_40c + 1))),local_40c);
  FUN_0042cdc0();
  ExceptionList = local_c;
  return;
}


