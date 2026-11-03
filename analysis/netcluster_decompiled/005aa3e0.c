// xrefs to FUN_005aa3e0: 005aba5d(005ab890) 

/* WARNING: Removing unreachable block (ram,0x005aa4eb) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __thiscall
FUN_005aa3e0(int param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4,int param_5)

{
  int iVar1;
  uint uVar2;
  undefined4 *puVar3;
  char unaff_DI;
  uint uVar4;
  int in_stack_00000020;
  undefined4 *in_stack_00000024;
  char cVar5;
  undefined4 uVar6;
  undefined4 uVar7;
  float fVar8;
  int iVar9;
  int iVar10;
  
  if (*(int *)(param_1 + 0x68) == 0) {
    return 0;
  }
  uVar4 = 0;
  if (*(int *)(param_1 + 0x288) != 0) {
    puVar3 = (undefined4 *)(param_1 + 0x6c);
    do {
      iVar1 = _AIL_3D_sample_status_4(*puVar3);
      if (iVar1 == 2) {
        if (in_stack_00000024 != (undefined4 *)0x0) {
          *in_stack_00000024 = *puVar3;
        }
        iVar1 = _AIL_set_3D_sample_file_8(*puVar3,param_3);
        if (iVar1 != 0) {
          _AIL_set_3D_user_data_12(*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),0,param_5);
          if ((in_stack_00000020 == 3) || (in_stack_00000020 == 4)) {
            uVar2 = (uint)((ulonglong)(uint)(*(int *)(param_1 + 100) * param_5) * 0x51eb851f >> 0x20
                          );
          }
          else {
            uVar2 = (uint)((ulonglong)(uint)(*(int *)(param_1 + 0x60) * param_5) * 0x51eb851f >>
                          0x20);
          }
          _AIL_set_3D_sample_effects_level_8(*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),0);
          iVar9 = _DAT_0065f07c;
          iVar10 = _DAT_0065f080;
          _AIL_set_3D_sample_distances_12
                    (*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),_DAT_0065f07c,_DAT_0065f080);
          _AIL_set_3D_sample_cone_16
                    (*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),_DAT_0065f074,_DAT_0065f078,0);
          fVar8 = (float)(uVar2 >> 5) / (float)_DAT_0064ffc0;
          iVar1 = *(int *)(param_1 + 0x6c + uVar4 * 4);
          _AIL_set_3D_sample_volume_8(iVar1,fVar8);
          uVar7 = *(undefined4 *)(param_1 + 0x6c + uVar4 * 4);
          _AIL_set_3D_sample_loop_count_8(uVar7,unaff_DI == '\0');
          uVar6 = 0x3f800000;
          cVar5 = '\0';
          _AIL_set_3D_orientation_28
                    (*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),(float)-iVar9,0,(float)-iVar10,0,
                     0x3f800000,0);
          _AIL_set_3D_position_16
                    (*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),(float)iVar1,0,(float)(int)fVar8);
          _AIL_set_3D_user_data_12(*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),1,uVar7);
          _AIL_set_3D_user_data_12(*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),2,uVar6);
          _AIL_set_3D_user_data_12(*(undefined4 *)(param_1 + 0x6c + uVar4 * 4),3,uVar6);
          _AIL_start_3D_sample_4(*(undefined4 *)(param_1 + 0x6c + uVar4 * 4));
          if (cVar5 != '\0') {
            _AIL_stop_3D_sample_4(*(undefined4 *)(param_1 + 0x6c + uVar4 * 4));
          }
          return 1;
        }
      }
      uVar4 = uVar4 + 1;
      puVar3 = puVar3 + 1;
    } while (uVar4 < *(uint *)(param_1 + 0x288));
  }
  return 0;
}


