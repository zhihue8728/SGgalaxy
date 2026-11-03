// xrefs to FUN_005a8a80: 00544987(00544720) 

void __fastcall FUN_005a8a80(int param_1)

{
  int iVar1;
  
  iVar1 = 0x40000 - *(int *)(param_1 + 0x1c);
  if (0 < iVar1) {
    iVar1 = Ordinal_16(*(undefined4 *)(param_1 + 8),
                       *(int *)(param_1 + 0x14) + *(int *)(param_1 + 0x1c),iVar1,0);
    *(int *)(param_1 + 0x1c) = *(int *)(param_1 + 0x1c) + iVar1;
    if (iVar1 == 0) {
      SendMessageA(*(HWND *)(param_1 + 0xc),0x403,0,0);
      FUN_005a8a50();
      return;
    }
  }
  return;
}


