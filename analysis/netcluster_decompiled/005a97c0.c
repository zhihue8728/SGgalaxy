// xrefs to FUN_005a97c0: 00548d45(00548c50) 005450f4(005450d0) 

undefined4 __thiscall FUN_005a97c0(int param_1,undefined4 param_2,undefined4 *param_3)

{
  char cVar1;
  int *_Memory;
  int iVar2;
  undefined4 uVar3;
  char *pcVar4;
  undefined1 *puVar5;
  char *pcVar6;
  short *psVar7;
  UINT UVar8;
  HMODULE pHVar9;
  FARPROC pFVar10;
  short sVar11;
  int unaff_ESI;
  int unaff_EDI;
  uint _Size;
  char acStack_3ac [4];
  undefined4 uStack_3a8;
  char acStack_2ac [272];
  short local_19c;
  undefined4 uStack_14;
  void *local_c;
  undefined1 *puStack_8;
  undefined4 uStack_4;
  
  uStack_4 = 0xffffffff;
  puStack_8 = &LAB_0063bbfb;
  local_c = ExceptionList;
  if (*(char *)(DAT_006ba818 + 0x50) == '\0') {
    ExceptionList = &local_c;
    *(undefined4 *)(param_1 + 0xc) = param_2;
    iVar2 = FUN_00545390();
    if ((local_19c == 0x101) || (iVar2 == 0)) {
      iVar2 = Ordinal_23();
      *(int *)(param_1 + 8) = iVar2;
      if (iVar2 != -1) {
        uStack_3a8 = *param_3;
        acStack_3ac[0] = '\x02';
        acStack_3ac[1] = '\0';
        Ordinal_9();
        iVar2 = Ordinal_4();
        if (iVar2 == 0) {
          if (*(char *)(DAT_006ba840 + 0xc5c) == '\0') {
            switch(*(undefined4 *)(DAT_006ba840 + 0xc3c)) {
            case 1:
              _strcpy_s(&stack0xfffffc38,10,"taccom\n");
              pcVar4 = &stack0xfffffc38;
              do {
                cVar1 = *pcVar4;
                pcVar4 = pcVar4 + 1;
              } while (cVar1 != '\0');
              _Size = (int)pcVar4 - (int)&stack0xfffffc39 & 0xffff;
              puVar5 = _malloc(0xf);
              *puVar5 = 0xaa;
              FUN_005a85b0();
              if (_Size != 0) {
                _memcpy(puVar5 + 2,&stack0xfffffc38,_Size);
              }
              puVar5[_Size + 2] = 0;
              iVar2 = Ordinal_19(*(undefined4 *)(param_1 + 8));
              if (iVar2 != -1) {
                    /* WARNING: Subroutine does not return */
                _free(puVar5);
              }
              MessageBoxA((HWND)0x0,&DAT_0065d5d4,&DAT_0064e624,0);
                    /* WARNING: Subroutine does not return */
              _free(puVar5);
            case 2:
              if (*(uint *)(DAT_006ba840 + 0xaa0) < 0x10) {
                FUN_005a8530();
              }
              else {
                FUN_005a8530();
              }
              break;
            case 4:
              pcVar4 = (char *)(DAT_006ba840 + 0x14);
              pcVar6 = pcVar4;
              do {
                cVar1 = *pcVar6;
                pcVar6 = pcVar6 + 1;
              } while (cVar1 != '\0');
              sVar11 = (short)pcVar6 - ((short)DAT_006ba840 + 0x15);
              psVar7 = (short *)FUN_00551d70();
              *psVar7 = sVar11;
              if (0 < sVar11) {
                _memcpy(psVar7 + 1,pcVar4,(int)sVar11);
              }
              iVar2 = Ordinal_19(*(undefined4 *)(param_1 + 8));
              if ((iVar2 == -1) || (iVar2 = Ordinal_16(*(undefined4 *)(param_1 + 8)), iVar2 == -1))
              {
                MessageBoxA((HWND)0x0,&DAT_0065d59c,&DAT_0064e624,0);
                goto LAB_005a9cd5;
              }
              if (unaff_ESI == -1) {
                MessageBoxA((HWND)0x0,&DAT_0065d564,&DAT_0064e624,0);
                goto LAB_005a9cd5;
              }
              FUN_00551ce0();
              break;
            case 5:
              pHVar9 = LoadLibraryA("chigamec.dll");
              if (pHVar9 == (HMODULE)0x0) {
                _strcpy_s(acStack_3ac,0x100,&DAT_0065d52c);
                MessageBoxA((HWND)0x0,acStack_3ac,&DAT_0064e624,0);
                goto LAB_005a9cd5;
              }
              pFVar10 = GetProcAddress(pHVar9,"SendEncryptedData");
              (*pFVar10)();
              FreeLibrary(pHVar9);
              break;
            case 6:
              iVar2 = Ordinal_19(*(undefined4 *)(param_1 + 8));
              if (iVar2 == -1) {
                MessageBoxA((HWND)0x0,&DAT_0065d614,&DAT_0064e624,0);
                goto LAB_005a9cd5;
              }
              break;
            case 8:
            case 9:
            case 10:
              UVar8 = GetSystemDirectoryA(acStack_3ac,0x100);
              if (UVar8 == 0) {
LAB_005a9c3e:
                pHVar9 = LoadLibraryA("C:\\WINNT\\System32\\cjconnector.dll");
                if ((pHVar9 == (HMODULE)0x0) &&
                   (pHVar9 = LoadLibraryA("C:\\Windows\\System\\cjconnector.dll"),
                   pHVar9 == (HMODULE)0x0)) {
                  _strcpy_s(acStack_2ac,0x100,&DAT_0065d480);
                  MessageBoxA((HWND)0x0,acStack_2ac,&DAT_0064e624,0);
                  goto LAB_005a9cd5;
                }
              }
              else {
                _strcat_s(acStack_3ac,0x100,"\\cjconnector.dll");
                pHVar9 = LoadLibraryA(acStack_3ac);
                if (pHVar9 == (HMODULE)0x0) goto LAB_005a9c3e;
              }
              pFVar10 = GetProcAddress(pHVar9,"ConnectorKey");
              if (pFVar10 == (FARPROC)0x0) {
                _strcpy_s(acStack_2ac,0x100,&DAT_0065d434);
                MessageBoxA((HWND)0x0,acStack_2ac,&DAT_0064e624,0);
LAB_005a9cd5:
                FUN_005a8a50();
                *(undefined4 *)(param_1 + 8) = 0xffffffff;
                PostQuitMessage(0);
                    /* WARNING: Subroutine does not return */
                _exit(0);
              }
              iVar2 = (*pFVar10)();
              if (iVar2 != 1) goto LAB_005a9cd5;
              break;
            case 0xb:
              _Memory = *(int **)(DAT_006ba840 + 0x14);
              puVar5 = &stack0xfffffc14;
              FUN_0042e1c0(&stack0xfffffc14);
              FUN_005a9770(puVar5);
              uVar3 = *(undefined4 *)(param_1 + 8);
              uStack_14 = 0;
              FUN_0042e1c0(uVar3);
              uStack_14 = 0xffffffff;
              FUN_005a96c0(uVar3);
              FUN_005a89b0();
              if (_Memory != (int *)0x0) {
                if ((int *)*_Memory != (int *)0x0) {
                  (**(code **)(*(int *)*_Memory + 8))();
                }
                    /* WARNING: Subroutine does not return */
                _free(_Memory);
              }
              *(undefined4 *)(DAT_006ba840 + 0x14) = 0;
              CoUninitialize();
              if (unaff_EDI != 1) {
                FUN_0042e530();
              }
              break;
            case 0xd:
              iVar2 = Ordinal_19(*(undefined4 *)(param_1 + 8));
              if (iVar2 == -1) {
                MessageBoxA((HWND)0x0,&DAT_0065d64c,&DAT_0064e624,0);
                goto LAB_005a9cd5;
              }
            }
          }
          iVar2 = Ordinal_101(*(undefined4 *)(param_1 + 8));
          if (iVar2 != 0) {
            Ordinal_3();
            *(undefined4 *)(param_1 + 8) = 0xffffffff;
            FUN_005453c0();
            ExceptionList = local_c;
            return 0;
          }
          if (*(int *)(DAT_006ba840 + 0xc3c) == 0xb) {
            Sleep(500);
          }
          goto LAB_005a9d0c;
        }
        Ordinal_3();
        *(undefined4 *)(param_1 + 8) = 0xffffffff;
      }
    }
    FUN_005453c0();
    uVar3 = 0;
  }
  else {
LAB_005a9d0c:
    uVar3 = 1;
  }
  ExceptionList = local_c;
  return uVar3;
}


