// xrefs to FUN_005a86e0: 005c9336(005c8ff0) 004acc00(004ac800) 00546633(005461a0) 00546cf1(005461a0) 

longlong FUN_005a86e0(undefined1 *param_1)

{
  longlong lVar1;
  
  lVar1 = __allmul(*param_1,0,0x100,0);
  lVar1 = __allmul(lVar1 + (ulonglong)(byte)param_1[1],0x100,0);
  lVar1 = __allmul(lVar1 + (ulonglong)(byte)param_1[2],0x100,0);
  lVar1 = __allmul(lVar1 + (ulonglong)(byte)param_1[3],0x100,0);
  lVar1 = __allmul(lVar1 + (ulonglong)(byte)param_1[4],0x100,0);
  lVar1 = __allmul(lVar1 + (ulonglong)(byte)param_1[5],0x100,0);
  lVar1 = __allmul(lVar1 + (ulonglong)(byte)param_1[6],0x100,0);
  return lVar1 + (ulonglong)(byte)param_1[7];
}


