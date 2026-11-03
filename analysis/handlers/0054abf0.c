// xrefs to FUN_0054abf0: 00544e01(00544b10) 

undefined4 __fastcall FUN_0054abf0(int param_1)

{
  char cVar1;
  int iVar2;
  BOOL BVar3;
  undefined4 uVar4;
  undefined4 local_28;
  undefined4 local_24;
  uint local_20;
  tagMSG local_1c;
  
  do {
    if (DAT_00d67e58 != '\0') {
      return 0;
    }
    iVar2 = PeekMessageA(&local_1c,(HWND)0x0,0,0,0);
    while (iVar2 != 0) {
      BVar3 = GetMessageA(&local_1c,(HWND)0x0,0,0);
      if (BVar3 != 0) {
        TranslateMessage(&local_1c);
        DispatchMessageA(&local_1c);
      }
      iVar2 = PeekMessageA(&local_1c,(HWND)0x0,0,0,0);
    }
    FUN_00548b20();
    FUN_00549640();
    if ((*(int *)(param_1 + 0x184) != *(int *)(param_1 + 0xbfc)) ||
       (*(char *)(param_1 + 0x25f8) != '\0')) {
      FUN_0054caf0(*(int *)(param_1 + 0xbfc));
      *(undefined1 *)(param_1 + 0x25f8) = 0;
    }
    if (*(char *)(DAT_006ba818 + 0x50) != '\0') {
      uVar4 = FUN_004255c0();
      cVar1 = FUN_0057b970(uVar4,&local_20,&local_24,&local_28);
      while (cVar1 != '\0') {
        if (local_20 < 0x106) {
          if (local_20 < 0x104) {
            if (local_20 == 0) {
              if ((DAT_006ba7cc != 0) && (*(char *)(DAT_006ba814 + 0x5c5b) == '\0')) {
                FUN_0049a0e0(local_24,local_28);
              }
            }
            else if ((0xff < local_20) && (local_20 < 0x103)) goto LAB_0054ad0f;
          }
          else {
LAB_0054ad0f:
            FUN_005488c0(local_20,local_24,local_28);
          }
        }
        else if (0x1ff < local_20) {
          if (local_20 < 0x20a) {
            FUN_00545a30(local_20,local_24,local_28);
          }
          else if (local_20 == 0x402) {
            FUN_0054a590(0x402,local_24,local_28);
          }
        }
        cVar1 = FUN_0057b970(uVar4,&local_20,&local_24,&local_28);
      }
    }
    do {
      if (*(int *)(param_1 + 0x1b0) == 0) break;
      cVar1 = FUN_005a9340();
    } while (cVar1 != '\0');
    Sleep(1);
  } while( true );
}


