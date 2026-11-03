// xrefs to FUN_005a9240: 005aa1ff(005aa1e0) 005a9dc5(005a9d60) 

undefined4 __thiscall FUN_005a9240(int param_1,undefined1 *param_2,size_t param_3)

{
  undefined4 uVar1;
  undefined4 uVar2;
  
  uVar2 = DAT_006ba7dc;
  if (*(char *)(DAT_006ba818 + 0x50) != '\0') {
    return 0;
  }
  switch(*param_2) {
  case 0:
  case 1:
  case 5:
  case 6:
  case 0xd:
    if (0x3ffdf < (int)param_3) {
LAB_005a92ab:
      uVar1 = FUN_00545260(*param_2);
      FUN_0047e540(uVar2,"S_%d O_%d Packet Too Long. Type : %d",DAT_00d69268,uVar1);
      return 0;
    }
    **(undefined1 **)(param_1 + 0x18) = 0xaa;
    FUN_005a85b0(param_3,*(int *)(param_1 + 0x18) + 1);
    _memcpy((void *)(*(int *)(param_1 + 0x18) + 3),param_2,param_3);
    break;
  default:
    if (0x3ffdf < (int)param_3) goto LAB_005a92ab;
    param_3 = FUN_005a8c80(param_2,param_3,*(int *)(param_1 + 0x18) + 3);
    **(undefined1 **)(param_1 + 0x18) = 0xaa;
    FUN_005a85b0(param_3,*(int *)(param_1 + 0x18) + 1);
  }
  uVar2 = Ordinal_19(*(undefined4 *)(param_1 + 8),*(undefined4 *)(param_1 + 0x18),param_3 + 3,0);
  return uVar2;
}


