// xrefs to FUN_005aa250: 0065efd0(-) 

undefined4 * __thiscall FUN_005aa250(undefined4 *param_1,byte param_2)

{
  *param_1 = CSingletonBase<CSoundManager>::vftable;
  DAT_006ba7c4 = 0;
  if ((param_2 & 1) != 0) {
                    /* WARNING: Subroutine does not return */
    _free(param_1);
  }
  return param_1;
}


