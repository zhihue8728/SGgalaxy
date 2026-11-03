// xrefs to FUN_005a8da0: 00526763(005266b0) 0057aa9a(0057a9a0) 005c97e3(005c96b0) 005c912a(005c8ff0) 005c9296(005c8ff0) 004af30a(004af1e0) 004af369(004af1e0) 0054803a(00547f80) 00547e11(00547d30) 0054fd24(0054fc10) 0054ff06(0054fdb0) 0054a0ec(00549d30) 0042ebb1(0042eb40) 004ac8e5(004ac800) 004ac8fd(004ac800) 004ac420(004ac360) 004ac438(004ac360) 004f8a8d(004f8820) 004f8b80(004f8820) 0048b0c6(0048ade0) 005afb2e(005afa50) 005b2598(005b2470) 004b4a94(004b4980) 004b4b30(004b4980) 004b4b95(004b4980) 

/* WARNING: Function: __alloca_probe replaced with injection: alloca_probe */

void __thiscall FUN_005a8da0(int param_1,void *param_2,uint param_3,undefined4 param_4)

{
  int iVar1;
  uint uVar2;
  undefined4 uVar3;
  int extraout_ECX;
  uint uVar4;
  char local_10000 [65532];
  undefined4 uStack_4;
  
  uStack_4 = 0x5a8daa;
  iVar1 = *(int *)(param_1 + 0x10);
  uVar2 = FUN_005a8680(iVar1 + *(int *)(param_1 + 4));
  uVar2 = uVar2 & 0xff;
  if (param_3 <= uVar2) {
    uVar3 = FUN_004ee140();
    FUN_0047e540(DAT_006ba7dc,"User %s string packet error1 : len %d, limit %d",uVar3,uVar2,param_3)
    ;
  }
  uVar4 = *(int *)(param_1 + 8) - *(int *)(param_1 + 4);
  if (uVar4 < uVar2 + 1) {
    uVar3 = FUN_004ee140();
    FUN_0047e540(DAT_006ba7dc,"User %s string packet error2 : len %d, limit %d, remain %d",uVar3,
                 uVar2,param_3,uVar4);
    uVar4 = 0;
    local_10000[0] = '\0';
    if (*(int *)(param_1 + 8) != 0) {
      do {
        _sprintf_s(local_10000,0x10000,"%s,%d",local_10000,
                   (uint)*(byte *)(uVar4 + *(int *)(param_1 + 0x10)));
        uVar4 = uVar4 + 1;
      } while (uVar4 < *(uint *)(param_1 + 8));
    }
    uVar3 = FUN_004ee140();
    FUN_0047e540(DAT_006ba7dc,"User %s error info : offset %d, inf %s, %s",uVar3,extraout_ECX + 1,
                 param_4,local_10000);
  }
  _memcpy(param_2,(void *)(extraout_ECX + 1 + iVar1),uVar2);
  *(undefined1 *)(uVar2 + (int)param_2) = 0;
  *(int *)(param_1 + 4) = *(int *)(param_1 + 4) + uVar2 + 1;
  return;
}


