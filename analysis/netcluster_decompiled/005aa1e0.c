// xrefs to FUN_005aa1e0: 0047e5a8(0047e540) 0049f186(0049f130) 0049f314(0049f2b0) 0049f7d5(0049f760) 0049f84b(0049f800) 004639e6(00463880) 005b4d05(005b4cb0) 00548e66(00548c50) 0047e7c1(0047e630) 00547855(00547820) 005478cb(00547880) 0054793b(005478f0) 004aad6b(004aaca0) 00547b35(00547b00) 00531a75(00531a20) 00548585(00548510) 0054ece5(0054ecb0) 00547ad8(00547a60) 005655ff(00565530) 0057d44e(0057d410) 005c600e(005c5fc0) 0056221d(00562130) 0057d321(0057d2d0) 004a26c8(004a2680) 00547290(00547250) 

void __fastcall FUN_005aa1e0(int param_1)

{
  int iVar1;
  
  *(undefined1 *)(*(int *)(param_1 + 8) + *(int *)(param_1 + 0x10)) = 0;
  *(int *)(param_1 + 8) = *(int *)(param_1 + 8) + 1;
  iVar1 = FUN_005a9240(*(undefined4 *)(param_1 + 0x10),*(undefined4 *)(param_1 + 8));
  if (iVar1 == -1) {
    FUN_005aa170(*(undefined4 *)(param_1 + 0x10),*(undefined4 *)(param_1 + 8));
  }
  else if (0 < *(int *)(DAT_00c32cc0 + 0x30)) {
    FUN_005a9d60();
    return;
  }
  return;
}


