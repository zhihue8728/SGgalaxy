// xrefs to FUN_005aa060: 005482a5(00547f80) 00547f56(00547d30) 005ae480(005ae400) 005b0147(005afa50) 005b2020(005b1fa0) 00568287(00567ea0) 005682b1(00567ea0) 004ba2cf(004ba060) 0056f2c0(0056f240) 00402510(00402490) 

void FUN_005aa060(undefined4 param_1,int param_2,int *param_3)

{
  char cVar1;
  char *_Dst;
  char *pcVar2;
  uint _Size;
  undefined8 uVar3;
  
  uVar3 = FUN_005a8690(*param_3 + param_2);
  _Size = (uint)uVar3 & 0xffff;
  *param_3 = (int)((ulonglong)uVar3 >> 0x20) + 2;
  _Dst = (char *)thunk_FUN_006094fc(_Size + 1);
  _memcpy(_Dst,(void *)(*param_3 + param_2),_Size);
  *param_3 = *param_3 + _Size;
  _Dst[_Size] = '\0';
  pcVar2 = _Dst;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  FUN_004026a0(_Dst,(int)pcVar2 - (int)(_Dst + 1));
                    /* WARNING: Subroutine does not return */
  _free(_Dst);
}


