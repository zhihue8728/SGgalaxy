// xrefs to FUN_005a9340: 0054adbc(0054abf0) 00479092(00478ec0) 

uint __fastcall FUN_005a9340(int param_1)

{
  int iVar1;
  undefined4 uVar2;
  undefined4 uVar3;
  uint uVar4;
  void *_Dst;
  int iVar5;
  undefined8 uVar6;
  HWND hWnd;
  
  iVar1 = *(int *)(param_1 + 0x14);
  uVar6 = FUN_005a8690(iVar1 + 1);
  uVar2 = DAT_006ba7dc;
  iVar5 = ((uint)uVar6 & 0xffff) + 3;
  if (*(int *)(param_1 + 0x1c) < iVar5) {
    return (uint)uVar6 & 0xffffff00;
  }
  if (*(char *)(param_1 + 0x20) == '\0') {
    if (*(char *)(param_1 + 0x10) != '\0') {
      uVar3 = FUN_00545260();
      FUN_0047e540(uVar2,"S_%d O_%d Encryption Enable Mode : Access Violation",DAT_00d69268,uVar3);
    }
switchD_005a9414_caseD_0:
    uVar4 = FUN_005a8690(*(int *)(param_1 + 0x14) + 1);
    uVar4 = uVar4 & 0xffff;
    _Dst = (void *)thunk_FUN_006094fc(uVar4);
    _memcpy(_Dst,(void *)(*(int *)(param_1 + 0x14) + 3),uVar4);
    *(int *)(param_1 + 0x1c) = *(int *)(param_1 + 0x1c) - iVar5;
    _memcpy(*(void **)(param_1 + 0x14),(void *)((int)*(void **)(param_1 + 0x14) + iVar5),
            *(size_t *)(param_1 + 0x1c));
    hWnd = *(HWND *)(param_1 + 0xc);
LAB_005a93e1:
    SendMessageA(hWnd,0x402,(WPARAM)_Dst,uVar4);
                    /* WARNING: Subroutine does not return */
    _free(_Dst);
  }
  switch(*(undefined1 *)(iVar1 + 3)) {
  case 0:
  case 3:
  case 0xb:
  case 0xc:
  case 0xd:
    goto switchD_005a9414_caseD_0;
  default:
    uVar4 = FUN_005a8690((int)((ulonglong)uVar6 >> 0x20));
    _Dst = (void *)thunk_FUN_006094fc((uVar4 & 0xffff) * 2 + 10);
    uVar4 = FUN_005a8ad0(*(int *)(param_1 + 0x14) + 3,uVar4 & 0xffff,_Dst);
    *(int *)(param_1 + 0x1c) = *(int *)(param_1 + 0x1c) - iVar5;
    _memcpy(*(void **)(param_1 + 0x14),(void *)((int)*(void **)(param_1 + 0x14) + iVar5),
            *(size_t *)(param_1 + 0x1c));
    hWnd = *(HWND *)(param_1 + 0xc);
    goto LAB_005a93e1;
  }
}


