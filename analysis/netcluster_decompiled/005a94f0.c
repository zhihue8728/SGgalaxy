// xrefs to FUN_005a94f0: 0047f349(0047f310) 00549774(00549770) 0058b836(0058b800) 0058b84b(0058b800) 005a9ed2(005a9e80) 

void FUN_005a94f0(void)

{
  int iVar1;
  
  iVar1 = FUN_006094fc(0xc);
  if (iVar1 != 0) {
    *(int *)iVar1 = iVar1;
  }
  if ((int *)(iVar1 + 4) != (int *)0x0) {
    *(int *)(iVar1 + 4) = iVar1;
  }
  return;
}


