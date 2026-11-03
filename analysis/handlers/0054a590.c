// xrefs to FUN_0054a590: 0054ad78(0054abf0) 0047903a(00478ec0) 005449fc(00544720) 

undefined4 __thiscall
FUN_0054a590(int param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4)

{
  char cVar1;
  
  cVar1 = FUN_0054a1d0(param_3,param_4);
  if (cVar1 == '\0') {
    if ((DAT_006ba7cc != 0) && (cVar1 = FUN_004b5670(param_3,param_4), cVar1 != '\0')) {
      return 0;
    }
    *(undefined1 *)(param_1 + 0xc30) = 0;
    *(undefined4 *)(param_1 + 0xc34) = param_3;
    *(undefined4 *)(param_1 + 0xc38) = param_4;
    if (DAT_00c346e8 != 0) {
      FUN_00545ca0(DAT_00c346e8 + 4);
      return 0;
    }
    FUN_00545ca0(0);
  }
  return 0;
}


