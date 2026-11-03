// xrefs to FUN_00545ca0: 0054a5df(0054a590) 0054a5f1(0054a590) 00545ce9(00545ca0) 

void __thiscall FUN_00545ca0(int param_1,int *param_2)

{
  char cVar1;
  undefined4 uVar2;
  int iVar3;
  
  if (*(char *)(param_1 + 0xc30) == '\0') {
    iVar3 = 0;
    if (0 < param_2[0x52]) {
      do {
        if (*(char *)(param_1 + 0xc30) != '\0') {
          return;
        }
        if (((param_2[0x54] == 0) || (iVar3 < 0)) || (param_2[0x52] <= iVar3)) {
          uVar2 = 0;
        }
        else {
          uVar2 = *(undefined4 *)(param_2[0x54] + iVar3 * 4);
        }
        FUN_00545ca0(uVar2);
        iVar3 = iVar3 + 1;
      } while (iVar3 < param_2[0x52]);
    }
    if (((*(char *)(param_1 + 0xc30) == '\0') && (*(char *)((int)param_2 + 0x155) != '\0')) &&
       (cVar1 = (**(code **)(*param_2 + 0x1c))
                          (*(undefined4 *)(param_1 + 0xc34),*(undefined4 *)(param_1 + 0xc38)),
       cVar1 != '\0')) {
      *(undefined1 *)(param_1 + 0xc30) = 1;
    }
  }
  return;
}


