
void FUN_005461a0(undefined1 *param_1,undefined4 param_2)

{
  bool bVar1;
  undefined1 uVar2;
  byte bVar3;
  char cVar4;
  char cVar5;
  char cVar6;
  int iVar7;
  undefined4 uVar8;
  int iVar9;
  undefined4 uVar10;
  undefined4 uVar11;
  undefined4 uVar12;
  uint uVar13;
  uint uVar14;
  uint uVar15;
  undefined4 uVar16;
  uint uVar17;
  uint uVar18;
  uint uVar19;
  uint uVar20;
  uint uVar21;
  uint uVar22;
  undefined8 uVar23;
  undefined1 *puVar24;
  undefined4 uVar25;
  undefined4 uVar26;
  undefined4 uVar27;
  uint uVar28;
  uint uVar29;
  undefined4 uVar30;
  uint uVar31;
  uint uVar32;
  uint uVar33;
  uint uVar34;
  uint uVar35;
  uint uVar36;
  uint uVar37;
  uint uVar38;
  uint uVar39;
  undefined1 *puVar40;
  uint uVar41;
  int iVar42;
  undefined4 local_288;
  undefined4 local_284;
  char local_27d;
  uint local_27c;
  uint local_278;
  uint local_274;
  uint local_270;
  uint local_26c;
  uint local_268;
  uint local_264;
  undefined4 local_260;
  undefined4 local_25c;
  undefined4 local_258;
  uint local_254;
  undefined4 local_250;
  uint local_24c;
  uint local_248;
  uint local_244;
  uint local_240;
  uint local_23c;
  uint local_238;
  uint local_234;
  uint local_230;
  uint local_22c;
  uint local_228;
  uint local_224;
  undefined4 local_220;
  uint local_21c;
  undefined8 local_218;
  int local_210;
  undefined1 local_20c [256];
  undefined1 local_10c [256];
  void *local_c;
  undefined1 *puStack_8;
  int local_4;
  
  puStack_8 = &LAB_00634729;
  local_c = ExceptionList;
  local_4 = 0;
  iVar42 = 1;
  ExceptionList = &local_c;
  uVar2 = FUN_005a8680(param_1,CReceivedPacketEx::vftable,1,param_2,*param_1,param_1);
  bVar1 = false;
  uVar17 = 1;
  iVar9 = iVar42;
  switch(uVar2) {
  case 1:
    FUN_004f2c50();
    if (((DAT_006ba7cc != 0) && (*(int *)(DAT_006ba7cc + 0x29b00) != 0)) &&
       (*(int *)(DAT_006ba7c8 + 0xc0c) == *(int *)(DAT_006ba7cc + 0x29b00))) {
      FUN_00483810();
    }
    iVar9 = iVar42 + 1;
    uVar17 = FUN_005a8680(param_1 + iVar42);
    uVar17 = uVar17 & 0xff;
  case 2:
    if (uVar17 != 0) {
      do {
        local_27c = uVar17;
        iVar42 = iVar9 + 4;
        local_284 = FUN_005a86b0(param_1 + iVar9);
        iVar9 = iVar42 + 1;
        bVar3 = FUN_005a8680(param_1 + iVar42);
        iVar42 = iVar9 + 1;
        uVar2 = FUN_005a8680(param_1 + iVar9);
        local_250 = CONCAT31(local_250._1_3_,uVar2);
        iVar9 = iVar42 + 2;
        uVar17 = FUN_005a8690(param_1 + iVar42);
        uVar17 = uVar17 & 0xffff;
        iVar42 = iVar9 + 4;
        uVar10 = FUN_005a86b0(param_1 + iVar9);
        iVar9 = iVar42 + 4;
        uVar11 = FUN_005a86b0(param_1 + iVar42);
        iVar42 = iVar9 + 4;
        local_258 = FUN_005a86b0(param_1 + iVar9);
        iVar9 = iVar42 + 1;
        uVar2 = FUN_005a8680(param_1 + iVar42);
        local_260 = CONCAT31(local_260._1_3_,uVar2);
        iVar42 = iVar9 + 1;
        cVar4 = FUN_005a8680(param_1 + iVar9);
        iVar9 = iVar42 + 1;
        cVar5 = FUN_005a8680(param_1 + iVar42);
        cVar5 = cVar5 + -1;
        iVar42 = iVar9 + 2;
        local_268 = FUN_005a8690(param_1 + iVar9);
        local_268 = local_268 & 0xffff;
        iVar9 = iVar42 + 2;
        local_270 = FUN_005a8690(param_1 + iVar42);
        local_270 = local_270 & 0xffff;
        iVar42 = iVar9 + 2;
        local_274 = FUN_005a8690(param_1 + iVar9);
        local_274 = local_274 & 0xffff;
        iVar9 = iVar42 + 2;
        local_244 = FUN_005a8690(param_1 + iVar42);
        local_244 = local_244 & 0xffff;
        iVar42 = iVar9 + 2;
        local_21c = FUN_005a8690(param_1 + iVar9);
        local_21c = local_21c & 0xffff;
        iVar9 = iVar42 + 2;
        local_24c = FUN_005a8690(param_1 + iVar42);
        local_24c = local_24c & 0xffff;
        iVar42 = iVar9 + 2;
        local_278 = FUN_005a8690(param_1 + iVar9);
        local_278 = local_278 & 0xffff;
        iVar9 = iVar42 + 2;
        local_254 = FUN_005a8690(param_1 + iVar42);
        local_254 = local_254 & 0xffff;
        iVar42 = iVar9 + 2;
        local_22c = FUN_005a8690(param_1 + iVar9);
        local_22c = local_22c & 0xffff;
        iVar9 = iVar42 + 1;
        uVar2 = FUN_005a8680(param_1 + iVar42);
        local_25c = CONCAT31(local_25c._1_3_,uVar2);
        iVar42 = iVar9 + 2;
        local_234 = FUN_005a8690(param_1 + iVar9);
        local_234 = local_234 & 0xffff;
        iVar9 = iVar42 + 2;
        local_264 = FUN_005a8690(param_1 + iVar42);
        local_264 = local_264 & 0xffff;
        iVar42 = iVar9 + 2;
        local_23c = FUN_005a8690(param_1 + iVar9);
        local_23c = local_23c & 0xffff;
        iVar9 = iVar42 + 2;
        local_26c = FUN_005a8690(param_1 + iVar42);
        local_26c = local_26c & 0xffff;
        iVar42 = iVar9 + 2;
        local_238 = FUN_005a8690(param_1 + iVar9);
        local_238 = local_238 & 0xffff;
        iVar9 = iVar42 + 2;
        local_228 = FUN_005a8690(param_1 + iVar42);
        local_228 = local_228 & 0xffff;
        iVar42 = iVar9 + 2;
        local_240 = FUN_005a8690(param_1 + iVar9);
        local_240 = local_240 & 0xffff;
        iVar9 = iVar42 + 2;
        local_248 = FUN_005a8690(param_1 + iVar42);
        local_248 = local_248 & 0xffff;
        iVar42 = iVar9 + 2;
        local_230 = FUN_005a8690(param_1 + iVar9);
        local_230 = local_230 & 0xffff;
        iVar7 = iVar42 + 8;
        uVar23 = FUN_005a86e0(param_1 + iVar42);
        iVar9 = iVar7 + 2;
        local_218 = uVar23;
        local_224 = FUN_005a8690(param_1 + iVar7);
        local_224 = local_224 & 0xffff;
        local_220 = 0;
        FUN_005a8da0(local_10c,0x40,&DAT_00652650);
        FUN_005a8da0(local_20c,0x40,&DAT_00652650);
        bVar3 = bVar3 & 0xf;
        if ((bVar3 == 0) || (2 < bVar3)) {
          uVar10 = FUN_004ee140();
          FUN_0047e540(DAT_006ba7dc,"%s got invalid unit of type %d",uVar10,bVar3);
        }
        else {
          local_210 = FUN_0055f0d0(0xf8);
          local_4._0_1_ = 1;
          if (local_210 == 0) {
            local_288 = 0;
          }
          else {
            local_288 = FUN_005c5840();
          }
          puVar40 = local_20c;
          uVar15 = local_278 & 0xffff;
          uVar20 = local_24c & 0xffff;
          uVar13 = local_21c & 0xffff;
          uVar18 = local_244 & 0xffff;
          uVar21 = local_274 & 0xffff;
          uVar14 = local_270 & 0xffff;
          uVar19 = local_268 & 0xffff;
          uVar22 = (uint)bVar3;
          puVar24 = local_10c;
          local_4 = (uint)local_4._1_3_ << 8;
          uVar12 = local_284;
          uVar25 = local_250;
          uVar26 = local_258;
          uVar27 = local_260;
          uVar28 = local_254;
          uVar29 = local_22c;
          uVar30 = local_25c;
          uVar31 = local_234;
          uVar32 = local_264;
          uVar33 = local_23c;
          uVar34 = local_26c;
          uVar35 = local_238;
          uVar36 = local_228;
          uVar37 = local_240;
          uVar38 = local_248;
          uVar39 = local_230;
          uVar41 = local_224;
          uVar16 = local_220;
          uVar23 = local_218;
          uVar8 = FUN_00407f70(local_284,puVar24,uVar22,local_250,uVar10,uVar11,local_258,local_260,
                               uVar19,uVar14,uVar21,uVar18,uVar13,uVar20,uVar15,local_254,local_22c,
                               local_25c,local_234,local_264,local_23c,local_26c,local_238,local_228
                               ,local_240,local_248,local_230,local_218,uVar17,puVar40,local_224,
                               local_220);
          FUN_005c5bb0(uVar8,uVar12,puVar24,uVar22,uVar25,uVar10,uVar11,uVar26,uVar27,uVar19,uVar14,
                       uVar21,uVar18,uVar13,uVar20,uVar15,uVar28,uVar29,uVar30,uVar31,uVar32,uVar33,
                       uVar34,uVar35,uVar36,uVar37,uVar38,uVar39,uVar23,uVar17,puVar40,uVar41,uVar16
                      );
          if (cVar4 == '\0') {
            uVar10 = local_288;
            uVar11 = FUN_004edb80(local_288);
            FUN_004edb50(uVar11,uVar10);
          }
          else {
            iVar42 = FUN_004edb40(cVar5);
            if (iVar42 == 0) {
              FUN_004edb20(cVar5,local_288);
            }
            else {
              uVar10 = FUN_004ee140();
              uVar11 = FUN_004ee140();
              FUN_0047e540(DAT_006ba7dc,"%s Wrong hot key : %d (User : %s)",uVar11,cVar5,uVar10);
              bVar1 = true;
              uVar10 = local_288;
              uVar11 = FUN_004edb80(local_288);
              FUN_004edb50(uVar11,uVar10);
            }
          }
        }
        local_27c = local_27c - 1;
        uVar17 = local_27c;
      } while (local_27c != 0);
      if (bVar1) {
        uVar10 = FUN_004ee140();
        uVar11 = FUN_004ee140();
        FUN_0047e540(DAT_006ba7dc,"%s hot key duplication (User : %s)",uVar11,uVar10);
        FUN_004ee510();
      }
    }
    if (((DAT_006ba7cc != 0) && (*(int *)(DAT_006ba7cc + 0x29b00) != 0)) &&
       (*(int *)(DAT_006ba7c8 + 0xc0c) == *(int *)(DAT_006ba7cc + 0x29b00))) {
      FUN_0048ab20(local_284);
    }
    break;
  case 3:
    uVar10 = FUN_005a86b0(param_1 + iVar42);
    if (((DAT_006ba7cc != 0) && (*(int *)(DAT_006ba7cc + 0x29b00) != 0)) &&
       (*(int *)(DAT_006ba7c8 + 0xc0c) == *(int *)(DAT_006ba7cc + 0x29b00))) {
      FUN_00483820(uVar10);
    }
    FUN_004ee430(uVar10);
    break;
  case 4:
    iVar9 = iVar42 + 4;
    uVar10 = FUN_005a86b0(param_1 + iVar42);
    iVar42 = iVar9 + 1;
    bVar3 = FUN_005a8680(param_1 + iVar9);
    iVar9 = iVar42 + 1;
    uVar2 = FUN_005a8680(param_1 + iVar42);
    local_250 = CONCAT31(local_250._1_3_,uVar2);
    iVar42 = iVar9 + 2;
    uVar17 = FUN_005a8690(param_1 + iVar9);
    uVar17 = uVar17 & 0xffff;
    iVar9 = iVar42 + 4;
    uVar11 = FUN_005a86b0(param_1 + iVar42);
    iVar42 = iVar9 + 4;
    local_210 = FUN_005a86b0(param_1 + iVar9);
    iVar9 = iVar42 + 4;
    local_258 = FUN_005a86b0(param_1 + iVar42);
    iVar42 = iVar9 + 1;
    uVar2 = FUN_005a8680(param_1 + iVar9);
    local_260 = CONCAT31(local_260._1_3_,uVar2);
    iVar9 = iVar42 + 1;
    cVar4 = FUN_005a8680(param_1 + iVar42);
    iVar42 = iVar9 + 1;
    cVar5 = FUN_005a8680(param_1 + iVar9);
    cVar5 = cVar5 + -1;
    iVar9 = iVar42 + 2;
    local_268 = FUN_005a8690(param_1 + iVar42);
    local_268 = local_268 & 0xffff;
    iVar42 = iVar9 + 2;
    local_270 = FUN_005a8690(param_1 + iVar9);
    local_270 = local_270 & 0xffff;
    iVar9 = iVar42 + 2;
    local_274 = FUN_005a8690(param_1 + iVar42);
    local_274 = local_274 & 0xffff;
    iVar42 = iVar9 + 2;
    local_244 = FUN_005a8690(param_1 + iVar9);
    local_244 = local_244 & 0xffff;
    iVar9 = iVar42 + 2;
    local_21c = FUN_005a8690(param_1 + iVar42);
    local_21c = local_21c & 0xffff;
    iVar42 = iVar9 + 2;
    local_24c = FUN_005a8690(param_1 + iVar9);
    local_24c = local_24c & 0xffff;
    iVar9 = iVar42 + 2;
    local_278 = FUN_005a8690(param_1 + iVar42);
    local_278 = local_278 & 0xffff;
    iVar42 = iVar9 + 2;
    local_254 = FUN_005a8690(param_1 + iVar9);
    local_254 = local_254 & 0xffff;
    iVar9 = iVar42 + 2;
    local_22c = FUN_005a8690(param_1 + iVar42);
    local_22c = local_22c & 0xffff;
    iVar42 = iVar9 + 1;
    uVar2 = FUN_005a8680(param_1 + iVar9);
    local_25c = CONCAT31(local_25c._1_3_,uVar2);
    iVar9 = iVar42 + 2;
    local_234 = FUN_005a8690(param_1 + iVar42);
    local_234 = local_234 & 0xffff;
    iVar42 = iVar9 + 2;
    local_264 = FUN_005a8690(param_1 + iVar9);
    local_264 = local_264 & 0xffff;
    iVar9 = iVar42 + 2;
    local_23c = FUN_005a8690(param_1 + iVar42);
    local_23c = local_23c & 0xffff;
    iVar42 = iVar9 + 2;
    local_26c = FUN_005a8690(param_1 + iVar9);
    local_26c = local_26c & 0xffff;
    iVar9 = iVar42 + 2;
    local_238 = FUN_005a8690(param_1 + iVar42);
    local_238 = local_238 & 0xffff;
    iVar42 = iVar9 + 2;
    local_228 = FUN_005a8690(param_1 + iVar9);
    local_228 = local_228 & 0xffff;
    iVar9 = iVar42 + 2;
    local_240 = FUN_005a8690(param_1 + iVar42);
    local_240 = local_240 & 0xffff;
    iVar42 = iVar9 + 2;
    local_248 = FUN_005a8690(param_1 + iVar9);
    local_248 = local_248 & 0xffff;
    iVar9 = iVar42 + 2;
    local_230 = FUN_005a8690(param_1 + iVar42);
    local_230 = local_230 & 0xffff;
    iVar42 = iVar9 + 8;
    local_218 = FUN_005a86e0(param_1 + iVar9);
    local_224 = FUN_005a8690(param_1 + iVar42);
    local_224 = local_224 & 0xffff;
    local_220 = 0;
    FUN_005a8da0(local_10c,0x40,&DAT_00652650);
    FUN_005a8da0(local_20c,0x40,&DAT_00652650);
    bVar3 = bVar3 & 0xf;
    if ((bVar3 == 0) || (2 < bVar3)) {
      uVar10 = FUN_004ee140();
      FUN_0047e540(DAT_006ba7dc,"%s got invalid unit of type %d",uVar10,bVar3);
      ExceptionList = local_c;
      return;
    }
    cVar6 = FUN_004ee3a0(uVar10,&local_288,&local_27d,&local_27c);
    if (cVar6 == '\0') {
      ExceptionList = local_c;
      return;
    }
    if (cVar4 == '\0') {
      if (local_27d != '\0') {
        local_284 = DAT_006ba7d8;
        local_27c = FUN_004edb80(local_288);
      }
LAB_00546e5e:
      FUN_004edb50(local_27c,local_288);
    }
    else {
      iVar9 = FUN_004edb40(cVar5);
      if (iVar9 != 0) {
        local_284 = FUN_004ee140();
        uVar12 = FUN_004ee140();
        FUN_0047e540(DAT_006ba7dc,"%s Wrong hot key : %d (User : %s)",uVar12,cVar5,local_284);
        bVar1 = true;
        local_284 = DAT_006ba7d8;
        local_27c = FUN_004edb80(local_288);
        goto LAB_00546e5e;
      }
      FUN_004edb20(cVar5,local_288);
    }
    puVar40 = local_20c;
    uVar18 = local_278 & 0xffff;
    uVar21 = local_24c & 0xffff;
    uVar13 = local_21c & 0xffff;
    uVar19 = local_244 & 0xffff;
    uVar22 = local_274 & 0xffff;
    uVar14 = local_270 & 0xffff;
    uVar20 = local_268 & 0xffff;
    uVar15 = (uint)bVar3;
    puVar24 = local_10c;
    uVar12 = local_250;
    iVar9 = local_210;
    uVar25 = local_258;
    uVar26 = local_260;
    uVar28 = local_254;
    uVar29 = local_22c;
    uVar27 = local_25c;
    uVar31 = local_234;
    uVar32 = local_264;
    uVar33 = local_23c;
    uVar34 = local_26c;
    uVar35 = local_238;
    uVar36 = local_228;
    uVar37 = local_240;
    uVar38 = local_248;
    uVar39 = local_230;
    uVar41 = local_224;
    uVar30 = local_220;
    uVar23 = local_218;
    uVar16 = FUN_00407f70(uVar10,puVar24,uVar15,local_250,uVar11,local_210,local_258,local_260,
                          uVar20,uVar14,uVar22,uVar19,uVar13,uVar21,uVar18,local_254,local_22c,
                          local_25c,local_234,local_264,local_23c,local_26c,local_238,local_228,
                          local_240,local_248,local_230,local_218,uVar17,puVar40,local_224,local_220
                         );
    FUN_005c5bb0(uVar16,uVar10,puVar24,uVar15,uVar12,uVar11,iVar9,uVar25,uVar26,uVar20,uVar14,uVar22
                 ,uVar19,uVar13,uVar21,uVar18,uVar28,uVar29,uVar27,uVar31,uVar32,uVar33,uVar34,
                 uVar35,uVar36,uVar37,uVar38,uVar39,uVar23,uVar17,puVar40,uVar41,uVar30);
    if (bVar1) {
      uVar10 = FUN_004ee140();
      FUN_0047e540(DAT_006ba7dc,"hot key duplication (User : %s)",uVar10);
      FUN_004ee510();
    }
  }
  ExceptionList = local_c;
  return;
}


