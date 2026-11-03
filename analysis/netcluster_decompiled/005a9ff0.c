// xrefs to FUN_005a9ff0: 00548271(00547f80) 00547f21(00547d30) 0057e523(0057e400) 0057e553(0057e400) 0057e6a5(0057e5e0) 0057e6dc(0057e5e0) 005b00b8(005afa50) 004b03af(004b0040) 004b4d8f(004b4980) 004b524f(004b4980) 004b5353(004b4980) 004b4820(004b4720) 0056647f(00566460) 00567fea(00567ea0) 004aa3c0(004aa340) 004aaeaf(004aadf0) 0047c9af(0047c640) 0047c9c3(0047c640) 0047c9da(0047c640) 004b8a10(004b8990) 00590fd3(00590fc0) 005353b1(00535350) 004f72c0(004f7240) 

void FUN_005a9ff0(undefined4 param_1,int param_2,int *param_3)

{
  char cVar1;
  uint uVar2;
  char *_Dst;
  char *pcVar3;
  int extraout_ECX;
  
  uVar2 = FUN_005a8680(*param_3 + param_2);
  uVar2 = uVar2 & 0xff;
  *param_3 = extraout_ECX + 1;
  _Dst = (char *)thunk_FUN_006094fc(uVar2 + 1);
  _memcpy(_Dst,(void *)(*param_3 + param_2),uVar2);
  *param_3 = *param_3 + uVar2;
  _Dst[uVar2] = '\0';
  pcVar3 = _Dst;
  do {
    cVar1 = *pcVar3;
    pcVar3 = pcVar3 + 1;
  } while (cVar1 != '\0');
  FUN_004026a0(_Dst,(int)pcVar3 - (int)(_Dst + 1));
                    /* WARNING: Subroutine does not return */
  _free(_Dst);
}


