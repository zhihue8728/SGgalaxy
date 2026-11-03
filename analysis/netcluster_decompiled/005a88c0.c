// xrefs to FUN_005a88c0: 00548d0e(00548c50) 0054744c(005473e0) 004b4e37(004b4980) 0056307b(00562ff0) 005631e8(00562ff0) 

void FUN_005a88c0(void *param_1,size_t param_2,int param_3,int *param_4)

{
  _memcpy(param_1,(void *)(*param_4 + param_3),param_2);
  *param_4 = *param_4 + param_2;
  return;
}


