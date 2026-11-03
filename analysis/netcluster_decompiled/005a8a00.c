// xrefs to FUN_005a8a00: 0065d2c0(-) 

undefined4 * __thiscall FUN_005a8a00(undefined4 *param_1,byte param_2)

{
  *param_1 = CSingletonBase<CSocket>::vftable;
  DAT_00c32cc0 = 0;
  if ((param_2 & 1) != 0) {
                    /* WARNING: Subroutine does not return */
    _free(param_1);
  }
  return param_1;
}


