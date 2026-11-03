
void __thiscall FUN_004ac360(int param_1,int param_2,undefined4 param_3)

{
  char cVar1;
  int iVar2;
  byte bVar3;
  undefined1 uVar4;
  int iVar5;
  uint uVar6;
  uint uVar7;
  uint uVar8;
  int *piVar9;
  char *pcVar10;
  undefined4 uVar11;
  undefined4 *puVar12;
  int iVar13;
  int *local_22c [2];
  uint local_224;
  undefined4 local_220;
  undefined4 local_21c;
  uint local_218;
  uint local_214;
  uint local_210;
  char local_20c [256];
  char local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  undefined4 local_4;
  
  local_4 = 0xffffffff;
  puStack_8 = &LAB_0062c41b;
  local_c = ExceptionList;
  ExceptionList = &local_c;
  FUN_00425740();
  local_4 = 0;
  bVar3 = FUN_005a8680(param_2);
  if (3 < bVar3) {
    FUN_004abcf0(param_2,param_3,"S_HERO_PUT",0);
  }
  uVar4 = FUN_005a8680(param_2 + 1);
  local_21c = CONCAT31(local_21c._1_3_,uVar4);
  FUN_005a8da0(local_20c,0x40,&DAT_00652650);
  FUN_005a8da0(local_10c,0x40,&DAT_00652650);
  iVar5 = FUN_005a86b0(param_2 + 2);
  local_220 = FUN_005a86b0(param_2 + 6);
  uVar6 = FUN_005a8690(param_2 + 10);
  uVar6 = uVar6 & 0xffff;
  uVar7 = FUN_005a8690(param_2 + 0xc);
  uVar7 = uVar7 & 0xffff;
  local_218 = FUN_005a8690(param_2 + 0xe);
  local_218 = local_218 & 0xffff;
  local_224 = FUN_005a8680(param_2 + 0x10);
  local_224 = local_224 & 0xff;
  local_210 = FUN_005a8680(param_2 + 0x11);
  local_210 = local_210 & 0xff;
  local_214 = FUN_005a8680(param_2 + 0x12);
  local_214 = local_214 & 0xff;
  uVar8 = FUN_005a8680(param_2 + 0x13);
  local_22c[0] = (int *)(uVar8 & 0xff);
  if (uVar6 < 0x40) {
    uVar6 = 0x40;
  }
  uVar8 = (uint)*(ushort *)(*(int *)(param_1 + 0x8564) + 0x1025f2);
  if ((int)(uVar8 - 0x40) <= (int)uVar6) {
    uVar6 = uVar8 - 0x41;
  }
  if (uVar7 < 0x40) {
    uVar7 = 0x40;
  }
  uVar8 = (uint)*(ushort *)(*(int *)(param_1 + 0x8564) + 0x1025f4);
  if ((int)(uVar8 - 0x40) <= (int)uVar7) {
    uVar7 = uVar8 - 0x41;
  }
  piVar9 = (int *)FUN_005ca290(iVar5);
  if ((piVar9 == (int *)0x0) && (piVar9 = (int *)FUN_005ca520(bVar3,iVar5), piVar9 == (int *)0x0)) {
    ExceptionList = local_c;
    return;
  }
  FUN_004d3050(local_220,local_220,bVar3,local_21c,1,0);
  if (iVar5 == *(int *)(DAT_006ba7d8 + 8)) {
    FUN_004c68a0(1);
  }
  piVar9[5] = local_218;
  piVar9[0x1c] = 0;
  *(int *)(DAT_006ba808 + 0x3c) = (int)(piVar9[4] * local_218) / 10;
  pcVar10 = local_20c;
  do {
    cVar1 = *pcVar10;
    pcVar10 = pcVar10 + 1;
  } while (cVar1 != '\0');
  if (0xc < (uint)((int)pcVar10 - (int)(local_20c + 1))) {
    uVar11 = FUN_004ee140();
    FUN_0047e540(DAT_006ba7dc,"%s User Name length invalid",uVar11);
  }
  _strcpy_s((char *)(piVar9 + 0x1e),0x41,local_20c);
  _strcpy_s((char *)((int)piVar9 + 0xb9),0xd,local_20c);
  _strcpy_s((char *)((int)piVar9 + 0xc6),0x41,local_10c);
  piVar9[0xd8] = local_224;
  piVar9[0xd9] = local_210;
  piVar9[0xda] = local_214;
  piVar9[0xdb] = (int)local_22c[0];
  piVar9[0x45] = 0;
  piVar9[0x44] = 100;
  FUN_004cb370(100);
  piVar9[0x56] = 0;
  piVar9[0x57] = 0;
  iVar5 = *(int *)(piVar9[*(ushort *)((int)piVar9 + 0xf0ae) + 0x3b2b] + 4) + 7;
  if (*(char *)(*(int *)(DAT_006ba7cc + 0x8564) + 0x3f8) == '\0') {
    iVar5 = (int)(iVar5 + (iVar5 >> 0x1f & 7U)) >> 3;
  }
  else {
    iVar5 = ((int)(iVar5 + (iVar5 >> 0x1f & 7U)) >> 3) * 2;
  }
  puVar12 = (undefined4 *)FUN_00420110(local_22c,uVar6,uVar7,iVar5,1,0);
  FUN_004c75c0(*puVar12,puVar12[1]);
  FUN_00438ca0();
  FUN_004d49a0();
  if (*(char *)((int)piVar9 + 0x69) != '\0') {
    iVar5 = *(int *)(*(int *)(param_1 + 0x8564) + 0x134);
    iVar2 = *(int *)(*(int *)(param_1 + 0x8564) + 0x130);
    local_22c[0] = (int *)(**(code **)(*piVar9 + 0x14))();
    iVar13 = (**(code **)(*piVar9 + 0x14))();
    FUN_0049a0e0(*local_22c[0] - iVar2 / 2,*(int *)(iVar13 + 4) - iVar5 / 2);
    FUN_0049ab30();
  }
  FUN_00425760();
  if (*(char *)(*(int *)(DAT_006ba7cc + 0x8564) + 0x3f8) != '\0') {
    FUN_0051d1f0(0x1d);
  }
  ExceptionList = local_c;
  return;
}


