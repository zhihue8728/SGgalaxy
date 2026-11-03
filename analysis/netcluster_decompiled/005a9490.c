// xrefs to FUN_005a9490: 0064c738(-) 0065d3c4(-) 

void * __thiscall FUN_005a9490(void *param_1,byte param_2)

{
  FUN_005a8f50();
  if ((param_2 & 1) != 0) {
                    /* WARNING: Subroutine does not return */
    _free(param_1);
  }
  return param_1;
}


