// xrefs to FUN_00478ec0: 00408073(00407fc0) 0058cae5(0058c9f0) 005a6f90(005a6ba0) 005a6fa6(005a6ba0) 004f3ca0(004f3c30) 005a7b58(005a79c0) 005a7b6b(005a79c0) 0040a53a(0040a430) 005e0b18(005e0a40) 00428174(004280e0) 0055e23c(0055e180) 005e7e1d(005e7d90) 005252d7(00525230) 00484e1c(00484da0) 0058d152(0058d080) 00553473(005533c0) 0059d123(0059d090) 00562599(00562500) 00585db2(00585d00) 00559084(00558ff0) 00553f08(00553e60) 00419d39(00419cc0) 004fd1be(004fd120) 0064c828(-) 00401d80(00401d10) 

undefined4 __fastcall FUN_00478ec0(int param_1)

{
  char cVar1;
  int iVar2;
  BOOL BVar3;
  undefined4 uVar4;
  undefined4 local_28;
  undefined4 local_24;
  uint local_20;
  tagMSG local_1c;
  
  *(int *)(DAT_006ba7c8 + 0xc18) = param_1;
  *(undefined4 *)(param_1 + 0x164) = 0;
  do {
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
    if (*(int *)(DAT_00c346e8 + 0x160) != *(int *)(DAT_006ba7c8 + 0xbfc)) {
      *(undefined4 *)(param_1 + 0x164) = 1;
      *(undefined4 *)(DAT_006ba7c8 + 0xc18) = 0;
      return *(undefined4 *)(param_1 + 0x164);
    }
    if (*(char *)(DAT_006ba818 + 0x50) != '\0') {
      uVar4 = FUN_004255c0();
      cVar1 = FUN_0057b970(uVar4,&local_20,&local_24,&local_28);
      while (cVar1 != '\0') {
        if (local_20 < 0x106) {
          if (local_20 < 0x104) {
            if (local_20 == 0) {
              if (DAT_006ba7cc != 0) {
                FUN_0049a0e0(local_24,local_28);
              }
            }
            else if ((0xff < local_20) && (local_20 < 0x103)) goto LAB_00478fd8;
          }
          else {
LAB_00478fd8:
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
      if (*(int *)(DAT_006ba7c8 + 0x1b0) == 0) break;
      cVar1 = FUN_005a9340();
    } while (cVar1 != '\0');
    Sleep(0);
    if (DAT_00d67e58 != '\0') {
      *(undefined4 *)(param_1 + 0x164) = 1;
    }
    if (*(int *)(param_1 + 0x164) != 0) {
      *(undefined4 *)(DAT_006ba7c8 + 0xc18) = 0;
      return *(undefined4 *)(param_1 + 0x164);
    }
  } while( true );
}


