// xrefs to FUN_005a8a50: 004ee1d1(004ee140) 005a9663(005a9600) 00548d26(00548c50) 004a26e7(004a2680) 005a9cd7(005a97c0) 00544962(00544720) 00548ac9(00548a50) 005a8abe(005a8a80) 004a2a4a(004a2910) 004a2bdf(004a2910) 004a2cf5(004a2910) 004a2dc1(004a2910) 004a2eda(004a2910) 00545119(00545110) 0053332c(00533310) 

undefined4 __fastcall FUN_005a8a50(int param_1)

{
  if (*(char *)(DAT_006ba818 + 0x50) == '\0') {
    Ordinal_3(*(undefined4 *)(param_1 + 8));
    *(undefined4 *)(param_1 + 8) = 0xffffffff;
  }
  return 1;
}


