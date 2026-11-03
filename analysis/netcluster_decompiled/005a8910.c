// xrefs to FUN_005a8910: 005a8cee(005a8c80) 005a8d28(005a8c80) 005a8d5d(005a8c80) 005a8b99(005a8ad0) 005a8bd6(005a8ad0) 005a8bff(005a8ad0) 

void FUN_005a8910(uint *param_1,uint *param_2,uint param_3,int param_4,int param_5)

{
  undefined4 uVar1;
  int iVar2;
  int iVar3;
  uint *puVar4;
  uint *puVar5;
  
  iVar2 = 0;
  puVar4 = param_2;
  puVar5 = param_1;
  if (param_3 >> 2 != 0) {
    do {
      iVar3 = iVar2 % param_5;
      iVar2 = iVar2 + 1;
      param_1 = puVar5 + 1;
      param_2 = puVar4 + 1;
      *puVar4 = *(uint *)(param_4 + iVar3 * 4) ^ *puVar5;
      puVar4 = param_2;
      puVar5 = param_1;
    } while (iVar2 < (int)(param_3 >> 2));
  }
  param_3 = param_3 & 3;
  if (param_3 != 0) {
    uVar1 = *(undefined4 *)(param_4 + (iVar2 % param_5) * 4);
    if (param_3 == 1) {
      *(byte *)param_2 = (byte)*param_1 ^ (byte)uVar1;
    }
    else {
      if (param_3 == 2) {
        *(ushort *)param_2 = (ushort)*param_1 ^ (ushort)uVar1;
        return;
      }
      if (param_3 == 3) {
        *(ushort *)param_2 = (ushort)*param_1 ^ (ushort)uVar1;
        *(byte *)((int)param_2 + 2) = (byte)((uint)uVar1 >> 0x10) ^ *(byte *)((int)param_1 + 2);
        return;
      }
    }
  }
  return;
}


