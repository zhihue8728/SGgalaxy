// xrefs to FUN_005a81e0: 0065d160(-) 

void __fastcall FUN_005a81e0(uint param_1)

{
  char cVar1;
  char *pcVar2;
  char *pcVar3;
  char local_124 [240];
  undefined4 uStack_34;
  undefined4 uStack_30;
  undefined4 uStack_2c;
  undefined4 uStack_28;
  uint local_24;
  uint local_20;
  uint local_1c;
  uint local_18;
  uint local_14;
  undefined4 local_10;
  undefined4 local_c;
  undefined4 local_8;
  
  _strcpy_s(local_124,0x100,"@ pmw-bk.xpf 0");
  local_14 = -(uint)(param_1 != 4) & param_1;
  local_24 = 0;
  local_20 = 0;
  local_1c = 0x101;
  local_18 = 0xb1;
  local_10 = 0xf0;
  local_c = 0;
  local_8 = 0;
  (**(code **)(*(int *)(param_1 + 0x360) + 0x40))(local_124);
  _strcpy_s(&stack0xfffffed8,0x100,"@ pmw-buts.xpf 0");
  local_18 = -(uint)(param_1 != 4) & param_1;
  local_14 = 0xf0;
  uStack_28 = 0x3b;
  local_24 = 0x30;
  local_20 = 0x95;
  local_1c = 0x13;
  local_10 = 0;
  local_c = 0x10;
  (**(code **)(*(int *)(param_1 + 0x654) + 0x40))(&stack0xfffffed8);
  if (*(uint *)(param_1 + 0x324) < 0x10) {
    pcVar3 = (char *)(param_1 + 0x310);
  }
  else {
    pcVar3 = *(char **)(param_1 + 0x310);
  }
  pcVar2 = pcVar3;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  FUN_004026a0(pcVar3,(int)pcVar2 - (int)(pcVar3 + 1));
  _strcpy_s(&stack0xfffffed4,0x100,"@ pmw-buts.xpf 3");
  local_1c = -(uint)(param_1 != 4) & param_1;
  uStack_2c = 0x3b;
  uStack_28 = 0x4f;
  local_24 = 0x95;
  local_20 = 0x13;
  local_18 = 0xf0;
  local_14 = 0;
  local_10 = 0x11;
  (**(code **)(*(int *)(param_1 + 0xdac) + 0x40))(&stack0xfffffed4);
  if (*(uint *)(param_1 + 0x340) < 0x10) {
    pcVar3 = (char *)(param_1 + 0x32c);
  }
  else {
    pcVar3 = *(char **)(param_1 + 0x32c);
  }
  pcVar2 = pcVar3;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  FUN_004026a0(pcVar3,(int)pcVar2 - (int)(pcVar3 + 1));
  _strcpy_s(&stack0xfffffed0,0x100,"@ pmw-buts.xpf 6");
  local_20 = -(uint)(param_1 != 4) & param_1;
  uStack_30 = 0x3b;
  uStack_2c = 0x6e;
  uStack_28 = 0x95;
  local_24 = 0x13;
  local_1c = 0xf0;
  local_18 = 0;
  local_14 = 0x12;
  (**(code **)(*(int *)(param_1 + 0x1504) + 0x40))(&stack0xfffffed0);
  if (*(uint *)(param_1 + 0x35c) < 0x10) {
    pcVar3 = (char *)(param_1 + 0x348);
  }
  else {
    pcVar3 = *(char **)(param_1 + 0x348);
  }
  pcVar2 = pcVar3;
  do {
    cVar1 = *pcVar2;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  FUN_004026a0(pcVar3,(int)pcVar2 - (int)(pcVar3 + 1));
  _strcpy_s(&stack0xfffffecc,0x100,"@ pmw-buts.xpf 9");
  local_24 = -(uint)(param_1 != 4) & param_1;
  uStack_34 = 0x66;
  uStack_30 = 0x94;
  uStack_2c = 0x43;
  uStack_28 = 0x16;
  local_20 = 0xf0;
  local_1c = 0;
  local_18 = 0x13;
  (**(code **)(*(int *)(param_1 + 0x1c5c) + 0x40))(&stack0xfffffecc);
  return;
}


